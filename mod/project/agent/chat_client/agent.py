import json
import logging
import traceback
import threading
from typing import Generator, List, Dict, Any, Optional, Union
import openai
import uuid
import os
import platform
import datetime

import public
from mod.project.agent.chat_client.memory import MemoryManager
from mod.project.agent.chat_client.retrieval import RAGService, ExternalRAGService

from .tools import registry
from .tools.base import _xml_response
from .tools.terminal import _CMD_MANAGER, _CMD_SESSION
from .skills import skill_manager

BINARY_EXTENSIONS = {
    '.zip', '.tar', '.gz', '.exe', '.dll', '.so', '.class', '.jar', '.war', '.7z',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.wav', '.ogg', '.mpg', '.mpeg',
    '.iso', '.bin', '.dat', '.db', '.sqlite', '.pyc', '.pyo'
}

class Agent:
    __version__ = "11.8.0_6.2"

    def __init__(self, session_id: str, config: Dict[str, Any] = None):
        self.session_id = session_id
        self.config = config or {}
        
        # 提取配置
        self.api_key = self.config.get("api_key")
        base_url = self.config.get("base_url")
        self.base_url = public.get_home_node(base_url) if base_url and 'bt.cn' in base_url else base_url
        self.model_name = self.config.get("model_name")
        self.rag_trigger_threshold = self.config.get("rag_trigger_threshold", 10)
        self.max_tool_iterations = self.config.get("max_tool_iterations", 10)
        self.enabled_tools = self.config.get("tools", [])
        self.default_headers = self.config.get("default_headers", {})
        self.default_headers["X-CVERSION"] = self.__version__
        self.system_prompt = self.config.get("system_prompt", "")
        self.temperature = self.config.get("temperature", 1)
        self.top_p = self.config.get("top_p", 1)
        
        # 官网知识库
        self.use_external_kb = self.config.get("use_external_kb", False)
        self.external_kb_appid = self.config.get("external_kb_appid", "bt_app_002")
        
        # Code mode configuration
        self.code_mode = self.config.get("code_mode", False)

        if self.code_mode:
            # Append environment info to system prompt
            self.current_dir = self.config.get("cwd")
            self.system_prompt += self._get_environment_info()
            
            # Default tools for code mode
            default_code_tools = [
                "Glob", "Grep", "LS", "Read", "Write", "DeleteFile",
                "SearchReplace", "StopCommand", "CheckCommandStatus", "RunCommand",
                "Task", "TodoWrite", "TodoRead", "TaskSummary", "WebFetch", "Skills"
            ]
            
            # Merge with existing enabled tools, avoiding duplicates
            for tool in default_code_tools:
                if tool not in self.enabled_tools:
                    self.enabled_tools.append(tool)
        else:
            # Default tools for non-code mode
            default_non_code_tools = [
                "Skills"
            ]
            for tool in default_non_code_tools:
                if tool not in self.enabled_tools:
                    self.enabled_tools.append(tool)

        self.memory = MemoryManager(
            session_id=session_id,
            sessions_dir=self.config.get("sessions_dir", "sessions"),
            sliding_window_size=self.config.get("sliding_window_size", 10),
            skill_agent_id=self.config.get("skill_agent_id"),
            model_name=self.model_name
        )
        
        # 将 MemoryManager 确定的 session_dir 传递给 RAGService
        self.rag = RAGService(
            session_dir=self.memory.session_dir,
            openai_api_key=self.api_key,
            openai_base_url=self.base_url,
            embedding_api_key=self.config.get("embedding_api_key"),
            embedding_base_url=self._process_url(self.config.get("embedding_base_url")),
            embedding_model_name=self.config.get("embedding_model_name"),
            small_model_name=self.config.get("small_model_name"),
            rag_retrieval_count=self.config.get("rag_retrieval_count", 10),
            rag_final_count=self.config.get("rag_final_count", 5),
            default_headers=self.default_headers
        )

        # 全局的知识库 RAG Service
        self.global_rag=None
        if self.use_external_kb:
            self.global_rag = ExternalRAGService(
                enable_rag_judgment=self.config.get("enable_rag_judgment", True),
                default_headers=self.default_headers
            )

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=self.default_headers
        )

    def _process_url(self, url):
        if url and 'bt.cn' in url:
            return public.get_home_node(url)
        return url

    def _get_environment_info(self) -> str:
        """Constructs environment information string to append to system prompt."""
        cwd = self.current_dir
        if os.path.exists(cwd):
            is_git = os.path.isdir(os.path.join(cwd, ".git"))
        else:
            is_git = False
        plat = platform.system().lower()
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # Note: model info is usually handled by the caller/config,
        # but we can try to include what we have.
        # The prompt template requested:
        # You are powered by the model named ${model.api.id}. The exact model ID is ${model.providerID}/${model.api.id}
        
        env_info = f"""

You are powered by the model named {self.model_name}.

Here is some useful information about the environment you are running in:
<env>
  Working directory: {cwd}
  Is directory a git repo: {"yes" if is_git else "no"}
  Platform: {plat}
  Today's date: {today}
</env>
<directories>
</directories>
"""
        return env_info

    def _is_binary_file(self, file_path: str) -> bool:
        """检查文件是否为二进制文件"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in BINARY_EXTENSIONS:
            return True
        
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    return True
        except:
            pass
        return False

    def _process_site_reference(self, site_name: str) -> tuple:
        """
        处理网站引用，返回 (call_prompt, result) 元组
        """
        call_prompt = f'[系统预处理] 检测到用户提到网站 "{site_name}"，已自动从数据库获取该网站的基础信息：'
        try:
            site_info = public.M('sites').where('name=?', (site_name,)).field('name,path,status,project_type,project_config').find()
            
            if not site_info:
                result = f'未找到网站: {site_name}'
            else:
                status_text = '开启' if site_info.get('status') == '1' else '关闭'
                result = f"网站基础信息:\n"
                result += f"- 网站名称(name): {site_info.get('name', '')}\n"
                result += f"- 项目路径(path): {site_info.get('path', '')}\n"
                result += f"- 网站状态(status): {status_text} (1=开启, 0=关闭)\n"
                result += f"- 项目类型(project_type): {site_info.get('project_type', 'PHP')}\n"
                result += f"- 项目配置(project_config): {site_info.get('project_config', '{}')}\n"
                result += f"\n字段说明:\n"
                result += f"- path: 网站项目路径\n"
                result += f"- status: 网站状态，1为开启状态，0为关闭状态\n"
                result += f"- project_type: 项目类型，如PHP、Java、Node等等\n"
                result += f"- project_config: 项目的额外配置，如果是需要启动的项目通常包含启动命令等信息，如果是静态或PHP项目通常为空\n"
        except Exception as e:
            result = f'获取网站信息失败: {str(e)}'
        
        return (call_prompt, result)

    def _process_file_reference(self, file_path: str) -> tuple:
        """
        处理单个文件引用，返回 (call_prompt, result) 元组
        """
        if not os.path.exists(file_path):
            return (
                f'Called the Read tool with the following input: {{"filePath":"{file_path}"}}',
                f'ERROR: 文件路径不存在: {file_path}'
            )
        
        if os.path.isdir(file_path):
            call_prompt = f'Called the LS tool with the following input: {{"path":"{file_path}"}}'
            try:
                from .tools.agent_tools import LS
                result = LS(path=file_path)
            except Exception as e:
                result = f'ERROR: 读取文件夹失败: {str(e)}'
            return (call_prompt, result)
        
        if self._is_binary_file(file_path):
            return (
                f'Called the Read tool with the following input: {{"filePath":"{file_path}"}}',
                f'ERROR: 当前是二进制文件还不支持读取: {file_path}'
            )
        
        call_prompt = f'Called the Read tool with the following input: {{"filePath":"{file_path}"}}'
        try:
            from .tools.read import Read
            result = Read(file_path=file_path)
        except Exception as e:
            result = f'ERROR: 读取文件失败: {str(e)}'
        return (call_prompt, result)

    def _process_user_input_files(self, user_input: Union[str, List[Dict[str, Any]]]) -> Union[str, List[Dict[str, Any]]]:
        """
        处理用户输入中的文件引用，将文件内容追加到 content 列表中
        """
        if isinstance(user_input, str):
            return user_input

        if not isinstance(user_input, list):
            return user_input

        file_refs = [item for item in user_input if isinstance(item, dict) and item.get("type") == "file"]
        site_refs = [item for item in user_input if isinstance(item, dict) and item.get("type") == "site"]

        if not file_refs and not site_refs:
            return user_input

        new_content = list(user_input)

        for file_ref in file_refs:
            file_path = file_ref.get("path", "")
            if not file_path:
                continue

            call_prompt, result = self._process_file_reference(file_path)

            new_content.append({
                "type": "text",
                "text": call_prompt,
                "ismeta": True
            })
            new_content.append({
                "type": "text",
                "text": result,
                "ismeta": True
            })

        for site_ref in site_refs:
            site_name = site_ref.get("name", "") or site_ref.get("path", "")
            if not site_name:
                continue

            call_prompt, result = self._process_site_reference(site_name)

            new_content.append({
                "type": "text",
                "text": call_prompt,
                "ismeta": True
            })
            new_content.append({
                "type": "text",
                "text": result,
                "ismeta": True
            })

        return new_content

    def close(self):
        """
        关闭 Agent，释放资源。
        """
        self.rag.close()
        if self.global_rag:
            self.global_rag.close()
        self.client.close()

    def _build_bg_command_messages(self, results: list, ai_msg_id: str = None, persist_immediately: bool = False) -> list:
        """
        将后台命令结果构建为 assistant(tool_calls) + tool 消息对。

        使用 RunCommand 作为虚拟工具名，生成与正常工具调用一致的调用链结构，
        这样后台命令结果可以自然地融入消息列表并享受缓存命中。

        持久化策略：
        - persist_immediately=True：立即持久化到会话文件（用于 loop 之前，如 session 启动时）
        - persist_immediately=False：不持久化，返回消息供调用方收集，延迟到 afterloop 统一持久化

        均标记 _system_generated=True，便于开发人员区分系统注入与 AI 真实生成的消息。
        """
        msgs = []
        for r in results:
            cmd = r.get("command", "")
            cwd = r.get("cwd")
            call_id = f"bg_{r['id']}"
            tool_call = {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "RunCommand",
                    "arguments": json.dumps({"command": cmd, "cwd": cwd, "background": True})
                }
            }
            assistant_msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call],
                "_system_generated": True
            }
            result_text = (
                f"[系统通知] 后台命令 {r['id']} 已完成 (status={r.get('status', 'unknown')}, "
                f"returncode={r.get('returncode', -1)})：\n\n"
                f"{r['output']}"
            )
            formatted_result = _xml_response("RunCommand", "done", result_text, max_chars=30000)
            tool_msg = {
                "role": "tool",
                "tool_call_id": call_id,
                "content": [{"type": "text", "text": formatted_result}],
                "_system_generated": True
            }
            # 仅在需要立即持久化时才写入会话文件
            if persist_immediately:
                if ai_msg_id is None:
                    ai_msg_id = str(uuid.uuid4())
                self.memory.add_message("assistant", assistant_msg.get("content"), id=ai_msg_id, tool_calls=assistant_msg.get("tool_calls"), _system_generated=True)
                self.memory.add_message("tool", tool_msg["content"], tool_call_id=call_id, id=ai_msg_id, _system_generated=True)
            msgs.append(assistant_msg)
            msgs.append(tool_msg)
        return msgs

    def _append_dynamic_reminder(self, collection: list, reminder_text: str):
        """
        将动态 reminder 文本追加到收集列表中。
        这些 reminder 会在每轮迭代时重新生成，不累积上一轮的内容。
        
        参数:
            collection: reminder 收集列表
            reminder_text: 要追加的 reminder 文本
        """
        collection.append(reminder_text)

    def _build_user_meta_message(self) -> List[Dict[str, Any]]:
        """
        构建系统环境信息的 content 列表。
        调用方需要自行包装成完整的消息字典（如 role="user", ismeta=True）。
        
        该 content 会被插入到消息数组的 system 之后，作为第一条用户消息的 content，
        并持久化到 session 文件。
        
        包含信息：操作系统、系统日期（仅日期，不含时间以提高缓存命中率）、当前模型、面板版本。
        每个 content block 标记 ismeta=True，用于前端隐藏显示。
        
        返回:
            包含系统环境信息的 content block 列表
        """
        import platform as _platform
        os_name = _platform.platform()
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        panel_version = getattr(public, 'version', lambda: 'unknown')() if hasattr(public, 'version') else 'unknown'

        text = (
            f"<system-reminder>\n"
            f"以下是当前系统环境信息，请在执行任务时参考：\n"
            f"- 操作系统: {os_name}\n"
            f"- 系统日期: {current_date}\n"
            f"- 当前模型: {self.model_name}\n"
            f"- 面板版本: {panel_version}\n"
            f"在执行所有动作前，都需要判断是否有对应可以使用的Skill工具，这将会提升你的效率和理解用户需求的能力。\n"
            f"</system-reminder>"
        )

        return [{"type": "text", "text": text, "ismeta": True}]

    def _build_user_meta_reminder(self, dynamic_reminders: list) -> Optional[Dict[str, Any]]:
        """
        将动态 reminder 列表合并为独立的 ismeta 用户消息块。
        该消息块不会被持久化到 session 文件，仅追加到 request_messages 末尾，每轮重新生成。
        
        动态 reminder 包括：RAG 检索结果、Skills 列表、后台命令执行结果等。
        消息级别和每个 content block 级别均标记 ismeta=True，用于前端隐藏显示。
        
        参数:
            dynamic_reminders: 当前轮次的动态 reminder 文本列表
            
        返回:
            合并后的用户消息字典，若列表为空则返回 None
        """
        if not dynamic_reminders:
            return None

        content_blocks = []
        for reminder in dynamic_reminders:
            content_blocks.append({
                "type": "text",
                "text": reminder,
                "ismeta": True
            })

        return {
            "role": "user",
            "content": content_blocks,
            "ismeta": True
        }

    def _strip_meta_from_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        在发送给 AI API 之前，从消息数组中清除所有 ismeta 字段。
        保留消息和内容本身，仅移除 ismeta 标记

        处理两个层级：
        1. 消息级别的 ismeta 字段（如 _build_user_meta_reminder 构建的整条消息）
        2. content block 级别的 ismeta 字段（如文件/站点引用注入的内容块）
        """
        result = []
        for msg in messages:
            clean_msg = {k: v for k, v in msg.items() if k != "ismeta"}
            content = clean_msg.get("content")
            if isinstance(content, list):
                clean_content = []
                for block in content:
                    if isinstance(block, dict):
                        clean_content.append({k: v for k, v in block.items() if k != "ismeta"})
                    else:
                        clean_content.append(block)
                clean_msg["content"] = clean_content
            result.append(clean_msg)
        return result

    def _inject_cache_control(self, request_messages: list) -> list:
        """
        注入消息缓存控制字段。

        注意：必须在 meta 消息追加之前调用，确保 cache_control 只打在真正的用户输入消息上，
        而不是最末尾的 system-reminder meta 消息块上。
        """
        result = []
        for msg in request_messages:
            new_msg = dict(msg)
            content = new_msg.get("content")
            if new_msg.get("role") == "system":
                if isinstance(content, str):
                    new_msg["content"] = [{"type": "text", "text": content}]
                elif isinstance(content, list):
                    new_msg["content"] = [dict(block) for block in content]
                if new_msg.get("role") == "system" and isinstance(new_msg["content"], list) and new_msg["content"]:
                    new_msg["content"][-1]["cache_control"] = {"type": "ephemeral"}
            result.append(new_msg)

        for i in range(len(result) - 1, -1, -1):
            if result[i].get("role") == "user":
                content = result[i].get("content")
                if isinstance(content, list) and content:
                    for block in content:
                        if block.get("type") == "text":
                            block["cache_control"] = {"type": "ephemeral"}
                            break
                break

        # 在最后一个 tool 消息上设置 cache_control
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("role") in ("tool"):
                content = result[i].get("content")
                if isinstance(content, list) and content:
                    for block in content:
                        if block.get("type") == "text":
                            block["cache_control"] = {"type": "ephemeral"}
                            break
                break

        # 统一消息键顺序，确保缓存命中率
        # 使用 sort_keys 序列化后再反序列化，确保键顺序一致
        standardized = []
        for msg in result:
            json_str = json.dumps(msg, sort_keys=True, ensure_ascii=False)
            ordered = json.loads(json_str)
            # 反转键顺序
            reversed_msg = {k: ordered[k] for k in reversed(list(ordered.keys()))}
            standardized.append(reversed_msg)
        return standardized

    def _create_completion_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]]):
        params = {
            "model": self.model_name,
            "messages": messages,
            "tools": tools if tools else None,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": self.temperature,
            "top_p": self.top_p,
            "extra_body": {}
        }

        thinking = self.config.get("thinking", False)
        web_search = self.config.get("web_search", False)

        if "qwen" in str(self.model_name).lower() or "default" in str(self.model_name).lower():
            params["extra_body"]["enable_thinking"] = thinking
            params["extra_body"]["enable_search"] = web_search
            params["extra_body"]["search_options"] = {
                "search_strategy": "max",       # 配置搜索策略为高性能模式
                "enable_search_extension": True # 垂直领域搜索增强 例如天气、股市等
            }
        
        if "doubao" in str(self.model_name).lower():
            enable_type = "enabled" if thinking else "disabled"
            params['extra_body']["thinking"] = {
                "type": enable_type
            }

        return self.client.chat.completions.create(**params)

    def _accumulate_usage(self, total_usage: dict, last_loop_tokens: dict, chunk) -> str:
        """
        从流式响应的 chunk 中累加 token 使用量统计。
        
        累加到 total_usage（整个聊天会话的总 token 使用量）和 
        last_loop_tokens（当前轮次的 token 使用量）。
        同时处理缓存相关的 token 统计（cache_creation_input_tokens, cached_tokens）。
        
        参数:
            total_usage: 总 token 使用量字典
            last_loop_tokens: 当前轮次 token 使用量字典
            chunk: OpenAI 流式响应 chunk
            
        返回:
            chunk 的消息 ID，若无则返回空字符串
        """
        if not chunk.usage:
            return ""
        total_usage["total_tokens"] += chunk.usage.total_tokens
        total_usage["input_tokens"] += chunk.usage.prompt_tokens
        total_usage["output_tokens"] += chunk.usage.completion_tokens
        last_loop_tokens["total_tokens"] = chunk.usage.total_tokens
        last_loop_tokens["input_tokens"] = chunk.usage.prompt_tokens
        last_loop_tokens["output_tokens"] = chunk.usage.completion_tokens
        ptd = getattr(chunk.usage, 'prompt_tokens_details', None)
        if not ptd:
            extra = getattr(chunk.usage, 'model_extra', None) or getattr(chunk.usage, '__pydantic_extra__', None) or {}
            ptd = extra.get('prompt_tokens_details')
        if ptd:
            if isinstance(ptd, dict):
                cache_creation = ptd.get('cache_creation_input_tokens', 0) or 0
                cached = ptd.get('cached_tokens', 0) or 0
            else:
                cache_creation = getattr(ptd, 'cache_creation_input_tokens', 0) or 0
                cached = getattr(ptd, 'cached_tokens', 0) or 0
            total_usage["cache_creation_input_tokens"] += cache_creation
            total_usage["cached_tokens"] += cached
            last_loop_tokens["cache_creation_input_tokens"] = cache_creation
            last_loop_tokens["cached_tokens"] = cached
        return chunk.id or ""

    def _process_completion_stream(self, response_stream, total_usage: dict, last_loop_tokens: dict):
        """
        处理 OpenAI 流式响应，累加内容并 yield 事件给前端。
        
        作为生成器函数，通过 yield from 将事件（reasoning/content/tool_call）直接转发给调用方，
        同时通过 return 传回计算结果（current_response_content, current_reasoning_content, 
        finish_reason, tool_call_chunks）。
        
        参数:
            response_stream: OpenAI 流式响应对象
            total_usage: 总 token 使用量字典
            last_loop_tokens: 当前轮次 token 使用量字典
            
        生成器:
            yield: 事件字典（type: reasoning/content/tool_call）
            return: (current_response_content, current_reasoning_content, finish_reason, tool_call_chunks)
        """
        tool_call_chunks = {}
        reported_tool_indices = set()
        current_response_content = ""
        current_reasoning_content = ""
        finish_reason = None

        for chunk in response_stream:
            msg_id = self._accumulate_usage(total_usage, last_loop_tokens, chunk)
            if msg_id:
                last_loop_tokens["_message_id"] = msg_id

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            if getattr(delta, "reasoning_content", None):
                current_reasoning_content += delta.reasoning_content
                yield {"type": "reasoning", "response": delta.reasoning_content}

            if delta.content:
                current_response_content += delta.content
                yield {"type": "content", "response": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index
                    if index not in tool_call_chunks:
                        tool_call_chunks[index] = {"id": tc.id, "function": {"name": "", "arguments": ""}}
                    if tc.id:
                        tool_call_chunks[index]["id"] = tc.id
                    if tc.function.name:
                        tool_call_chunks[index]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_call_chunks[index]["function"]["arguments"] += tc.function.arguments
                    tool_name = tool_call_chunks[index]["function"]["name"]
                    if tool_name and tool_call_chunks[index]["function"]["arguments"]:
                        tool_exists = registry.tool_exists(tool_name)
                        tool_enabled = registry.is_tool_enabled(tool_name, self.enabled_tools) if tool_exists else False
                        if tool_exists and tool_enabled:
                            reported_tool_indices.add(index)
                            yield {
                                "type": "tool_call",
                                "tool": tool_name,
                                "args": tool_call_chunks[index]["function"]["arguments"],
                                "id": tool_call_chunks[index]["id"]
                            }

        return current_response_content, current_reasoning_content, finish_reason, tool_call_chunks

    def _process_tool_calls(self, tool_call_chunks, current_response_content, current_reasoning_content,messages, ai_msg_id, pending_bg_reminders, last_loop_tokens):
        """
        执行工具调用并处理结果。
        
        作为生成器函数，通过 yield from 将工具执行事件（tool_call/tool_result/subtask_stream）
        直接转发给调用方，同时通过 return 传回更新后的消息列表和是否超过 token 限制的标志。
        
        主要逻辑：
        1. 将助手消息（含工具调用）添加到记忆和消息列表
        2. 逐个执行工具调用，处理存在/启用检查
        3. 特殊处理 Task 工具（子代理事件转发）和 TodoWrite/Read 工具（注入 session_id）
        4. 检查已完成的后台命令，注入到消息列表
        5. 检查 token 超限
        
        参数:
            tool_call_chunks: 工具调用块字典
            current_response_content: 当前轮次的文本响应内容
            current_reasoning_content: 当前轮次的推理内容
            messages: 消息列表（会被修改）
            ai_msg_id: AI 消息 ID
            pending_bg_reminders: 待处理的后台命令 reminder 列表
            last_loop_tokens: 当前轮次 token 使用量字典
            
        生成器:
            yield: 事件字典（type: tool_call/tool_result/subtask_stream/error）
            return: (messages, token_exceeded)
        """
        assistant_msg_kwargs = {"tool_calls": []}
        for idx in sorted(tool_call_chunks.keys()):
            tc = tool_call_chunks[idx]
            assistant_msg_kwargs["tool_calls"].append({
                "id": tc["id"], "type": "function", "function": tc["function"]
            })
        if current_reasoning_content:
            assistant_msg_kwargs["reasoning_content"] = current_reasoning_content
        self.memory.add_message("assistant", current_response_content, id=ai_msg_id, **assistant_msg_kwargs)
        assistant_api_msg = {
            "role": "assistant",
            "content": current_response_content,
            "tool_calls": assistant_msg_kwargs["tool_calls"]
        }
        assistant_api_msg["reasoning_content"] = current_reasoning_content
        messages.append(assistant_api_msg)

        _CMD_SESSION.session_id = self.session_id
        _CMD_SESSION.sessions_dir = self.config.get("sessions_dir")
        for tc in assistant_msg_kwargs["tool_calls"]:
            func_name = tc["function"]["name"]
            args_str = tc["function"]["arguments"]
            call_id = tc["id"]
            tool_exists = registry.tool_exists(func_name)
            tool_enabled = registry.is_tool_enabled(func_name, self.enabled_tools) if tool_exists else False
            if not tool_exists:
                result_str = _xml_response(func_name, "error", f"Error: Tool '{func_name}' does not exist.")
                content_structure = [{"type": "text", "text": result_str}]
                self.memory.add_message("tool", content_structure, tool_call_id=call_id, id=ai_msg_id)
                messages.append({"role": "tool", "tool_call_id": call_id, "content": content_structure})
                continue
            if not tool_enabled:
                tool_id = registry.get_tool_id(func_name)
                result_str = _xml_response(func_name, "error", f"Error: Tool '{func_name}' (ID: {tool_id}) is not enabled. You do not have permission to use this tool.")
                content_structure = [{"type": "text", "text": result_str}]
                self.memory.add_message("tool", content_structure, tool_call_id=call_id, id=ai_msg_id)
                messages.append({"role": "tool", "tool_call_id": call_id, "content": content_structure})
                continue

            yield {"type": "tool_call", "tool": func_name, "args": args_str, "id": call_id}
            try:
                args = json.loads(args_str)
                if func_name == "Task":
                    agent_config = self.config.copy()
                    agent_config.pop("system_prompt", None)
                    agent_config.pop("tools", None)
                    args["parent_config"] = agent_config
                    args["parent_session_id"] = self.session_id
                if func_name in ["TodoWrite", "TodoRead", "TaskSummary"]:
                    args["session_id"] = self.session_id
                    args["sessions_dir"] = self.config.get("sessions_dir")
                func = registry.get_tool_func(func_name)
                if func:
                    result = func(**args)
                    if func_name == "Task" and hasattr(result, '__next__'):
                        result_str = ""
                        for event in result:
                            event_type = event.get("type")
                            if event_type == "subtask_stream":
                                yield {"type": "subtask_stream", "task_id": event.get("task_id"), "chunk": event.get("chunk")}
                            elif event_type == "subtask_done":
                                result_str = event.get("result", "")
                            elif event_type == "subtask_error":
                                result_str = _xml_response(func_name, "error", event.get("data", ""))
                        if not result_str:
                            result_str = _xml_response(func_name, "error", "Task produced no result")
                    else:
                        result_str = result
                else:
                    result_str = _xml_response(func_name, "error", f"Error: Tool {func_name} not found.")
            except Exception as e:
                result_str = _xml_response(func_name, "error", f"Error executing tool: {str(e)}")

            yield {"type": "tool_result", "tool": func_name, "result": result_str, "id": call_id}
            content_structure = [{"type": "text", "text": result_str}]
            self.memory.add_message("tool", content_structure, tool_call_id=call_id, id=ai_msg_id)
            messages.append({"role": "tool", "tool_call_id": call_id, "content": content_structure})

        max_context_tokens = self.config.get("max_context_tokens", 64000)
        if last_loop_tokens.get('input_tokens', 0) >= max_context_tokens:
            yield {"type": "error", "data": "上下文已超过最大Token限制，为避免信息丢失，请压缩上下文后再继续对话"}
            return messages, True

        return messages, False

    def chat(self, user_input: Union[str, List[Dict[str, Any]]]) -> Generator[Dict[str, Any], None, None]:
        """
        主聊天循环，支持流式响应和工具调用。
        
        生命周期（6 阶段）:
            Phase 1 - 初始化: 生成消息 ID
            Phase 2 - preloop: 系统信息持久化 + 用户输入处理（含 RAG 合并）+ 记忆写入
            Phase 3 - 构建消息: 构建基础消息数组（含系统信息）
            Phase 4 - 循环准备: 工具配置 + pending_bg_reminders 初始化
            Phase 5 - 迭代循环:
                - pre_iteration: dynamic_reminders 每轮全新重建（不累积）
                - API 调用 + 流式处理
                - post_iteration: 后台命令 → tool_call + tool_result 注入到 messages
            Phase 6 - afterloop: 保存助手响应 + 更新 token
        
        消息数组结构:
            [0] system_prompt                                    (role: system)
            [1] system_info_message                              (role: user, ismeta, persisted)
            [2..N-1] 历史消息                                     (from memory)
            [N] 当前用户输入（含 RAG 结果）                          (role: user, persisted)
            [N+1] dynamic_meta_message                           (role: user, NOT persisted)
        
        参数:
            user_input: 用户输入，可以是字符串或包含文本/文件/站点引用的列表
            
        生成器:
            yield: 事件字典（type: meta_info/content/reasoning/tool_call/tool_result/subtask_stream/stop/error）
        """
        try:
            # === Phase 1: 初始化 ===
            user_msg_id = str(uuid.uuid4())
            ai_msg_id = str(uuid.uuid4())
            yield {"type": "meta_info", "user_msg_id": user_msg_id, "ai_msg_id": ai_msg_id}

            # === Phase 2: 处理用户输入与记忆（preloop） ===
            # 系统信息消息持久化：仅在首次空会话时添加，保存到 session 文件
            is_first_chat = self.memory.get_total_rounds() == 0
            if is_first_chat:
                self.memory.add_message("user", self._build_user_meta_message(), ismeta=True)
            # 处理文件/站点引用，注入的 ismeta 块会被合并到用户消息中
            user_input = self._process_user_input_files(user_input)

            # RAG检索：结果合并到用户输入中一起持久化，避免作为 dynamic_reminder 每轮变动破坏缓存命中
            # 先从 user_input 中提取纯文本用于 RAG 检索
            user_text = user_input
            if isinstance(user_input, list):
                text_parts = []
                for item in user_input:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                user_text = "\n".join(text_parts)

            recent_history = self.memory.get_sliding_window()
            if self.global_rag:
                global_docs = self.global_rag.search(user_text, scope="global", session_history=recent_history,enable_rag_judgment=True)
                if global_docs:
                    rag_blocks = "\n".join(
                        f"<knowledge_base>\n{doc}\n</knowledge_base>" for doc in global_docs
                    )
                    rag_content = (
                        f"<system-reminder>\n"
                        f"以下内容来自外部知识库检索结果，仅供参考。请注意：\n"
                        f"1. 这些内容并非用户直接输入，而是系统自动检索的补充资料\n"
                        f"2. 可以作为回答的参考依据，但不能完全信任其准确性\n"
                        f"3. 如果与用户当前问题无关，请忽略这些内容\n\n"
                        f"{rag_blocks}\n"
                        f"</system-reminder>"
                    )
                    # 合并到用户输入 content 中，标记 ismeta 用于前端隐藏
                    if isinstance(user_input, str):
                        user_input = [{"type": "text", "text": user_input}]
                    user_input.append({"type": "text", "text": rag_content, "ismeta": True})
            
            # 用户消息持久化
            self.memory.add_message("user", user_input, id=user_msg_id)

            # === Phase 4: 构建基础消息数组（preloop） ===
            messages = self._build_messages()

            # 消费未被使用的reminder（这些会在第一轮 pre_iteration 时加入 dynamic_reminders）
            pending_bg_reminders = []

            # 延迟持久化收集器：loop 运行中的后台命令结果先收集，等 afterloop 统一持久化
            pending_bg_persist = []

            # 消费上一次会话持久化的后台命令结果，立即持久化并注入 messages
            persisted = _CMD_MANAGER.consume_persisted_results(
                self.config.get("sessions_dir", "sessions"), self.session_id
            )
            if persisted:
                messages.extend(self._build_bg_command_messages(persisted, ai_msg_id=ai_msg_id, persist_immediately=True))

            tools = registry.get_openai_tools(enabled_ids=self.enabled_tools)
            iteration_count = 0
            full_response_content = ""
            full_reasoning_content = ""
            tool_call_chunks = {}
            total_usage = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0,"cache_creation_input_tokens": 0, "cached_tokens": 0}
            last_message_id = ""

            # === Phase 5: 迭代循环 ===
            while iteration_count < self.max_tool_iterations:
                iteration_count += 1
                last_loop_tokens = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0,"cache_creation_input_tokens": 0, "cached_tokens": 0}

                # --- pre_iteration: 每轮重新生成 dynamic_reminders 动态内容 保证每次都会在message最末尾 ---
                # 从 pending_bg_reminders 复制并清空，确保不累积上一轮的 reminder
                dynamic_reminders = list(pending_bg_reminders)
                pending_bg_reminders = []

                # --- 检查工具执行期间是否有后台命令完成，注入 messages 供下轮使用 ---
                finished_cmds = _CMD_MANAGER.get_finished_commands(session_id=self.session_id)
                if finished_cmds:
                    bg_msgs = self._build_bg_command_messages(finished_cmds, ai_msg_id=ai_msg_id, persist_immediately=False)
                    messages.extend(bg_msgs)
                    pending_bg_persist.extend(bg_msgs)

                # 构建请求消息：拷贝基础消息 → 注入缓存控制 → 追加动态 meta → 清除 ismeta
                request_messages = list(messages)
                # 注意：cache_control 必须在 meta 消息追加之前注入，避免缓存打到 meta 上
                request_messages = self._inject_cache_control(request_messages)
                meta_msg = self._build_user_meta_reminder(dynamic_reminders)
                if meta_msg:
                    request_messages.append(meta_msg)
                # 清除 ismeta 字段（保留内容）
                request_messages = self._strip_meta_from_messages(request_messages)
                response_stream = self._create_completion_stream(request_messages, tools)

                # --- 流式响应处理 ---
                stream_result = yield from self._process_completion_stream(response_stream, total_usage, last_loop_tokens)
                current_response_content, current_reasoning_content, finish_reason, tool_call_chunks = stream_result
                last_message_id = last_loop_tokens.pop("_message_id", last_message_id)

                if current_response_content:
                    full_response_content = current_response_content
                if current_reasoning_content:
                    full_reasoning_content = current_reasoning_content

                yield {"type": "meta_info", "user_msg_id": user_msg_id, "ai_msg_id": ai_msg_id,"last_loop_tokens": dict(last_loop_tokens), "iteration": iteration_count}

                # --- post_iteration: 停止/工具调用分支 ---
                if not tool_call_chunks:
                    # 无工具调用时，检查是否有运行中的后台命令
                    sessions_dir = self.config.get("sessions_dir")
                    running_ids = _CMD_MANAGER.get_running_command_ids(session_id=self.session_id)
                    if running_ids:
                        # 等待后台命令完成，注入 messages 供下轮使用，延迟持久化
                        bg_results = _CMD_MANAGER.wait_for_commands(running_ids, sessions_dir=sessions_dir, session_id=self.session_id)
                        bg_msgs = self._build_bg_command_messages(bg_results, ai_msg_id=ai_msg_id, persist_immediately=False)
                        messages.extend(bg_msgs)
                        pending_bg_persist.extend(bg_msgs)
                        continue
                    # 无后台命令，正常停止
                    yield {"type": "stop", "usage": total_usage, "message_id": last_message_id}
                    break

                # --- 工具执行 ---
                # yield from 委托给 _process_tool_calls，它会将后台命令结果通过tool_call + tool_result 注入 messages
                tool_result = yield from self._process_tool_calls(tool_call_chunks, current_response_content, current_reasoning_content,messages, ai_msg_id, pending_bg_reminders, last_loop_tokens)
                messages, token_exceeded = tool_result
                if token_exceeded:
                    break

            # === Phase 6: 最终记忆更新（afterloop） ===
            if not tool_call_chunks and full_response_content:
                 kwargs = {}
                 if full_reasoning_content:
                     kwargs["reasoning_content"] = full_reasoning_content
                 # ai消息持久化
                 self.memory.add_message("assistant", full_response_content, id=ai_msg_id, **kwargs)

            # 统一持久化 loop 运行中收集的后台命令消息（在 AI 消息之后写入，保持消息顺序）
            for bg_msg in pending_bg_persist:
                if bg_msg["role"] == "assistant":
                    self.memory.add_message("assistant", bg_msg.get("content"), id=ai_msg_id, tool_calls=bg_msg.get("tool_calls"), _system_generated=True)
                elif bg_msg["role"] == "tool":
                    self.memory.add_message("tool", bg_msg["content"], tool_call_id=bg_msg["tool_call_id"], id=ai_msg_id, _system_generated=True)

            if iteration_count >= self.max_tool_iterations:
                yield {"type": "error", "data": "达到最大行动次数上限，已强制停止当前对话 error_code:max_tool_iterations"}

            
            # 更新 meta.json 中的 token 使用量
            self.memory.update_meta_tokens(
                total_tokens=last_loop_tokens["total_tokens"],
                input_tokens=last_loop_tokens["input_tokens"],
                output_tokens=last_loop_tokens["output_tokens"]
            )
            
            # 发送 meta_info 包含 ID 和 token 使用量
            yield {
                "type": "meta_info",
                "user_msg_id": user_msg_id,
                "ai_msg_id": ai_msg_id,
                "last_loop_tokens": last_loop_tokens
            }

        except openai.AuthenticationError as e:
            yield {"type": "error", "data": f"API密钥错误或无效，请检查密钥是否正确:{e}"}
        except openai.RateLimitError as e:
            yield {"type": "error", "data": "接口调用频率超限，请稍后再试或提升配额:{}".format(e)}
        except openai.APIConnectionError as e:
            yield {"type": "error", "data": f"无法连接到API服务器（{self.base_url}），请检查网络或地址是否正确:{e}"}
        except openai.APIError as e:
            yield {"type": "error", "data": f"API返回错误：{str(e)}"}
        except Exception as e:
            logging.error(f"Unexpected error in Agent.chat: {traceback.format_exc()}")
            yield {"type": "error", "data": f"调用AI接口时发生未知错误：{str(e)}"}
    
    def _filter_file_blocks(self, content: Union[str, List[Dict[str, Any]]]) -> Union[str, List[Dict[str, Any]]]:
        """
        过滤掉 type="file" 和 type="site" 的块，只保留 type="text" 的块
        """
        if isinstance(content, str):
            return content
        
        if not isinstance(content, list):
            return content
        
        FILTERED_TYPES = {"file", "site"}
        return [item for item in content if not (isinstance(item, dict) and item.get("type") in FILTERED_TYPES)]

    def _build_messages(self) -> List[Dict[str, Any]]:
        """构建包含系统指令、上下文和滑动窗口的 Prompt。

        参数:
            is_first_chat: 是否为首次空会话，仅在首次时插入系统环境信息消息

        技术债务：当前 sliding window 机制已移除（get_sliding_window 返回全部历史）。
        如果未来恢复 sliding window，需要在加载历史消息时过滤掉带 ismeta 的 content blocks，
        避免已持久化的系统信息消息在历史中重复出现。
        过滤方式：对 content 为 list 的消息，过滤掉 ismeta=True 的 block；
        如果过滤后 content 为空，则跳过整条消息。
        """

        messages = [{"role": "system", "content": self.system_prompt}]

        window = self.memory.get_sliding_window()
        for msg in window:
            content = msg["content"]
            content = self._filter_file_blocks(content)
            # 深拷贝 content，避免修改 memory 中的原始数据
            if isinstance(content, list):
                content = [dict(block) if isinstance(block, dict) else block for block in content]

            m = {
                "role": msg["role"],
                "content": content
            }
            if msg.get("role") == "assistant" and "reasoning_content" in msg:
                m["reasoning_content"] = msg["reasoning_content"]
            if "tool_calls" in msg:
                m["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                m["tool_call_id"] = msg["tool_call_id"]
            messages.append(m)

        return messages
