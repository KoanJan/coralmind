EVALUATION_STANDARD = """
## Task Execution Result Evaluation Standard

### 1. Evaluation Objective

Score the final output of AI task execution to assess how well the output meets the original task requirements.

### 2. Evaluation Dimensions

1. **Completeness** (Weight: 30%)
   - Whether all required content of the task is completed
   - Whether key information or steps are missing
   - Whether the output content is comprehensive

2. **Accuracy** (Weight: 30%)
   - Whether the output content is accurate and error-free
   - Whether there are factual errors
   - Whether the information is precise and reliable

3. **Relevance** (Weight: 25%)
   - Whether the output closely aligns with task requirements
   - Whether irrelevant content is included
   - Whether key points are highlighted

4. **Quality** (Weight: 15%)
   - Professionalism of the output
   - Clarity of expression
   - Coherence of logic

### 3. Scoring Criteria

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 9-10 | Excellent | Fully meets task requirements, exceptional performance across all dimensions, no obvious defects |
| 7-8 | Good | Basically meets task requirements, good performance across all dimensions, minor room for improvement |
| 5-6 | Average | Partially meets task requirements, obvious deficiencies in some dimensions |
| 3-4 | Poor | Barely completes the task, serious issues in multiple dimensions |
| 0-2 | Failed | Does not complete task requirements, extremely low output quality or off-topic |

### 4. Scoring Principles

1. **Objective and Fair**: Score based on task requirements and actual output, avoid subjective bias

2. **Comprehensive Consideration**: Comprehensively evaluate performance across all dimensions, not relying on a single aspect

3. **Strict Standards**: Give lower scores for missing key information or serious errors

4. **Recognize Excellence**: Give high scores for performance that exceeds expectations

### 5. Scoring Process

1. Carefully read the original task requirements
2. Thoroughly review the actual output content
3. Evaluate each dimension one by one
4. Give a final score (integer from 0-10) based on all dimensions

### 6. Examples

**Task Requirements**:
```text
Summarize the core points of this article and list the key data supporting each point
```

**Output Example A** (9 points):
- Completely summarized all core points
- Provided accurate data support for each point
- Clear structure, professional expression

**Output Example B** (6 points):
- Summarized main points but missed secondary points
- Some data missing or inaccurate
- Average structure

**Output Example C** (3 points):
- Only mentioned partial points
- Many data errors
- Confusing expression
"""


PLAN_STANDARD = r"""
## Execution Plan Standard

### 1. Core Concepts

An Execution Plan (Plan) is a structured approach that decomposes a complex task into multiple sequentially executed nodes. Each node (PlanNode) represents an execution step, and nodes form dependencies through inputs and outputs. The final node produces the task result.

### 2. Structure Description

A Plan contains a nodes list, where each PlanNode includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| id | string | Node identifier, unique within the plan, recommended to use semantic names like "analyze", "summarize" |
| input_fields | list[InputField] | Describes what input information this node requires |
| requirements | string | Describes the specific task this node undertakes |
| output_names | dict[str, str] \| null | Output fields and their definitions, format: `{"field_name": "field_definition"}` |
| is_final_node | boolean | Whether this is the final node |

InputField structure:

| Field | Type | Description |
|-------|------|-------------|
| source_type | enum | Input source type: "original_material" (original material) or "output_of_another_node" (output from another node) |
| material_name | string | When source_type is original_material, specifies the material name |
| output_of_another_node | object | When source_type is output_of_another_node, specifies the dependent node ID and output field name |

### 3. Planning Rules

1. **Node Count**: The plan must contain at least 1 node

2. **Node Order**: Nodes in the nodes list are executed in order. Depended nodes must appear before nodes that depend on them

3. **Final Node**:
   - There must be exactly one final node, located at the end of the nodes list
   - The final node's `is_final_node` must be `true`
   - The final node's `output_names` must be `null`

4. **Intermediate Nodes**:
   - Non-final nodes have `is_final_node` as `false`
   - Non-final nodes must define at least one output field (`output_names` not empty)
   - Output field content format must be string (str), meaning each node's output dict type is `dict[str, str]` not `dict[str, Any]`
   - In `output_names` field descriptions, clearly indicate that output content type is string

5. **Input Sources**:
   - When using `original_material` type, `material_name` must be a name that exists in user-provided materials
   - When using `output_of_another_node` type, the referenced node must exist and appear before the current node

6. **ID Uniqueness**: All node IDs must be unique within the plan

### 4. Design Principles

1. **Single Responsibility**: Each node should focus on one clear subtask

2. **Appropriate Granularity**: Nodes should not be too granular (like single-line operations) or too broad (like "complete the entire task")

3. **Clear Dependencies**: Clearly mark each node's input sources to ensure the execution chain is traceable

4. **Explicit Outputs**: Intermediate node output fields should have clear semantic definitions for subsequent nodes to understand and use

### 5. Example

```json
{
  "nodes": [
    {
      "id": "extract",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "article"
        }
      ],
      "requirements": "Extract all key information from the article, including main points, data, conclusions, etc.",
      "output_names": {
        "key_points": "List of extracted key points (string type)",
        "data_facts": "Data and facts from the article (string type)"
      },
      "is_final_node": false
    },
    {
      "id": "summarize",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "extract",
            "output_field_name": "key_points"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "extract",
            "output_field_name": "data_facts"
          }
        }
      ],
      "requirements": "Based on the extracted key points and data facts, write a concise summary",
      "output_names": null,
      "is_final_node": true
    }
  ]
}
```
"""
