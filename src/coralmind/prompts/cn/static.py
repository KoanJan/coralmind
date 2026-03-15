EVALUATION_STANDARD = """
## 任务执行结果评分标准

### 一、概念说明

- **交付（Deliverable）**：任务产出的成果形式。例如任务是"写一篇短故事"，那么交付就是"一篇短故事"。
- **要求/约束（Requirements/Constraints）**：对交付物的具体描述。例如"一篇3000字的科幻短故事，背景设定在火星"。

只有先有交付，才谈得上满足要求。如果没有交付（如没写任何内容），或交付形式错误（如要求写故事却写了说明文），则直接判定为低分。

### 二、评级标准

| 分数段 | 等级 | 评级条件 |
|--------|------|----------|
| 0-2 | 不合格 | 偏离主题、或无交付（交付形式错误/无实质性输出） |
| 3-4 | 较差 | 交付类型正确，但存在逻辑错误或客观事实错误 |
| 5-6 | 中等 | 交付类型正确 + 逻辑良好，但未完成所有要求 |
| 7-8 | 良好 | 交付类型正确 + 逻辑良好 + 完成所有要求，但缺乏深度或创新 |
| 9-10 | 优秀 | 交付类型正确 + 逻辑良好 + 完成所有要求 + 具有深度或创新 |

### 三、各级评级条件详解

#### 不合格（0-2分）

- 偏离主题：输出内容与任务要求完全不相关
- 无交付：没有任何实质性输出内容，或交付形式错误（如要求写故事却写了说明文）

#### 较差（3-4分）

- 交付类型正确：交付形式符合任务要求（如要求写故事，实际写了故事）
- 逻辑错误：存在明显的逻辑矛盾或推理错误
- 客观事实错误：存在明显的错误信息或虚假内容

#### 中等（5-6分）

- 交付类型正确：交付形式符合任务要求
- 逻辑良好：逻辑清晰，无明显错误
- 未完成所有要求：遗漏了部分要求，但主要任务已完成

#### 良好（7-8分）

- 交付类型正确：交付形式符合任务要求
- 逻辑良好：逻辑清晰连贯
- 完成所有要求：满足任务的所有具体要求
- 缺乏深度或创新：内容准确但较为平淡，缺乏深入分析或创新视角

#### 优秀（9-10分）

- 交付类型正确：交付形式符合任务要求
- 逻辑良好：逻辑清晰连贯，表达专业
- 完成所有要求：满足任务的所有具体要求
- 具有深度或创新：提供深入分析、创新视角、或超出预期的表现

### 四、评分流程

1. 首先判断交付类型是否正确
2. 检查逻辑是否良好
3. 检查是否完成所有要求
4. 判断是否有深度或创新
5. 根据满足的最高级别确定分数区间

### 五、示例

**任务要求**：
```text
请总结这篇文章的核心观点，并列出支持每个观点的关键数据
```

**输出示例 A** (9 分)：
- 完整总结了所有核心观点
- 为每个观点提供了准确的数据支持
- 结构清晰，表达专业，有深入分析
- 评级：交付类型正确 + 逻辑良好 + 完成所有要求 + 有深度 → 9-10 分

**输出示例 B** (6 分)：
- 总结了主要观点但遗漏了次要观点
- 部分数据缺失或不准确
- 结构一般
- 评级：交付类型正确 + 逻辑尚可，但未完成所有要求 → 5-6 分

**输出示例 C** (3 分)：
- 仅提及部分观点
- 包含明显的逻辑错误
- 评级：交付类型正确，但存在逻辑错误 → 3-4 分
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
| output_constraints | OutputConstraints | 输出约束，包含输出类型、字段定义和内容规格 |
| is_final_node | boolean | 是否为最终节点 |

InputField结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| source_type | enum | 输入来源类型："original_material"（原始物料）或 "output_of_another_node"（其他节点输出） |
| material_name | string | 当source_type为original_material时，指定物料名称 |
| output_of_another_node | object | 当source_type为output_of_another_node时，指定依赖的节点ID和输出字段名 |

OutputConstraints结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| output_type | enum | 输出类型："text"（纯文本）或 "model"（结构化模型） |
| fields | dict[str, str] \| null | 当output_type为model时，定义输出字段及其描述，格式为 `{"字段名": "字段描述"}` |
| content_spec | string | 内容规格，描述期望输出的内容特征，用于语义验证 |

### 三、制定规则

1. **节点数量**：计划必须包含至少1个节点

2. **节点顺序**：nodes列表中的节点按顺序执行，被依赖的节点必须排在依赖它的节点之前

3. **最终节点**：
   - 有且仅有一个最终节点，位于nodes列表末尾
   - 最终节点的 `is_final_node` 必须为 `true`
   - 最终节点的 `output_constraints.output_type` 应为 `text`
   - 最终节点的 `output_constraints.fields` 应为 `null`

4. **中间节点**：
   - 非最终节点的 `is_final_node` 为 `false`
   - 非最终节点应使用 `model` 类型的输出（`output_type` 为 `model`），以便后续节点可以引用具体的输出字段
   - 必须定义至少一个输出字段（`fields` 不为空）
   - 输出字段的内容格式必须为字符串（str），即每个节点的输出类型为 `dict[str, str]` 而非 `dict[str, Any]`
   - 在 `fields` 的字段描述中，应明确标注输出内容的类型为字符串（string）

5. **输入来源**：
   - 使用 `original_material` 类型时，`material_name` 必须是用户提供的物料中存在的名称
   - 使用 `output_of_another_node` 类型时，引用的节点必须存在且位于当前节点之前

6. **ID唯一性**：所有节点的id在计划内必须唯一

7. **内容规格**：每个节点的 `content_spec` 应清晰描述期望的输出内容特征，便于验证输出是否符合预期

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
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "key_points": "提取的关键要点列表（string 类型）",
          "data_facts": "文章中的数据和事实（string 类型）"
        },
        "content_spec": "从文章中提取的关键信息，包含主要观点和数据事实"
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
      "output_constraints": {
        "output_type": "text",
        "fields": null,
        "content_spec": "一份简洁的文章摘要"
      },
      "is_final_node": true
    }
  ]
}
```
"""
