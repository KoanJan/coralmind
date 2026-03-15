import json

from ...model import Task
from .static import EVALUATION_STANDARD

VALIDATION_EXPECTED_OUTPUT_FIELDS = "# 预期输出字段\n\n{output_names_text}\n"

VALIDATION_PROMPT = """# 任务要求

{requirements}

# 预期输出字段

{output_names_text}

# 实际输出

{output_text}

# 验证任务

请验证实际输出是否满足以下条件：
1. 是否包含所有预期输出字段？
2. 每个字段的内容是否与其定义匹配？
3. 整体输出是否满足任务要求？
{alignment_check}

以 JSON 格式返回：
{{"passed": true/false, "reason": "失败原因（如果通过则为空字符串）"}}"""

VALIDATION_ALIGNMENT_CHECK = """4. 输出是否与原始全局要求保持一致？如果输出偏离了原始意图，应当拒绝。

原始全局要求：
{global_requirements}"""

VALIDATION_RELEVANT_CHECK = """4. 输出是否与相关任务要求保持一致？如果输出偏离了指定要求，应当拒绝。

相关任务要求：
{relevant_requirements}"""

SCORE_RETURN_FORMAT = """# 返回格式

请以以下 JSON 格式返回评估结果：
```json
{
  "score": 0-10 的整数,
  "reason": "评分的详细原因"
}
```"""


def build_validation_messages(
    materials: dict[str, str],
    requirements: str,
    output: str | dict[str, str],
    output_names: dict[str, str] | None,
    relevant_requirements: str | None = None,
) -> list[str]:
    """Build messages for validating task output."""
    messages: list[str] = []

    for name, content in materials.items():
        messages.append(f"# {name}\n\n{content}")

    if isinstance(output, str):
        output_text = output
        output_names_text = ""
    else:
        output_name_descriptions = [f"- `{k}`: {v}" for k, v in (output_names or {}).items()]
        output_names_text_content = "\n".join(output_name_descriptions)
        output_names_text = VALIDATION_EXPECTED_OUTPUT_FIELDS.format(output_names_text=output_names_text_content)
        output_text = json.dumps(output, indent=2, ensure_ascii=False)

    if relevant_requirements:
        alignment_check = VALIDATION_RELEVANT_CHECK.format(relevant_requirements=relevant_requirements)
    else:
        alignment_check = ""

    validation_prompt = VALIDATION_PROMPT.format(
        requirements=requirements,
        output_names_text=output_names_text,
        output_text=output_text,
        alignment_check=alignment_check
    )
    messages.append(validation_prompt)

    return messages


def build_score_messages(task: Task, output: str) -> list[str]:
    """Build messages for scoring task output."""
    messages: list[str] = []

    for material in task.materials:
        messages.append(f"# {material.name}\n\n{material.content}")

    messages.append(f"# 任务要求\n\n{task.requirements}")
    messages.append(f"# 实际输出\n\n{output}")
    messages.append(EVALUATION_STANDARD)
    messages.append(SCORE_RETURN_FORMAT)

    return messages
