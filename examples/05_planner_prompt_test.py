"""
Test case for Planner prompt fix - prevent LLM from misinterpreting output_format as material.

This example reproduces a real-world scenario where LLM incorrectly referenced
"Final Output Format" as an original material in the execution plan.

Expected behavior after fix:
- LLM should NOT reference "Final Output Format" in input_fields
- LLM should only reference materials from the "Materials" section
"""

import json
import logging
import os
from coralmind import Agent, Language, LLMConfig, Material, OutputFormat, Task

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
logging.getLogger("coralmind").setLevel(logging.DEBUG)

MATERIAL_NAMES = [
    "用户指定主副线",
    "情绪价值设定(含爽点、核心冲突、观众期待)",
    "题材类型",
    "全剧内容体量(总集数)",
]

REQUIREMENTS = """
# 故事逻辑性要求

## 零、全局性
- 解释：某一句话单看没问题，但一旦结合上下文分析，可能出现其中某个人或物存在前后矛盾

## 一、因果性
- 确保每个情节有明确的前因后果，且符合一般性逻辑。

## 二、顺序性
- 明确故事中各事件发生的先后顺序，且一旦确定不可更改。

## 三、状态一致性
- 人物或事物的状态如果发生改变，则一定经过某个过程。

## 四、人物反应合理性
- 动机必要性：人物的每一个动作和每一句台词，都必须有清晰的内在或外在动机。
- 动机充分性：动机必须足够支撑人物的行为。
- 符合人类正常反应：人物角色面对外界刺激的反应必须符合正常的人类反应。

## 五、物理空间一致性
- 位置唯一性：禁止人物或事物同时存在于逻辑互斥的空间。
- 位置移动无跳跃：所有人物或事物的位置变化，必须要有明确的移动路径。

## 六、语义与表述
- 台词要求：要注意台词是谁对谁说的，是否存在人称错位问题。
- 表述要求：确保所有用词正确合理，不存在误用或歧义的情况。
"""

OUTPUT_FORMAT_JSON_SCHEMA = json.dumps({
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": {
        "antagonistMotive": {
            "properties": {
                "name": {"type": "string", "maxLength": 4, "minLength": 2, "description": "反派姓名"},
                "motive": {"type": "string", "description": "恶行动机"},
                "charismatic_label": {"type": "string", "description": "魅力标签"},
                "sources": {"type": "string", "description": "拥有的资源"},
                "bottom_line": {"type": "string", "description": "底线"}
            },
            "additionalProperties": False,
            "type": "object",
            "required": ["name", "motive", "charismatic_label", "sources", "bottom_line"]
        },
        "characterProfile": {
            "properties": {
                "name": {"type": "string", "description": "人物姓名"},
                "role": {"type": "string", "description": "角色定位（主角/反派/配角）"},
                "sex": {"type": "string", "description": "性别"},
                "age": {"type": "integer", "description": "年龄（可选）"},
                "appearance": {"type": "string", "description": "外貌特征"},
                "occupation": {"type": "string", "description": "职业"},
                "personality_strengths": {"type": "string", "description": "性格优点"},
                "personality_weaknesses": {"type": "string", "description": "性格缺点"},
                "contrasting_label": {"type": "string", "description": "反差标签"},
                "external_goal": {"type": "string", "description": "外在目标"},
                "internal_need": {"type": "string", "description": "内在需求"}
            },
            "additionalProperties": False,
            "type": "object",
            "required": ["name", "role", "sex"]
        },
        "coreConflict": {
            "properties": {
                "protagonist_desire": {"type": "string", "description": "主角终极欲望"},
                "antagonist_resistance": {"type": "string", "description": "反派核心阻力"},
                "irreconcilability": {"type": "string", "description": "不可妥协原因"}
            },
            "additionalProperties": False,
            "type": "object",
            "required": ["protagonist_desire", "antagonist_resistance", "irreconcilability"]
        },
        "storyPlanResponse": {
            "properties": {
                "genre": {"type": "string", "description": "题材类型"},
                "synopsis": {"type": "string", "description": "故事梗概"},
                "core_conflict": {"$ref": "#/$defs/coreConflict"},
                "characters": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/characterProfile"},
                    "description": "人物设定列表"
                },
                "antagonist_motive": {"$ref": "#/$defs/antagonistMotive"}
            },
            "additionalProperties": False,
            "type": "object",
            "required": ["genre", "synopsis", "core_conflict", "characters", "antagonist_motive"]
        }
    },
    "$ref": "#/$defs/storyPlanResponse"
}, ensure_ascii=False, indent=2)


def main():
    llm = LLMConfig(
        model_id=os.environ.get("DEFAULT_MODEL_ID", "gpt-4o-mini"),
        base_url=os.environ.get("DEFAULT_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("DEFAULT_API_KEY", ""),
    )

    agent = Agent(default_llm=llm)

    materials = [
        Material(name=name, content=f"【{name}】的具体内容...")
        for name in MATERIAL_NAMES
    ]

    task = Task(
        materials=materials,
        requirements=REQUIREMENTS,
        output_format=OutputFormat(json_schema=OUTPUT_FORMAT_JSON_SCHEMA),
        language=Language.CN,
    )

    print("=" * 60)
    print("Testing Planner prompt fix")
    print("=" * 60)
    print("\nMaterials:")
    for m in task.materials:
        print(f"  - {m.name}")
    print(f"\nOutput Format: JSON Schema (complex structure)")
    print("\nExpected: LLM should NOT reference 'Final Output Format' as material")
    print("=" * 60)

    try:
        result = agent.run(task)
        print("\n✅ SUCCESS: Plan generated without errors!")
        print(f"\nResult type: {type(result)}")
    except Exception as e:
        error_msg = str(e)
        if "Final Output Format" in error_msg or "not found in task template" in error_msg:
            print(f"\n❌ FAILED: LLM incorrectly referenced output_format as material")
            print(f"Error: {error_msg}")
        else:
            print(f"\n❌ FAILED with other error: {error_msg}")
        raise


if __name__ == "__main__":
    main()
