FIX_DICT_STRUCTURE = """The following JSON has a structure error:

```json
{json_string}
```

Error: {error_msg}

Please fix the JSON and return ONLY the corrected JSON. Requirements:
1. The output must be a JSON object (dict), not an array
2. All values must be strings (str), not arrays or nested objects
3. If you need to represent multiple items, use newline-separated strings or JSON-stringified strings
4. Do not include any markdown formatting or explanations, just the raw JSON"""

FIX_MODEL_VALIDATION = """The following JSON has validation errors:

```json
{json_string}
```

Error: {error_msg}

Target schema:
```json_schema
{schema}
```

Please fix the JSON and return ONLY the corrected JSON. Requirements:
1. The output must conform to the target schema exactly
2. All required fields must be present
3. Field types must match the schema definitions
4. Do not include any markdown formatting or explanations, just the raw JSON"""

OUTPUT_FORMAT_WITH_NAMES = """Return a JSON dictionary containing the following fields: {output_name_descriptions}.

**CRITICAL**: All values in the dictionary MUST be strings (str type), NOT arrays, objects, or nested structures.
- If you need to return multiple items, format them as a single string (e.g., newline-separated or JSON stringified)
- Example of CORRECT format: {{"items": "item1\\nitem2\\nitem3"}}
- Example of WRONG format: {{"items": ["item1", "item2", "item3"]}}"""

OUTPUT_FORMAT_WITHOUT_NAMES = "Return the final result directly. Do not include any content that is not part of the deliverable itself."

PLANNER_OUTPUT_FORMAT_SECTION = """

# Final Output Format (JSON Schema)
The final output will be formatted to match this schema after all nodes complete:
```json
{json_schema}
```

**CRITICAL CONSTRAINTS**:
- This schema is for the FINAL output only, NOT for intermediate nodes
- Each intermediate node must output `dict[str, str]` where values are plain strings
- Do NOT create nodes that output JSON arrays or nested objects
- The final node should output a single string containing all content
- JSON formatting happens AFTER execution, not during
- This is NOT a material and should NOT be referenced in input_fields
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

# Return Format (JSON Schema)
```json
{return_format_schema}
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

# Return Format (JSON Schema)

```json
{{
  "name": "string - concise name for this node",
  "description": "string - description of what this node covers",
  "children": [...],  // for non-leaf nodes, list of child nodes
  "scope": [[1, 5], [10, 15]]  // for leaf nodes only, segment ID ranges
}}
```

Return ONLY the root node of the tree (which MUST have children). The tree should have 2-4 levels of depth.
"""

RELEVANT_REQUIREMENTS_CONTEXT = """# Relevant Task Requirements

The following requirements are relevant to the current step:

```
{relevant_requirements}
```

Please follow these requirements while executing the current task.
"""
