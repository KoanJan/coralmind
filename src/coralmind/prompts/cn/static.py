EVALUATION_STANDARD = """
## 任务执行结果评分标准

### 一、评分目标

对 AI 执行任务的最终输出进行评分，评估输出结果对于原始任务要求的满足程度。

### 二、评分维度

1. **完整性** (权重：30%)
   - 是否完成了任务要求的所有内容
   - 是否遗漏了关键信息或步骤
   - 输出内容是否全面

2. **准确性** (权重：30%)
   - 输出内容是否准确无误
   - 是否存在事实性错误
   - 信息是否精确可靠

3. **相关性** (权重：25%)
   - 输出是否紧扣任务要求
   - 是否包含无关内容
   - 重点是否突出

4. **质量** (权重：15%)
   - 输出的专业性
   - 表达的清晰度
   - 逻辑的连贯性

### 三、评分标准

| 分数段 | 等级 | 描述 |
|--------|------|------|
| 9-10 | 优秀 | 完全满足任务要求，各维度表现卓越，无明显缺陷 |
| 7-8 | 良好 | 基本满足任务要求，各维度表现良好，有少量可改进之处 |
| 5-6 | 中等 | 部分满足任务要求，某些维度存在明显不足 |
| 3-4 | 较差 | 仅勉强完成任务，多个维度存在严重问题 |
| 0-2 | 不合格 | 未完成任务要求，输出质量极低或偏离主题 |

### 四、评分原则

1. **客观公正**：基于任务要求和实际输出进行评分，避免主观偏见

2. **综合考量**：综合考虑各维度表现，不单一依赖某个方面

3. **严格要求**：对于关键信息缺失或严重错误应给予较低分数

4. **鼓励优秀**：对于超出预期的表现应给予高分认可

### 五、评分流程

1. 仔细阅读任务的原始要求
2. 全面审阅实际输出内容
3. 按照四个维度逐一评估
4. 综合各维度给出最终分数 (0-10 的整数)

### 六、示例

**任务要求**：
```text
请总结这篇文章的核心观点，并列出支持每个观点的关键数据
```

**输出示例 A** (9 分)：
- 完整总结了所有核心观点
- 为每个观点提供了准确的数据支持
- 结构清晰，表达专业

**输出示例 B** (6 分)：
- 总结了主要观点但遗漏了次要观点
- 部分数据缺失或不准确
- 结构一般

**输出示例 C** (3 分)：
- 仅提及部分观点
- 数据错误较多
- 表达混乱
"""


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
