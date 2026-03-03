PLAN_STANDARD = r"""
## 执行计划的规范

### 一、核心概念

执行计划（Plan）是将复杂任务分解为多个有序执行节点的结构化方案。每个节点（PlanNode）代表一个执行步骤，节点之间通过输入输出形成依赖关系，最终节点产出任务结果。

### 二、结构说明

Plan包含一个nodes列表，每个PlanNode包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 节点标识，计划内唯一，建议使用语义化命名如"analyze"、"summarize" |
| input_fields | list[InputField] | 描述该节点需要哪些输入信息 |
| requirements | string | 描述该节点承当的具体任务 |
| output_names | dict[str, str] \| null | 输出字段及其定义，格式为 `{"字段名": "字段定义"}` |
| is_final_node | boolean | 是否为最终节点 |

InputField结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| source_type | enum | 输入来源类型："original_material"（原始物料）或 "output_of_another_node"（其他节点输出） |
| material_name | string | 当source_type为original_material时，指定物料名称 |
| output_of_another_node | object | 当source_type为output_of_another_node时，指定依赖的节点ID和输出字段名 |

### 三、制定规则

1. **节点数量**：计划必须包含至少1个节点

2. **节点顺序**：nodes列表中的节点按顺序执行，被依赖的节点必须排在依赖它的节点之前

3. **最终节点**：
   - 有且仅有一个最终节点，位于nodes列表末尾
   - 最终节点的 `is_final_node` 必须为 `true`
   - 最终节点的 `output_names` 必须为 `null`

4. **中间节点**：
   - 非最终节点的 `is_final_node` 为 `false`
   - 非最终节点必须定义至少一个输出字段（`output_names` 不为空）
   - 输出字段的内容格式必须为字符串（str），即每个节点的输出 dict 类型为 `dict[str, str]` 而非 `dict[str, Any]`
   - 在 `output_names` 的字段描述中，应明确标注输出内容的类型为字符串（string）

5. **输入来源**：
   - 使用 `original_material` 类型时，`material_name` 必须是用户提供的物料中存在的名称
   - 使用 `output_of_another_node` 类型时，引用的节点必须存在且位于当前节点之前

6. **ID唯一性**：所有节点的id在计划内必须唯一

### 四、设计原则

1. **职责单一**：每个节点应专注于一个明确的子任务

2. **粒度适中**：节点不宜过于细碎（如单行操作）或过于宽泛（如"完成整个任务"）

3. **依赖清晰**：明确标注每个节点的输入来源，确保执行链路可追溯

4. **输出明确**：中间节点的输出字段应具有清晰的语义定义，便于后续节点理解和使用

### 五、示例

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
      "requirements": "从文章中提取所有关键信息，包括主要观点、数据、结论等",
      "output_names": {
        "key_points": "提取的关键要点列表（string 类型）",
        "data_facts": "文章中的数据和事实（string 类型）"
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
      "requirements": "基于提取的关键要点和数据事实，撰写一份简洁的摘要",
      "output_names": null,
      "is_final_node": true
    }
  ]
}
```
"""
