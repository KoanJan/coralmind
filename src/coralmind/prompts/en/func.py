import json

from ...model import Task
from .static import EVALUATION_STANDARD

VALIDATION_EXPECTED_OUTPUT_FIELDS = "# Expected Output Fields\n\n{output_names_text}\n"

VALIDATION_PROMPT = """# Task Requirements

{requirements}

# Expected Output Fields

{output_names_text}

# Actual Output

{output_text}

# Validation Task

Please validate whether the actual output meets the following conditions:
1. Does it contain all expected output fields?
2. Does each field's content match its definition?
3. Does the overall output meet the task requirements?
{alignment_check}

Return in JSON format:
{{"passed": true/false, "reason": "reason for failure (empty string if passed)"}}"""

VALIDATION_ALIGNMENT_CHECK = """4. Does the output align with the original global requirements? If the output deviates from the original intent, it should be rejected.

Original Global Requirements:
{global_requirements}"""

SCORE_RETURN_FORMAT = """# Return Format

Please return the evaluation result in the following JSON format:
```json
{
  "score": integer from 0-10,
  "reason": "detailed reason for the score"
}
```"""


def build_validation_messages(
    materials: dict[str, str],
    requirements: str,
    output: str | dict[str, str],
    output_names: dict[str, str] | None,
    global_requirements: str | None = None,
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

    if global_requirements:
        alignment_check = VALIDATION_ALIGNMENT_CHECK.format(global_requirements=global_requirements)
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

    messages.append(f"# Task Requirements\n\n{task.requirements}")
    messages.append(f"# Actual Output\n\n{output}")
    messages.append(EVALUATION_STANDARD)
    messages.append(SCORE_RETURN_FORMAT)

    return messages
