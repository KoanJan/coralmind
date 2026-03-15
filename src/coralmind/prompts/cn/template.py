FIX_MODEL_VALIDATION = """以下 JSON 存在验证错误：

```json
{json_string}
```

错误：{error_msg}

目标 schema：
```json_schema
{schema}
```

请修复 JSON 并仅返回修正后的 JSON。要求：
1. 输出必须严格符合目标 schema
2. 所有必填字段必须存在
3. 字段类型必须与 schema 定义匹配
4. 不要包含任何 markdown 格式或解释，仅返回原始 JSON"""

OUTPUT_FORMAT_WITH_NAMES = """返回一个 JSON 字典，包含以下字段：{output_name_descriptions}。

**重要提示**：字典中的所有值必须是字符串（str 类型），不能是数组、对象或嵌套结构。
- 如果需要返回多个项目，请将其格式化为单个字符串（例如换行分隔或 JSON 序列化）
- 正确格式示例：{{"items": "项目1\\n项目2\\n项目3"}}
- 错误格式示例：{{"items": ["项目1", "项目2", "项目3"]}}"""

OUTPUT_FORMAT_WITHOUT_NAMES = "直接返回最终结果。不要包含任何不属于交付物本身的内容。"

PLANNER_OUTPUT_FORMAT_SECTION = """

# 最终输出格式（JSON Schema）
所有节点完成后，最终输出将格式化为符合此 schema 的形式：
```json
{json_schema}
```

**重要约束**：
- 此 schema 仅用于最终输出，不适用于中间节点
- 每个中间节点必须输出 `dict[str, str]`，其中值为纯字符串
- 不要创建输出 JSON 数组或嵌套对象的节点
- 最终节点应输出包含所有内容的单个字符串
- JSON 格式化发生在执行之后，而非执行期间
- 这不是物料，不应在 input_fields 中引用
"""

PLANNER_MESSAGE_TEMPLATE = """
# 任务输入

## 物料（可用于 input_fields）
{materials_names}

## 要求
```text
{requirements}
```
{output_format_section}
# 你的任务

根据上述任务输入创建详细的执行计划。不要直接完成用户的要求。

**重要提示**：在为每个节点创建 input_fields 时，仅引用上方"物料"部分中的物料。不要将"最终输出格式"或任何其他项目作为物料引用。

# 执行计划规范
```text
{plan_standard}
```

# 返回格式（JSON Schema）
```json
{return_format_schema}
```
"""

OLD_PLAN_ATTACHMENT = "# 附件：过去类似任务的良好计划示例\n\n```json\n{old_plan}\n```"

EXECUTOR_REQUIREMENTS = "以上分别是 {material_names}。\n\n{requirements}"

FORMAT_TO_SCHEMA = """
以上是原始输出内容。

# 你的任务
将原始输出转换为严格遵循下方 JSONSchema 的有效 JSON。保留原始输出中的所有有意义信息。

# JSONSchema
```json
{json_schema}
```

# 返回格式
仅返回 JSON 对象，不要包含任何 markdown 格式、代码块或额外文本。
"""

GLOBAL_REQUIREMENTS_CONTEXT = """# 全局任务背景

本步骤是一个更大任务的一部分。原始的总体要求是：

```
{global_requirements}
```

请在执行当前步骤时牢记这一全局目标。
"""

REQUIREMENT_TREE_BUILD = """# 任务

根据以下文本片段构建结构化树。每个片段有 ID 和内容。

# 文本片段

{lines_text}

# 你的任务

将这些片段组织成层级树结构：
1. 创建有意义的分类和子分类
2. 每个叶子节点应通过 `scope` 引用具体的片段 ID
3. 非叶子节点应有 `children`，叶子节点应有 `scope`
4. `scope` 格式：`[[起始ID, 结束ID], ...]`，表示连续范围
5. `name` 应简洁，`description` 应说明该节点涵盖的内容

**重要**：根节点必须是非叶子节点（有 `children`），且所有叶子节点的 scope 合并后必须覆盖从 1 到最后一个片段 ID 的所有片段。不允许任何片段丢失。

# 返回格式（JSON Schema）

```json
{{
  "name": "字符串 - 该节点的简洁名称",
  "description": "字符串 - 描述该节点涵盖的内容",
  "children": [...],  // 非叶子节点使用，子节点列表
  "scope": [[1, 5], [10, 15]]  // 仅叶子节点使用，片段 ID 范围
}}
```

仅返回树的根节点（必须有 children）。树的深度应为 2-4 层。
"""

RELEVANT_REQUIREMENTS_CONTEXT = """# 相关任务要求

以下要求与当前步骤相关：

```
{relevant_requirements}
```

请在执行当前任务时遵循这些要求。
"""
