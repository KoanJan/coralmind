"""
Reproduce the task from agent.log - Story planning with specific materials.

This example reproduces a real task execution from agent.log:
- Materials: 题材类型, 全剧内容体量(总集数), 剧名
- Requirements: Story logic requirements
- Output Format: Complex JSON schema for story planning
"""

import json
import logging
import os
from coralmind import Agent, Language, LLMConfig, Material, OutputFormat, Task

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("coralmind").setLevel(logging.DEBUG)
logging.getLogger("coralmind").addHandler(logging.FileHandler("06.log"))

REQUIREMENTS = """
# 故事逻辑性要求\n# 故事逻辑性要求\n\n## 零、全局性\n\n- **解释**：某一句话单看没问题，但一旦结合上下文分析，可能出现其中某个人或物存在前后矛盾\n    - 例子\n        - 错误内容：A把雨伞扔车站垃圾桶了，上了公交车。A坐了半个小时。A下了车，雨还没停，于是打开了伞。\n        - 原因：A的雨伞在A上车前就被扔进出发站的垃圾桶里，因此A此时身上不应该有伞。这短内容中”雨伞“的位置违反了“物理空间一致性”。\n        - 附带说明：原内容总共三句话，每一句话单看都没问题，但是联系起来便存在逻辑问题。\n- **执行**：以下要求必须结合整个上下文分析判断\n\n## 一、因果性\n\n- 确保每个情节有明确的前因后果，且符合一般性逻辑。\n\n## 二、顺序性\n\n- 明确故事中各事件发生的先后顺序，且一旦确定不可更改。\n\n## 三、状态一致性\n\n- **人物或事物的状态如果发生改变，则一定经过某个过程。_如果这个过程本身不是剧情的悬念或线索_，则必须描述清楚发生了什么**\n    - 例子1: 花盆从完好变成破碎 -> 花盆一定经历了某个过程：可能是摔坏了或者被敲碎了等等或其他原因。\n    - 例子2: 某个配角死了 -> 一定有确切的死因。\n- **否则，确保人物或事物的状态前后一致**\n    - 例子1: 某件衣服挂在阳台 -> 假若没有外部因素影响，则这件衣服无论多久还是挂在阳台\n    - 例子2: A接起了电话 -> “通话中”是一个持续性的状态，但又不可能是永久性的，因此必须要在后续合适的时候明确描述其挂断行为\n\n## 四、人物反应合理性：\n\n- **动机必要性**\n    - **定义**：人物的每一个动作和每一句台词，都必须有清晰的内在或外在动机。\n    - **分析路径**：对于“某角色的某行为”->该角色为何这么做？->是否存在外部动机（该角色看到了什么？或听到了什么？）->\n      若有则结束，若无则判断是否存在内部动机->若有则结束，若无则说明【该行为不合理】\n    - **调整方案**：补充动机或删除行为\n- **动机充分性**\n    - **定义**：动机必须足够支撑人物的行为\n    - **分析路径**：对于某个角色的动机和对应行为->这个动机足以导致该角色这样做吗？是否显得太过夸张？->若是，则说明【动机虽存在但不足】\n    - **调整方案**：增强动机或削弱行为\n- **符合人类正常反应**\n    - **定义**：人物角色面对外界刺激的反应必须符合正常的人类反应，具体如何反应还需结合具体事件、场合、角色性格、背景等。\n    - **外部刺激**：人物角色看到的和听到的一切，都属于外部刺激\n    - **人物反应**：包含对白、动作、表情三种形式\n    - 【强制】**执行步骤**：（外界刺激）->正常人一般会会如何反应->故事背景是什么->当前角色设定是什么->\n      综上分析该角色如何反应才合理->（人物角色做出反应）\n    - 若执行完上述步骤后，人物反应与“正常人反应”偏差过大且无合理解释（如背景、设定、心理铺垫等），则视为【人物反应不合理】。\n    - 示例1：\n        - 外界刺激：“深夜小明下楼取宵夜时，看见一个白衣女子朝他飘了过去，白衣女子的脸没有五官”\n        - 思考路径：正常人面对这种情况会如何反应->故事背景是什么->小明的角色设定是什么->综合各方面因素判断小明应该如何反应才合理\n        - 可能性1（不止一种）：正常人会恐惧逃跑->故事背景是小明潜伏进来解决这个小区的灵异事件->小明设定是道士->\n          综上分析小明不仅不恐惧逃跑还会迎面战斗\n- **人类社会性**（符合人类社会的一般习惯）\n    1. _社交边界_：例如：私人聚会一般不允许外人在场、刚认识不久的人的相处模式与信任程度？等等其他。\n    2. _人之常情_：例如：面对突发情况时，考虑普通人的反应是怎么样的。\n- **动机合理性**\n    1. _符合人物角色的设定_\n    2. _默认人物动机一致连续，除非有变故_\n- **环境约束性**（当前物理/社会规则限制）\n- **可行性验证**\n    - 角色行为受物理规则约束（例：*重伤角色不能瞬间跃过5m宽悬崖*）\n\n## 五、物理空间一致性\n\n1. **位置唯一性**\n    - 禁止人物或事物同时存在于逻辑互斥的空间（例：*魔法剑不能同时在主角手中和城堡宝箱内*）\n2. **尺寸与空间匹配**\n    - 物体尺寸需符合容器/场景容量（例：*高度2m的巨人无法躲进1m高的橱柜*）\n    - 动态尺寸变化需守恒（例：*膨胀咒语使物体体积倍增时，周围物品应被挤压移位*）\n3. **位置移动无跳跃**\n    - 所有人物或事物的位置变化，必须要有明确的移动路径，确保不存在跳跃\n    - 实体间的相对位置同理\n        - 示例：\n            - 原内容：上一句写张三双手扛着箱子，下一句直接写张三拿着手机打字\n            - 问题：存在相对位置的改变但未描述清楚过程\n            - 修改方法：中间插入一句用于交代“箱子如何离开张三手里以及张三从哪里拿出手机”的动作过程\n\n## 六、语义与表述\n\n### A.语义要求\n\n1. **清晰**：确保所有用词意思明确，不存在含糊不清或歧义的情况\n    - **人物台词**：\n        - 要注意台词是谁对谁说的，是否存在人称错位问题\n        - 分析台词前后的背景情节是什么，是否存在台词与剧情出现矛盾的问题\n2. **准确**：确保所有用词正确合理，不存在误用或歧义的情况\n3. **语法**：部分省略句可能会导致歧义\n    - 例：\n        - 问题内容：张三（对着李四）：收下你的传家宝，就别担心了\n        - 问题原因：台词省略主语导致表述不清与歧义。谁收下李四的传家宝？后续的“担心”指的是担心什么？这句台词的意图是什么？嘲讽？安慰？\n        - 调整方案示例（需结合实际剧情）\n            - 调整方案1：张三（对着李四）：我到底如何收下你的传家宝，你就别担心了\n            - 调整方案2：张三（对着李四）：你赶紧收下你的传家宝吧，其他问题就别担心了\n\n### B.表述要求\n\n- **巧用虚词**：合理使用虚词可以使语句更加自然通顺\n    - 副词：修饰动词、形容词（如：非常、立刻、赶紧等）\n        - 例：”张三跑过去“（生硬）->“张三赶紧跑过去”（生动）\n    - 助词：辅助功能（如：了、着等）\n        - 例：”张三指文件说“（生硬）->“张三指着文件说”（使用“着”表示状态持续）\n        - 例：对话场景中，“吃完”（生硬）->“吃完了”（“了”表示完成状态，自然且符合口语习惯）\n        - 例：“张三笑，说”（生硬）->“张三笑了笑，说”（这里助词“了”表示“笑”的持续时间短且已完成，且符合口语习惯，自然）\n- **主谓合理性**\n    - 例：“手机跳起来”（不合理，手机不会跳）->“手机震了”（合理）\n- **【强制性要求】使用“主谓(助词/补语)宾”代替“主谓宾”**\n    - 同理要求：**使用“主谓(助词/补语)”代替“主谓”**\n    - 例：“张三看手机，说..”(主谓宾结构，生硬)->“张三看了下手机，说..”(主谓助宾结构，自然)\n    - 例：“张三拿那本书，说..”(主谓宾结构，生硬)->“张三拿出那本书，说..”(主谓助宾结构，自然)\n    - 例：“张三摇头”（生硬）->“张三摇了摇头”（自然）【主语+动词】->【主语+动词+“了”+动词】\n\n## 七、时间表述一致性\n\n1. **全局锚定**：关键事件的绝对时间与相对时间描述必须严格统一（例：禁止出现“台词暗示近期死亡，设定却是15年前”等矛盾）\n2. **跨度验证**：涉及时间跨度的设定需验证物理/社会合理性\n    - **物理合理性**：符合客观规律（例：中毒症状时长需匹配毒理特性）\n    - **社会合理性**：符合常理认知（例：遗产纠纷一般在死亡后1年内启动，不可能拖延15年）\n3. **角色语言**：角色台词中的时间表述需适配其身份认知（亲历者用具体时间点，非亲历者用相对时长或事件标签）\n\n## 八、自检清单\n\n1. 对所有出现外部刺激时的角色的反应（对白、动作、表情）表现的内容，是否都执行了“四、人物反应合理性-符合人类正常反应-执行步骤”？并且执行结果是“反应合理”？\n2. 人物和事物是否都满足“状态一致性”？\n3. 人物和事物是否都满足“物理空间一致性”？\n4. 所有人物的所有行为是否满足“动机必要性”和“动机充分性”？\n5. 是否符合“语义与表述”的相关要求？\n\n# 动态漫剧本主线设计要求\n# 动态漫剧本主线设计要求\n\n**执行目标：基于选定题材，完成一个目标具体、冲突可信、可落地的故事主线框架**\n\n---\n\n## 前置准备\n\n### 1.警惕过度“伟光正”\n\n- 原因：“伟光正”倾向，会导致你生成的剧情显“傻”、“降智”、“像小学生作文”等诸多负面效应，导致输出的内容不可用\n- 约束与逃离：仅确保输出的内容不涉及敏感即可，警惕过度“伟光正”倾向\n\n### 2.情绪价值导向\n\n- 先明确：观众对本剧的期待是什么？观众希望在每一集中看到什么？\n- 后确定：为了满足观众的期待，本剧应该主要提供何种爽点或爽感？\n- 这是最核心的一步，后续所有工作都围绕这一个元目标进行。\n\n### 3.黑名单内容\n\n- 范围：\n    - 禁止一切“口号式”、“情怀式”的内容（上到故事主题下到每一个词汇）。如：“守护”、“弘扬”、“成为最好的..”等一切相似的**语义**\n      （注意是语义，不仅是词汇）\n    - 禁止一切“科技”或“非遗文化”元素（**超自然设定不属于非遗文化**）\n- 反制方式：若出现则必须对整个语义进行更换，即便代价是改动剧情也必须执行（但要确保故事类型(`genre`)不变且修改后的内容与故事类型(`genre`)匹配），而不是仅仅替换词汇\n\n### 4.唤醒多视角意识\n\n剧本存在三大类视角：\n\n1. **上帝视角**，也就是编剧的视角\n2. **观众视角**\n3. **剧中各人物的视角**\n\n进行信息控制时，必须理清相关的视角。\n\n---\n\n### **第一步：明确题材，确定故事线结构**\n\n- **题材定义**\n- **故事线主副规则**：\n  - **情感题材**\n    - **热词识别**：“逆袭”、“穿越”或其他相近词汇\n    - **结构要求**：必须**以且仅以情感关系线为唯一主线**、其余方面（如事业）为辅助\n  - **其他**（无特殊要求）\n- 每条故事线都包含：起点状态、终点状态、过程概述（从起点到终点的过程）\n\n---\n\n### **第二步：基于故事线结构，定义【具体化】的核心冲突**\n\n- 为什么要基于故事线结构来定冲突？\n    - 原因：不同的故事线结构，主角的目标、反派的阻力等都不一样。\n\n- **执行规则**：\n    - 主角终极目标、反派核心阻力，这两项必须与第一步的主线同样类型（如：主线是感情线，那么这两项便必须是感情类型的）\n    - 第一步的副线，可以作为主线的载体、背景等，其作用是辅助主线，使其更加立体。\n    - **禁止口号化目标**：主角的终极目标必须是**一个具体的、可完成的行动或状态**，而非抽象的情怀或理念。应避免使用“守护”、“弘扬”、“成为最好”等空洞词汇。\n\n严格遵守**执行规则**，设计以下三项：\n\n1. 主角终极目标\n    - **要求**：必须具象化，包含**具体行动和可验证的结果**。\n    - **反例**：“守护社区的书香气”（抽象口号）、“夺回家产”（不够具体）。\n    - **正例**：“在六个月内，通过举办系列社区活动，使书店扭亏为盈，续签租约。”（行动：举办活动；结果：扭亏为盈、续签租约）\n2. 反派核心阻力\n    - **要求**：需直击痛点，阻碍主角达成上述具体目标。\n    - **正例**：“反派计划收购整条街区的物业，将书店所在楼宇改建为高端咖啡馆，并已开始暗中逼迁。”\n3. 不可妥协原因\n    - **要求**：解释为何双方在上述具体目标上无法退让。\n    - **正例**：“对反派而言，该商业项目是其晋升集团核心的业绩基石；对主角而言，书店是母亲的遗物和与社区的情感纽带，失去书店意味着背叛承诺和记忆。”\n\n---\n\n### **第三步：主角与反派的动机设计**\n\n这一步是为了让主角和反派的对抗具备强大的逻辑支撑，而不是强行凑戏。\n\n🔹 **主角绑定表**\n\n| 属性   | 设计要点                                         |  \n|------|----------------------------------------------|  \n| 核心需求 | ______（主角的内在驱动力，想要什么）                                       |  \n| 能力短板 | ______（能力层面的不足，例：口吃/无钱无权/旧伤复发）                       |  \n| 核心优势 | ______（能力层面的突出，**需能帮助其实现第二步的【具体目标】**，如：金手指、系统或其他等）   |\n| 软肋   | ______（情感/道德层面的弱点，例：重视家人/容易心软/有愧疚感）                 |\n\n🔹 **反派阻力表**\n\n| 属性   | 设计要点                          |  \n|------|-------------------------------|  \n| 表面身份 | ______（例：慈善家/董事长/养父）          |  \n| 恶行动机 | ______（需合理，例：掩盖年轻时强奸罪）        |  \n| 魅力标签 | ______（例：儒雅/虔诚教徒/爱动物）         |  \n| 资源   | 人脉/权力/资金/制度（例：控股集团/司法系统/黑帮网络） |  \n| 底线   | 绝不做/绝不认（例：不伤害家人/永不公开丑闻）       |\n\n----\n\n### **第四步：全局线索设计**\n\n设计至少1条全局线索，要求每条线索：\n\n1. 在故事前期埋设一次\n2. 在故事中期强化一次\n3. 在故事后期的颠覆性反转中触发回收\n\n----\n\n### **第五步：故事背景设定**\n\n1. **未出场关键角色状态**（例：【主角】父亲--15年前失踪/公司创始人/疑似被害）\n2. **世界规则**（例：【商战剧】上市公司股权变动需董事会70%投票通过）\n3. **关键道具**（例：【悬疑剧】带血的合同书--关联十年前绑架案）\n4. **前情/真相**：需要具体详细（最好包含细节），确保后续细化剧情时不会跑偏\n5. **金手指**（若有）：详细说明其功能、使用条件与使用限制\n\n----\n\n### **第六步：降低观看门槛与元素限制**\n\n1. 尽量避开专业领域的一切信息或知识，避免观众信息疲劳；\n    - 需要规避的专业领域包括但不限于：法律/金融/财务/科技/数学/政治等\n2. 尽量避免出现\"科技\"、\"技术\"、\"西方神话\"等元素。\n\n----\n\n### **第七步：检查复查**\n\n1. 故事线的主副结构是否严格遵守\"故事线主副规则\"？\n2. 故事线的主线类型是否与用户指定的题材背离？\n3. 黑名单内容是否出现在本大纲？若出现则必须对整个语义进行更换（即便代价是修改剧情）。\n\n\n# 剧情合理性要求\n# 剧情合理性检查\n\n## **一、角色动机合理性检查**\n对于某个角色的行为，进行以下分析：\n\n1. 该角色执行该行为时，他/她掌握了哪些信息？（视角局限性-避免上帝视角未卜先知）\n2. 该角色的更深层次的需求是什么？性格如何？本次行为是否违背该需求？（人物一致性-避免出现矛盾）\n3. 外部条件是否允许该角色完成该行为？是否排除了所有可能的外部阻力？（客观性）\n4. 时机问题：该角色之前是否具备足够的客观条件与主观意向执行该行为？如果之前便已具备，那么直到现在才执行该行为便明显不合理。\n5. 动机强度与行为匹配度：该角色的动机强度（如生存、尊严、利益、情感等对角色的重要程度）是否足以驱动当前行为？\n   - 动机是否具备**不可妥协性**是否存在更温和、低成本的替代方案，角色为何必须选择当前行为）\n   - 动机是否具备**累积性**若为突发行为，是否有短期强刺激铺垫；若为长期行为，是否有持续动机叠加）\n   - **行为强度是否与动机强度对等**（避免 “小动机大行为” 如因口角引发灭门，或 “大动机小行为” 如面临生死危机仅被动逃避）\n   - 兼顾适配具体角色的人设（如冲动型与隐忍型在面对同等遭遇时的反抗程度各不相同）\n\n## **二、现实合理性检查**\n\n1. 因果链条是否闭合；\n2. 人物行为动机是否成立；\n3. 场景与行为是否符合现实世界的常识与制度；\n4. 是否出现“编剧便利”“巧合性事件”“天降线索”；\n5. 是否存在时间线矛盾或信息重复；\n6. 是否存在逻辑空洞或无解释转折；\n7. 物品的物理结构或特征，是否严格按照其在真实世界中的实际结构或特征？未与真实世界的实际情况相悖？\n8. 剧情规划的表述是否确定唯一？是否存在模棱两可或提供多种选择的情况？\n\n\n\n# 最终交付物\n一个动态漫的故事主线架构（不含三大幕划分）。\n\n# 最终交付物内容要求\n1. 符合【题材类型】\n2. 符合【全剧内容体量(总集数)】\n3. 符合【剧名】\n4. 严格遵守【故事逻辑性要求】\n5. 严格遵守【动态漫剧本主线设计要求】\n6. 严格遵守【剧情合理性要求】\n7. 所有输出内容必须使用中文。
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
        model_id=os.environ.get("DEFAULT_MODEL_ID", "qwen-plus-latest"),
        base_url=os.environ.get("DEFAULT_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        api_key=os.environ.get("DEFAULT_API_KEY", ""),
    )

    planner_llm = LLMConfig(
        model_id=os.environ.get("PLANNER_MODEL_ID", "qwen-plus-latest"),
        base_url=os.environ.get("PLANNER_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        api_key=os.environ.get("PLANNER_API_KEY", ""),
    )

    validator_llm = LLMConfig(
        model_id=os.environ.get("VALIDATOR_MODEL_ID", "qwen-plus-latest"),
        base_url=os.environ.get("VALIDATOR_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        api_key=os.environ.get("VALIDATOR_API_KEY", ""),
    )

    agent = Agent(default_llm=llm, planner_llm=planner_llm, executor_llm=planner_llm, validator_llm=validator_llm)

    materials = [
        Material(name="题材类型", content="诸神擂台"),
        Material(name="全剧内容体量(总集数)", content="60集"),
        Material(name="剧名", content="诸神擂台：黑无常大战西方诸神"),
    ]

    task = Task(
        materials=materials,
        requirements=REQUIREMENTS,
        output_format=OutputFormat(json_schema=OUTPUT_FORMAT_JSON_SCHEMA),
        language=Language.CN,
    )

    print("=" * 80)
    print("Reproducing task from agent.log")
    print("=" * 80)
    print("\nMaterials:")
    for m in task.materials:
        print(f"  - {m.name}: {m.content}")
    print(f"\nRequirements: Story logic requirements (see code for details)")
    print(f"\nOutput Format: Complex JSON schema for story planning")
    print("=" * 80)

    try:
        result = agent.run(task)
        print("\n✅ Task completed successfully!")
        print(f"\nResult type: {type(result)}")
        if isinstance(result, dict):
            result_json = json.dumps(result, indent=2)
            print(f"Result: \n{result_json}")
        else:
            print(f"Result: \n{result}")
    except Exception as e:
        print(f"\n❌ Task failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
