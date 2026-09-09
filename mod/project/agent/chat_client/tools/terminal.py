from . import register_tool
from .base import _xml_response
import threading
import subprocess
import time
import uuid
import os
import json

_CMD_SESSION = threading.local()

def _get_session_context():
    """从线程局部变量中获取当前会话上下文。
    
    Returns:
        tuple: (session_id, sessions_dir)，若未设置则返回 (None, None)
    """
    return getattr(_CMD_SESSION, 'session_id', None), getattr(_CMD_SESSION, 'sessions_dir', None)

# --- Command Manager for Non-blocking Commands ---
class CommandManager:
    """后台命令管理器，负责管理非阻塞命令的生命周期。
    
    支持命令的启动、状态查询、输出读取、结果持久化和跨会话恢复。
    使用线程安全的字典存储命令状态，通过后台线程异步读取命令输出。
    """
    
    def __init__(self):
        """初始化命令管理器，创建空的命令字典和线程锁。"""
        self.commands = {}
        self.lock = threading.Lock()

    def start_command(self, command: str, cwd: str, session_id: str = None, sessions_dir: str = None, background: bool = False) -> tuple:
        """启动一个新的子进程命令。
        
        Args:
            command: 要执行的 shell 命令字符串。
            cwd: 命令执行的工作目录。
            session_id: 会话ID，用于关联命令与会话。
            sessions_dir: 会话目录路径，用于持久化结果。
            background: 是否为后台命令（影响是否持久化结果）。
            
        Returns:
            tuple: (cmd_id, error)，成功时 error 为 None，失败时 cmd_id 为 None。
        """
        cmd_id = str(uuid.uuid4())
        
        shell_cmd = command
        if os.name == 'nt':
             shell_cmd = ["powershell", "-Command", command]
        
        try:
            process = subprocess.Popen(
                shell_cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                shell=False if os.name == 'nt' else True 
            )
        except Exception as e:
            return None, str(e)

        cmd_info = {
            "id": cmd_id,
            "session_id": session_id,
            "sessions_dir": sessions_dir,
            "process": process,
            "output": [], # List of lines
            "status": "running",
            "start_time": time.time(),
            "cwd": cwd,
            "command": command,
            "background": background
        }
        
        with self.lock:
            self.commands[cmd_id] = cmd_info

        # 启动后台线程读取命令输出
        t = threading.Thread(target=self._read_output, args=(cmd_id, process))
        t.daemon = True
        t.start()
        
        return cmd_id, None

    def _read_output(self, cmd_id, process):
        """后台线程：持续读取子进程的标准输出，命令结束时更新状态并持久化结果。
        
        此方法在独立线程中运行，逐行读取输出并存储到 cmd_info["output"] 列表中。
        当进程结束时，将状态设为 "done" 并触发结果持久化。
        
        Args:
            cmd_id: 命令的唯一标识符。
            process: subprocess.Popen 对象。
        """
        try:
            for line in iter(process.stdout.readline, ''):
                with self.lock:
                    if cmd_id in self.commands:
                        self.commands[cmd_id]["output"].append(line)
        except Exception:
            pass
        finally:
            try:
                process.stdout.close()
            except:
                pass
            
            # 等待进程结束并获取返回码
            return_code = process.wait()
            
            with self.lock:
                if cmd_id in self.commands:
                    self.commands[cmd_id]["status"] = "done"
                    self.commands[cmd_id]["returncode"] = return_code

            # 命令完成后持久化结果到磁盘
            self._persist_command_result(cmd_id)

    def get_status(self, cmd_id: str, priority: str = "bottom", limit: int = 1000):
        """获取指定命令的当前状态和部分输出。
        
        Args:
            cmd_id: 命令的唯一标识符。
            priority: 输出优先级，"bottom" 返回最新行，"top" 返回最早行。
            limit: 最多返回的输出行数。
            
        Returns:
            dict: 包含 status, returncode, output, cwd, command 的字典，
                  若命令不存在则返回 None。
        """
        with self.lock:
            if cmd_id not in self.commands:
                return None
            
            cmd = self.commands[cmd_id]
            output_lines = cmd["output"]
            
            if priority == "bottom":
                lines = output_lines[-limit:]
            else:
                lines = output_lines[:limit]
                
            return {
                "status": cmd["status"],
                "returncode": cmd.get("returncode"),
                "output": "".join(lines),
                "cwd": cmd["cwd"],
                "command": cmd["command"]
            }

    def get_running_command_ids(self, session_id: str = None) -> list:
        """获取当前正在运行的命令ID列表。
        
        Args:
            session_id: 可选，仅返回属于该会话的运行中命令。
            
        Returns:
            list: 状态为 "running" 的命令ID列表。
        """
        with self.lock:
            result = []
            for cid, cmd in self.commands.items():
                if cmd["status"] == "running":
                    if session_id is not None and cmd.get("session_id") != session_id:
                        continue
                    result.append(cid)
            return result

    def get_finished_commands(self, session_id: str = None) -> list:
        """非阻塞地获取已完成（done/stopped）的后台命令结果，并从内部状态中清除。
        
        与 wait_for_commands 不同，此方法不会阻塞等待运行中的命令，
        仅返回当前已经完成的命令。用于在工具执行循环中主动检测后台命令完成，
        避免模型在调用其他工具期间不知道后台命令已完成。
        
        Args:
            session_id: 会话ID，仅返回属于该会话的命令结果。
            
        Returns:
            已完成命令的结果字典列表。
        """
        # 扫描所有命令，收集非 running 状态且属于当前会话的命令
        results = []
        finished_ids = []
        sessions_dir = None

        with self.lock:
            for cid, cmd in self.commands.items():
                if cmd["status"] == "running":
                    continue
                if session_id is not None and cmd.get("session_id") != session_id:
                    continue
                results.append(self._result_dict(cmd))
                finished_ids.append(cid)
                if not sessions_dir:
                    sessions_dir = cmd.get("sessions_dir")

        # 从内部状态中删除已消费的命令
        for cid in finished_ids:
            with self.lock:
                if cid in self.commands:
                    del self.commands[cid]

        # 清理磁盘持久化文件中对应的条目，防止下次对话重复消费
        if finished_ids and sessions_dir and session_id:
            self._remove_persisted_entries(set(finished_ids), sessions_dir, session_id)

        return results

    def _get_command_output(self, cmd_id: str) -> str:
        """获取指定命令的完整输出（拼接所有行）。
        
        Args:
            cmd_id: 命令的唯一标识符。
            
        Returns:
            str: 命令的完整输出文本，若命令不存在则返回空字符串。
        """
        with self.lock:
            if cmd_id in self.commands:
                return "".join(self.commands[cmd_id]["output"])
            return ""

    def _result_dict(self, cmd):
        """从命令信息字典构建标准化的结果字典。
        
        Args:
            cmd: 命令信息字典（self.commands 中的条目）。
            
        Returns:
            dict: 包含 id, session_id, status, returncode, output, cwd, command 的结果字典。
        """
        return {
            "id": cmd["id"],
            "session_id": cmd.get("session_id"),
            "status": cmd["status"],
            "returncode": cmd.get("returncode", -1),
            "output": "".join(cmd["output"]),
            "cwd": cmd["cwd"],
            "command": cmd["command"]
        }

    def _persist_command_result(self, cmd_id):
        """将后台命令的执行结果持久化到磁盘文件。
        
        仅在命令标记为 background=True 且未被 wait_for_commands 消费时才会持久化，
        避免与 wait_for_commands 的结果重复。
        
        Args:
            cmd_id: 命令的唯一标识符。
        """
        with self.lock:
            if cmd_id not in self.commands:
                return
            cmd = self.commands[cmd_id]
            if not cmd.get("background") or cmd.get("_consumed_by_wait"):
                return
            sessions_dir = cmd.get("sessions_dir")
            session_id = cmd.get("session_id")
            if not sessions_dir or not session_id:
                return
            result = self._result_dict(cmd)
        self._persist_results([result], sessions_dir, session_id)

    def _persist_results(self, results, sessions_dir, session_id):
        """将命令结果列表追加写入持久化文件。
        
        持久化文件路径：{sessions_dir}/{session_id}/.bg_command_results.json
        
        Args:
            results: 要持久化的结果字典列表。
            sessions_dir: 会话目录路径。
            session_id: 会话ID。
        """
        if not sessions_dir or not session_id:
            return
        bg_file = os.path.join(sessions_dir, session_id, '.bg_command_results.json')
        try:
            os.makedirs(os.path.dirname(bg_file), exist_ok=True)
            existing = []
            if os.path.exists(bg_file):
                try:
                    with open(bg_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    pass
            existing.extend(results)
            with open(bg_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False)
        except Exception:
            pass

    def consume_persisted_results(self, sessions_dir: str, session_id: str) -> list:
        """消费（读取并删除）持久化的后台命令结果。
        
        在新对话开始时调用，用于获取上一轮对话中后台命令的完成结果。
        读取后会删除持久化文件，确保不会重复消费。
        
        Args:
            sessions_dir: 会话目录路径。
            session_id: 会话ID。
            
        Returns:
            list: 持久化的命令结果列表，若无文件或读取失败则返回空列表。
        """
        if not sessions_dir or not session_id:
            return []
        bg_file = os.path.join(sessions_dir, session_id, '.bg_command_results.json')
        if not os.path.exists(bg_file):
            return []
        try:
            with open(bg_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            os.remove(bg_file)
            return results
        except Exception:
            return []

    def _remove_persisted_entries(self, cmd_ids: set, sessions_dir: str, session_id: str):
        """从持久化文件中移除指定命令ID的条目。
        
        当命令结果已被 get_finished_commands 或 wait_for_commands 消费后，
        需要同步清理持久化文件，防止下次对话重复消费。
        
        Args:
            cmd_ids: 要移除的命令ID集合。
            sessions_dir: 会话目录路径。
            session_id: 会话ID。
        """
        if not sessions_dir or not session_id:
            return
        bg_file = os.path.join(sessions_dir, session_id, '.bg_command_results.json')
        try:
            if not os.path.exists(bg_file):
                return
            with open(bg_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            filtered = [r for r in existing if r.get("id") not in cmd_ids]
            if filtered:
                with open(bg_file, 'w', encoding='utf-8') as f:
                    json.dump(filtered, f, ensure_ascii=False)
            else:
                os.remove(bg_file)
        except Exception:
            pass

    def wait_for_commands(self, cmd_ids: list, poll_interval: float = 2, max_wait: float = 1800,
                          sessions_dir: str = None, session_id: str = None):
        """阻塞等待指定命令完成，超时后强制终止。
        
        当模型停止调用工具时调用，等待所有运行中的后台命令完成。
        超过 max_wait 秒后，未完成的命令会被强制终止。
        此方法会标记命令为 "_consumed_by_wait"，防止 _persist_command_result 重复持久化。
        
        Args:
            cmd_ids: 要等待的命令ID列表。
            poll_interval: 轮询间隔（秒），默认2秒。
            max_wait: 最大等待时间（秒），默认1800秒（30分钟）。
            sessions_dir: 会话目录路径，用于清理持久化文件。
            session_id: 会话ID。
            
        Returns:
            list: 所有命令的结果字典列表（包括超时被终止的）。
        """
        cmd_id_set = set(cmd_ids)
        # 标记这些命令已被 wait 消费，防止 _read_output 线程重复持久化
        with self.lock:
            for cid in cmd_id_set:
                if cid in self.commands:
                    self.commands[cid]["_consumed_by_wait"] = True

        results = []
        remaining_ids = set(cmd_ids)
        start_time = time.time()

        # 轮询等待所有命令完成
        while remaining_ids and (time.time() - start_time) < max_wait:
            finished_ids = set()
            for cid in list(remaining_ids):
                with self.lock:
                    if cid not in self.commands:
                        finished_ids.add(cid)
                        continue
                    cmd = self.commands[cid]
                    if cmd["status"] in ("done", "stopped"):
                        finished_ids.add(cid)
                        results.append(self._result_dict(cmd))

            remaining_ids -= finished_ids

            if remaining_ids:
                time.sleep(poll_interval)

        # 超时后强制终止未完成的命令
        for cid in remaining_ids:
            with self.lock:
                if cid in self.commands:
                    cmd = self.commands[cid]
                    try:
                        cmd["process"].terminate()
                    except Exception:
                        pass
                    cmd["status"] = "stopped"
                    results.append(self._result_dict(cmd))

        # 清理内部状态
        for cid in cmd_ids:
            with self.lock:
                if cid in self.commands:
                    del self.commands[cid]

        # 清理持久化文件中对应的条目
        self._remove_persisted_entries(cmd_id_set, sessions_dir, session_id)

        return results

    def stop_command(self, cmd_id: str):
        """终止指定的运行中命令。
        
        Args:
            cmd_id: 命令的唯一标识符。
            
        Returns:
            bool: 成功终止返回 True，命令不存在或非运行状态返回 False。
        """
        with self.lock:
            if cmd_id not in self.commands:
                return False
            
            cmd = self.commands[cmd_id]
            if cmd["status"] == "running":
                try:
                    cmd["process"].terminate() 
                    cmd["status"] = "stopped"
                except:
                    pass
                return True
            return False

_CMD_MANAGER = CommandManager()

@register_tool(category="Agent", name_cn="运行命令", risk_level="high")
class RunCommand:
    """
    Executes a given terminal command and returns its output.
    
    IMPORTANT: Avoid using this tool to run `find`, `grep`, `cat`, `head`, `tail`, `sed`, `awk`, or `echo` commands, unless explicitly instructed or after you have verified that a dedicated tool cannot accomplish your task. Instead, use the appropriate dedicated tool as this will provide a much better experience for the user:
    
    - File search: Use Glob tool (NOT find or ls)
    - Content search: Use Grep tool (NOT grep or rg)
    - Read files: Use Read tool (NOT cat/head/tail)
    - Edit files: Use SearchReplace tool (NOT sed/awk)
    - Write files: Use Write tool (NOT echo >/cat <<EOF)
    - Communication: Output text directly (NOT echo/printf)
    
    While the RunCommand tool can do similar things, it's better to use the built-in tools as they provide a better user experience and make it easier to review tool calls and give permission.
    
    # Instructions
    
    - If your command will create new directories or files, first use this tool to run `ls` to verify the parent directory exists and is the correct location.
    - Always quote file paths that contain spaces with double quotes in your command (e.g., cd "path with spaces/file.txt")
    - You may specify an optional timeout in milliseconds (up to 1800000ms / 30 minutes). By default, your command will timeout after 120000ms (2 minutes).
    
    ## Background Tasks
    - You can use `blocking=False` to run the command in the background. Only use this if you don't need the result immediately and are OK being notified when the command completes later. You do not need to check the output right away - you'll be notified when it finishes. You do not need to use '&' at the end of the command when using this parameter.
    - If your command is long running and you would like to check its status — use `blocking=False`. No sleep needed.
    - If waiting for a background task you started with `blocking=False`, use CheckCommandStatus to check — do not poll.
    - Rule of thumb: If the command typically runs for more than 30 seconds or runs indefinitely, use `blocking=False`.
    - Notifications: You will receive an automatic notification once result-producing commands complete. There is no need to repeatedly call the CheckCommandStatus tool to poll for command status — you will be notified automatically when the command finishes, unless it is a long-running process such as a started server.
    
    ## Multiple Commands
    When issuing multiple commands:
    - If the commands are independent and can run in parallel, make multiple RunCommand tool calls in a single message.
    - If the commands depend on each other and must run sequentially, use a single RunCommand call with '&&' to chain them together.
    - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail.
    - DO NOT use newlines to separate commands (newlines are ok in quoted strings).
    
    ## Avoid Unnecessary Sleep
    Avoid unnecessary `sleep` commands:
    - Do not sleep between commands that can run immediately — just run them.
    - Do not retry failing commands in a sleep loop — diagnose the root cause.
    - If you must sleep, keep the duration short (1-5 seconds) to avoid blocking the user.
    
    Args:
        command: The terminal command to execute.
        blocking: Whether to block and wait for the command to finish (default True).
        cwd: The working directory to run the command in.
        timeout: Optional timeout in milliseconds (default 120000ms = 2 mins). Only applies if blocking=True.
        description: Clear, concise description of what this command does in 5-10 words.
    """
    def execute(self, command: str, blocking: bool = True, cwd: str = None, timeout: int = 120000, description: str = None) -> str:
        """执行终端命令。
        
        支持阻塞和非阻塞两种模式：
        - 阻塞模式 (blocking=True)：等待命令完成或超过自动转后台阈值后返回
        - 非阻塞模式 (blocking=False)：立即返回，命令在后台运行
        
        Args:
            command: 要执行的终端命令字符串。
            blocking: 是否阻塞等待命令完成，默认 True。
            cwd: 工作目录，默认使用当前目录。
            timeout: 超时时间（毫秒），默认120000ms（2分钟），仅阻塞模式有效。
            description: 命令描述（5-10词），用于结果展示。
            
        Returns:
            str: XML 格式的执行结果，包含命令输出或错误信息。
        """
        BASH_MAX_RETURN_CHARS=30000
        AUTO_BG_THRESHOLD = 20
        
        stripped_cmd = command.strip()
        if stripped_cmd == "bt" or stripped_cmd.startswith("bt "):
            try:
                bt_result = subprocess.run("bt < /dev/null", shell=True, capture_output=True, text=True, timeout=10)
                bt_output = bt_result.stdout
                if bt_result.stderr:
                    bt_output += "\n" + bt_result.stderr
            except Exception as e:
                bt_output = str(e)
            warning = (
                "[BT Panel Command Blocked]\n"
                f"Original command: {command}\n"
                f"Output of 'bt < /dev/null':\n{bt_output}\n\n"
                "禁止帮用户执行面板相关操作命令，请让用户手动执行 若是重启面板 可以让用户通过 首页-右上角重启-重启面板进行重启。"
            )
            return _xml_response("RunCommand", "done", warning, max_chars=BASH_MAX_RETURN_CHARS)
        
        session_id, sessions_dir = _get_session_context()
        
        if not cwd:
            cwd = os.getcwd()
            
        if blocking:
            try:
                cmd_id, err = _CMD_MANAGER.start_command(command, cwd, session_id=session_id, sessions_dir=sessions_dir)
                if err:
                    return _xml_response("RunCommand", "error", err, max_chars=BASH_MAX_RETURN_CHARS)

                start_time = time.time()
                # 阻塞等待时间上限：取 AUTO_BG_THRESHOLD 和 timeout 的较小值
                max_block = min(AUTO_BG_THRESHOLD, timeout / 1000.0)

                # 轮询等待命令完成
                while time.time() - start_time < max_block:
                    status_info = _CMD_MANAGER.get_status(cmd_id)
                    if not status_info:
                        return _xml_response("RunCommand", "error", "Command process lost unexpectedly", max_chars=BASH_MAX_RETURN_CHARS)

                    if status_info["status"] in ("done", "stopped"):
                        output = status_info["output"]

                        final_output = output
                        if description:
                            final_output = f"Description: {description}\n\n{output}"

                        with _CMD_MANAGER.lock:
                            if cmd_id in _CMD_MANAGER.commands:
                                del _CMD_MANAGER.commands[cmd_id]

                        return _xml_response("RunCommand", "done", final_output, max_chars=BASH_MAX_RETURN_CHARS)

                    time.sleep(1)

                # 超过阈值未完成，自动转为后台执行
                current_output = _CMD_MANAGER._get_command_output(cmd_id)
                with _CMD_MANAGER.lock:
                    if cmd_id in _CMD_MANAGER.commands:
                        _CMD_MANAGER.commands[cmd_id]["background"] = True
                result = f"""<terminal_id>new</terminal_id>
<terminal_cwd>{cwd}</terminal_cwd>
Note: The command exceeded the {AUTO_BG_THRESHOLD}s auto-background threshold and has been automatically switched to background execution.
<command_id>{cmd_id}</command_id>
The command is still running in the background. You will be automatically notified when the command finishes. you can call CheckCommandStatus tool to check its progress and get the final result. But Do NOT call it immediately or repeatedly after this command starts running.
[Partial output so far]:
```
{current_output}
```
"""
                return _xml_response("RunCommand", "running", result, max_chars=BASH_MAX_RETURN_CHARS)

            except Exception as e:
                return _xml_response("RunCommand", "error", str(e), max_chars=BASH_MAX_RETURN_CHARS)
        else:
            # 非阻塞模式：直接以 background=True 启动
            cmd_id, err = _CMD_MANAGER.start_command(command, cwd, session_id=session_id, sessions_dir=sessions_dir, background=True)
            if err:
                return _xml_response("RunCommand", "error", err, max_chars=BASH_MAX_RETURN_CHARS)
                
            result = f"""<terminal_id>new</terminal_id>
<terminal_cwd>{cwd}</terminal_cwd>
Note: Command ID is provided for you to check command status later.
<command_id>{cmd_id}</command_id>
The command is running,You will be automatically notified when the command finishes, you can call CheckCommandStatus tool to get more logs to know whether it's running successfully But Do NOT call it immediately or repeatedly after this command starts running.
"""
            return _xml_response("RunCommand", "running", result, max_chars=BASH_MAX_RETURN_CHARS)

@register_tool(category="Agent", name_cn="检查命令状态", risk_level="low")
class CheckCommandStatus:
    """
    Check the status and output of a non-blocking command.
    
    Args:
        command_id: ID of the command to get status for.
        output_priority: Priority for displaying command output. 'bottom' (show newest lines) or 'top'.
    """
    def execute(self, command_id: str, output_priority: str = "bottom") -> str:
        """检查指定命令的执行状态和输出。
        
        若命令已完成（done/stopped），会自动从 CommandManager 中清理该命令。
        若命令仍在运行，会附加提醒告知模型不要重复轮询。
        
        Args:
            command_id: 要检查的命令ID。
            output_priority: 输出优先级，"bottom" 显示最新行，"top" 显示最早行。
            
        Returns:
            str: XML 格式的命令状态和输出日志。
        """
        status_info = _CMD_MANAGER.get_status(command_id, output_priority)
        if not status_info:
            return _xml_response("CheckCommandStatus", "error", "Command ID not found")
            
        # 命令已完成，从管理器中清理
        if status_info["status"] in ("done", "stopped"):
            with _CMD_MANAGER.lock:
                if command_id in _CMD_MANAGER.commands:
                    del _CMD_MANAGER.commands[command_id]

        logs = status_info["output"]
        status_str = status_info["status"]
        
        # 若命令仍在运行，提醒模型不要重复轮询
        running_hint = ""
        if status_str == "running":
            running_hint = """
REMINDER: You do NOT need to call CheckCommandStatus repeatedly. You will be automatically notified when the command finishes. Stop polling and wait — repeated calls waste compute resources and user quota. If you are currently polling in a loop or using sleep-and-poll patterns, STOP immediately.
"""

        result = f"""<terminal_id>unknown</terminal_id>
<terminal_cwd>{status_info['cwd']}</terminal_cwd>
<command_id>{command_id}</command_id>
<command_status>{status_str.capitalize()}</command_status><command_run_logs>
command output:
```
{logs}
```
</command_run_logs>
{running_hint}"""
        return _xml_response("CheckCommandStatus", "done", result)

@register_tool(category="Agent", name_cn="停止命令", risk_level="medium")
class StopCommand:
    """
    Terminate a running command.
    
    Args:
        command_id: The command id of the running command that you need to terminate.
    """
    def execute(self, command_id: str) -> str:
        """终止指定的运行中命令。
        
        Args:
            command_id: 要终止的命令ID。
            
        Returns:
            str: XML 格式的停止结果，成功或失败信息。
        """
        if _CMD_MANAGER.stop_command(command_id):
            return _xml_response("StopCommand", "done", f"Command {command_id} stopped.")
        else:
            return _xml_response("StopCommand", "error", f"Failed to stop command {command_id} (not running or not found).")
