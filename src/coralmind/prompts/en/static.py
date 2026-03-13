EVALUATION_STANDARD = """
## Task Execution Result Evaluation Standard

### 1. Concept Clarification

- **Deliverable**: The form of output produced by the task. For example, if the task is "write a short story", the deliverable is "a short story".
- **Requirements/Constraints**: Specific descriptions of the deliverable. For example, "a 3000-word sci-fi short story set on Mars".

Only when there is a deliverable can requirements be met. If there is no deliverable (e.g., nothing was written) or the deliverable form is wrong (e.g., asked to write a story but wrote an exposition), it should be directly judged as a low score.

### 2. Grading Criteria

| Score Range | Grade | Grading Conditions |
|-------------|-------|-------------------|
| 0-2 | Failed | Off-topic, or no deliverable (wrong deliverable form / no substantive output) |
| 3-4 | Poor | Correct deliverable type, but has logical errors or factual errors |
| 5-6 | Average | Correct deliverable type + Good logic, but did not complete all requirements |
| 7-8 | Good | Correct deliverable type + Good logic + Complete all requirements, but lacks depth or innovation |
| 9-10 | Excellent | Correct deliverable type + Good logic + Complete all requirements + Has depth or innovation |

### 3. Detailed Grading Conditions

#### Failed (0-2 points)

- Off-topic: Output content is completely irrelevant to task requirements
- No deliverable: No substantive output content, or wrong deliverable form (e.g., asked to write a story but wrote an exposition)

#### Poor (3-4 points)

- Correct deliverable type: Deliverable form matches task requirements (e.g., asked to write a story, actually wrote a story)
- Logical errors: Contains obvious logical contradictions or reasoning errors
- Factual errors: Contains obvious incorrect information or false content

#### Average (5-6 points)

- Correct deliverable type: Deliverable form matches task requirements
- Good logic: Clear logic, no obvious errors
- Incomplete requirements: Missed some requirements, but main task is completed

#### Good (7-8 points)

- Correct deliverable type: Deliverable form matches task requirements
- Good logic: Clear and coherent logic
- Complete all requirements: Meets all specific requirements of the task
- Lacks depth or innovation: Content is accurate but flat, lacks in-depth analysis or innovative perspective

#### Excellent (9-10 points)

- Correct deliverable type: Deliverable form matches task requirements
- Good logic: Clear and coherent logic, professional expression
- Complete all requirements: Meets all specific requirements of the task
- Has depth or innovation: Provides in-depth analysis, innovative perspective, or performance that exceeds expectations

### 4. Scoring Process

1. First determine if the deliverable type is correct
2. Check if logic is good
3. Check if all requirements are completed
4. Determine if there is depth or innovation
5. Determine the score range based on the highest level met

### 5. Examples

**Task Requirements**:
```text
Summarize the core points of this article and list the key data supporting each point
```

**Output Example A** (9 points):
- Completely summarized all core points
- Provided accurate data support for each point
- Clear structure, professional expression, in-depth analysis
- Grade: Correct deliverable type + Good logic + Complete all requirements + Has depth → 9-10 points

**Output Example B** (6 points):
- Summarized main points but missed secondary points
- Some data missing or inaccurate
- Average structure
- Grade: Correct deliverable type + Acceptable logic, but incomplete requirements → 5-6 points

**Output Example C** (3 points):
- Only mentioned partial points
- Contains obvious logical errors
- Grade: Correct deliverable type, but has logical errors → 3-4 points
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
