OUTPUT_FORMAT_WITH_NAMES = """Output fields: {output_name_descriptions}."""

OUTPUT_FORMAT_WITHOUT_NAMES = "Return the final result directly. Do not include any content that is not part of the deliverable itself."

PLANNER_OUTPUT_FORMAT_SECTION = """

# Final Output Format
The final output will be formatted to match this schema after all nodes complete:
```json
{json_schema}
```

**Note**: This is for the FINAL output only, NOT for intermediate nodes. This is NOT a material and should NOT be referenced in input_fields.
"""

PLANNER_MESSAGE_TEMPLATE = """
# Task Input

## Materials (Available for input_fields)
{materials_names}

## Requirements
```text
{requirements}
```
{output_format_section}
# Your Task

Create a detailed execution plan based on the Task Input above. Do not directly complete the user's requirements.

**IMPORTANT**: When creating input_fields for each node, only reference materials from the "Materials" section above. Do NOT reference "Final Output Format" or any other items as materials.

# Execution Plan Standard
```text
{plan_standard}
```
"""

OLD_PLAN_ATTACHMENT = "# Attachment: Example of a good plan from past similar tasks\n\n```json\n{old_plan}\n```"

EXECUTOR_REQUIREMENTS = "The above are {material_names} respectively.\n\n{requirements}"

FORMAT_TO_SCHEMA = """
The above is the original output content.

# Your Task
Transform the original output into a valid JSON that strictly follows the JSONSchema below. Preserve all meaningful information from the original output.

# JSONSchema
```json
{json_schema}
```

# Return Format
Return ONLY the JSON object, without any markdown formatting, code blocks, or additional text.
"""

GLOBAL_REQUIREMENTS_CONTEXT = """# Global Task Background

This step is part of a larger task. The original overall requirement is:

```
{global_requirements}
```

Please keep this global goal in mind while executing the current step.
"""

REQUIREMENT_TREE_BUILD = """# Task

Build a structured tree from the following text segments. Each segment has an ID and content.

# Text Segments

{lines_text}

# Your Task

Organize these segments into a hierarchical tree structure:
1. Create meaningful categories and subcategories
2. Each leaf node should reference specific segment IDs via `scope`
3. Non-leaf nodes should have `children`, leaf nodes should have `scope`
4. `scope` format: `[[start_id, end_id], ...]` for continuous ranges
5. `name` should be concise, `description` should explain the node's content

**IMPORTANT**: The root node MUST be a non-leaf node (with `children`), and all leaf nodes' scopes combined MUST cover ALL segment IDs from 1 to the last segment ID. No segment should be lost.
"""

RELEVANT_REQUIREMENTS_CONTEXT = """# Relevant Task Requirements

The following requirements are relevant to the current step:

```
{relevant_requirements}
```

Please follow these requirements while executing the current task.
"""
