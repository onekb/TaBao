
import os
import json
from . import register_tool
from .base import _xml_response
from ..skills import skill_manager

# 动态生成文档字符串以包含可用 skills
def _get_skill_doc():
    skills = skill_manager.all_enabled()
    
    if not skills:
        return "Load a specialized skill that provides domain-specific instructions and workflows. No skills are currently available."

    skill_list = "\n".join([
        f"  <skill>\n    <name>{s.name}</name>\n    <description>{s.description}</description>\n  </skill>"
        for s in skills
    ])

    return f"""加载一个专用技能，该技能提供特定领域的指令和工作流。
当用户要求你执行任务时，检查是否有可用技能与之匹配。技能提供专门的能力和领域知识。
技能将注入详细的指令、工作流以及对捆绑资源（脚本、参考文档、模板）的访问到对话上下文中。
工具输出包含一个 `<skill_content name="...">` 区块，其中包含加载的内容。

<available_skills>
{skill_list}
</available_skills>

【重要规则】
1. 主动匹配：如果当前用户请求或上下文涉及以下任何 Skill 的能力范围，请优先调用对应的 Skill 来完成任务。
2. 避免重复：如果上下文中已有相关 Skill 的调用结果，且当前信息足够完成任务，请不要重复调用同一个 Skill。
3. 智能判断：仅在确实需要新的 Skill 能力时才调用，不要重复调用已提供过相同或相似信息的 Skill。
"""


class Skills:
    """
    Skills, 动态加载Skills列表,通过动态生成 __doc__ 来更新可用技能列表。
    """
    
    __name__ = "Skills"
    
    @property
    def __doc__(self):
        # 每次访问 __doc__ 时都重新生成，确保获取最新的 skills 状态
        return _get_skill_doc()
    
    def __call__(self, name: str):
        """
        Load a specialized skill that provides domain-specific instructions and workflows.

        Args:
            name: The name of the skill from available_skills
        """
        skill_obj = skill_manager.get_enabled(name)
        
        if not skill_obj:
            target_skill = skill_manager.get(name)
            if target_skill and not skill_manager.is_enabled(name):
                return _xml_response("Skills", "error", f"Skill '{name}' is disabled.")
            available = ", ".join([s.name for s in skill_manager.all_enabled()])
            return _xml_response("Skills", "error", f"Skill '{name}' not found. Available skills: {available or 'none'}")

        # 获取文件列表
        skill_dir = os.path.dirname(skill_obj.location)
        files = skill_manager.list_files(skill_dir)
        file_list_str = "\n".join([f"<file>{f}</file>" for f in files])

        output = [
            f"<skill_content name=\"{skill_obj.name}\">",
            f"# Skill: {skill_obj.name}",
            "",
            skill_obj.content.strip(),
            "",
            f"Base directory for this skill: {skill_dir}",
            "Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.",
            "Note: file list is sampled. limited to 50 files.",
            "",
            "<skill_files>",
            file_list_str,
            "</skill_files>",
            "</skill_content>"
        ]

        return _xml_response("Skills", "done", "\n".join(output))


# 注册工具
Skills = register_tool(category="Agent", name_cn="Skills", risk_level="low")(Skills())
