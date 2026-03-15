from pydantic import BaseModel

from ...model import Task
from .static import EVALUATION_STANDARD

VALIDATION_PROMPT_DICT = """# Task Requirements

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

VALIDATION_PROMPT_STR = """# Task Requirements

{requirements}

# Expected Output

{output_what}

# Actual Output

{output_text}

# Validation Task

Please validate whether the actual output meets the following conditions:
1. Does the output match the expected output description?
2. Does the output meet the task requirements?
3. Is the output clean without irrelevant content (e.g., self-praise, meta-commentary, or explanations not part of the deliverable)?
{alignment_check}

Return in JSON format:
{{"passed": true/false, "reason": "reason for failure (empty string if passed)"}}"""

VALIDATION_ALIGNMENT_CHECK = """4. Does the output align with the original global requirements? If the output deviates from the original intent, it should be rejected.

Original Global Requirements:
{global_requirements}"""

VALIDATION_RELEVANT_CHECK_DICT = """4. Does the output align with the relevant task requirements? If the output deviates from the specified requirements, it should be rejected.

Relevant Task Requirements:
{relevant_requirements}"""

VALIDATION_RELEVANT_CHECK_STR = """4. Does the output align with the relevant task requirements? If the output deviates from the specified requirements, it should be rejected.

Relevant Task Requirements:
{relevant_requirements}"""

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
    output: str | BaseModel,
    output_names: dict[str, str] | None,
    output_what: str | None = None,
    relevant_requirements: str | None = None,
) -> list[str]:
    """Build messages for validating task output."""
    messages: list[str] = []

    for name, content in materials.items():
        messages.append(f"# {name}\n\n{content}")

    if isinstance(output, str):
        output_text = output
        if output_what is None:
            output_what = requirements
        validation_prompt = VALIDATION_PROMPT_STR.format(
            requirements=requirements,
            output_what=output_what,
            output_text=output_text,
            alignment_check=VALIDATION_RELEVANT_CHECK_STR.format(relevant_requirements=relevant_requirements) if relevant_requirements else ""
        )
    else:
        output_name_descriptions = [f"- `{k}`: {v}" for k, v in (output_names or {}).items()]
        output_names_text = "\n".join(output_name_descriptions)
        output_text = output.model_dump_json(indent=2)
        validation_prompt = VALIDATION_PROMPT_DICT.format(
            requirements=requirements,
            output_names_text=output_names_text,
            output_text=output_text,
            alignment_check=VALIDATION_RELEVANT_CHECK_DICT.format(relevant_requirements=relevant_requirements) if relevant_requirements else ""
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
