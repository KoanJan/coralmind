import json

plan_example_json = """
{
  "nodes": [
    {
      "id": "analyze_market",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "market_report",
          "output_of_another_node": null
        }
      ],
      "requirements": "分析市场报告中的市场规模与增长、主要产品类别、技术趋势及挑战与风险，提炼市场现状总结和关键趋势",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "market_summary": "市场规模、增长情况、主要产品类别等现状的总结",
          "key_trends": "市场中的技术趋势（如Matter协议、AI大模型、边缘计算等）及增长趋势"
        },
        "content_spec": "从市场报告中提取关键信息，形成结构化的市场分析结果"
      },
      "is_final_node": false
    },
    {
      "id": "analyze_competitors",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "competitor_analysis",
          "output_of_another_node": null
        }
      ],
      "requirements": "分析竞品分析中的各竞争对手（A、B、C、D公司）的市场份额、核心产品、定价策略、优势劣势及最新动向，总结竞品核心信息并识别差异化机会",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "competitor_summary": "各竞品的核心信息（市场份额、产品、定价、优劣势）总结",
          "differentiation_opportunities": "竞品未覆盖或薄弱的市场/产品/功能领域"
        },
        "content_spec": "从竞品分析中提取关键信息，识别市场机会"
      },
      "is_final_node": false
    },
    {
      "id": "analyze_users",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "user_survey",
          "output_of_another_node": null
        }
      ],
      "requirements": "分析用户调研中的用户画像分布、购买动机、痛点反馈及期望功能，总结用户需求现状并排序核心痛点",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "user_demand_summary": "用户画像、购买动机、期望功能等需求现状的总结",
          "core_pains_ranking": "用户反馈的核心痛点（如APP混乱、联动问题、安装复杂等）按优先级排序"
        },
        "content_spec": "从用户调研中提取需求洞察，形成结构化的用户分析结果"
      },
      "is_final_node": false
    },
    {
      "id": "define_target_market",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_market",
            "output_field_name": "key_trends"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_competitors",
            "output_field_name": "differentiation_opportunities"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_users",
            "output_field_name": "user_demand_summary"
          }
        }
      ],
      "requirements": "结合市场关键趋势、竞品差异化机会及用户需求总结，选择目标细分市场（如智能安防+智能照明组合、智能温控+能源管理等）并说明选择理由",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "target_market": "选择的目标细分市场（如智能安防+智能照明一体化解决方案）",
          "target_market_reason": "选择该细分市场的理由（基于市场增长潜力、竞品空白、用户需求强度的综合分析）"
        },
        "content_spec": "基于多维度分析，明确目标细分市场定位"
      },
      "is_final_node": false
    },
    {
      "id": "define_user_profile",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_target_market",
            "output_field_name": "target_market"
          }
        },
        {
          "source_type": "original_material",
          "material_name": "user_survey",
          "output_of_another_node": null
        }
      ],
      "requirements": "基于目标细分市场及用户调研中的年龄、城市等级、收入水平、住房情况等画像数据，定义核心用户群体的具体特征（需覆盖 demographic、行为习惯、需求偏好等维度）",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "core_user_profile": "核心用户群体特征（如26-35岁、新一线/二线城市、月入1-2万、自有住房的年轻夫妻，关注家居安全与生活便利性）"
        },
        "content_spec": "定义清晰的目标用户画像"
      },
      "is_final_node": false
    },
    {
      "id": "define_product_positioning",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_competitors",
            "output_field_name": "differentiation_opportunities"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_users",
            "output_field_name": "core_pains_ranking"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_user_profile",
            "output_field_name": "core_user_profile"
          }
        }
      ],
      "requirements": "结合竞品差异化机会、用户核心痛点及目标用户画像，制定产品定位声明（需明确目标用户、核心价值、差异化优势）及差异化卖点（需具体可感知）",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "product_positioning": "产品定位声明（如为年轻家庭提供高性价比的智能安防+照明一体化解决方案，解决多设备联动与安装复杂问题）",
          "differentiation_selling_points": "差异化卖点列表（如统一APP控制所有设备、支持Matter协议跨品牌联动、15分钟快速安装）"
        },
        "content_spec": "制定清晰的产品定位和差异化策略"
      },
      "is_final_node": false
    },
    {
      "id": "plan_product_portfolio",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "market_report",
          "output_of_another_node": null
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_users",
            "output_field_name": "core_pains_ranking"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_competitors",
            "output_field_name": "competitor_summary"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_target_market",
            "output_field_name": "target_market"
          }
        }
      ],
      "requirements": "基于目标市场的产品类别（来自市场报告）、用户需求的功能优先级（来自用户调研）、竞品的产品组合（来自竞品分析），规划产品组合（需覆盖核心产品、扩展产品）并排序优先级（需说明排序理由）",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "product_portfolio": "产品组合列表（如核心产品：智能门锁、智能摄像头；扩展产品：智能灯泡、智能开关）",
          "portfolio_priority": "产品优先级排序及理由（如先做智能门锁（用户对安全性需求最高，竞品B公司在该领域有一定份额但性价比不足），再做智能摄像头（与门锁形成安防组合，提升用户粘性））"
        },
        "content_spec": "规划合理的产品组合和优先级"
      },
      "is_final_node": false
    },
    {
      "id": "set_pricing_strategy",
      "input_fields": [
        {
          "source_type": "original_material",
          "material_name": "user_survey",
          "output_of_another_node": null
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_competitors",
            "output_field_name": "competitor_summary"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_product_positioning",
            "output_field_name": "product_positioning"
          }
        }
      ],
      "requirements": "结合用户调研中的价格接受度（如1000-2000元价格区间占比35%）、竞品的定价策略（如B公司中端定价1500元）及产品定位（如中端高性价比），制定产品价格区间（需覆盖单产品与套装）并说明理由",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "price_ranges": "产品价格区间（如智能门锁：800-1200元；智能摄像头：500-800元；安防+照明套装：1500-2500元）",
          "pricing_reason": "定价理由（基于用户接受度、竞品定价、产品定位的综合分析，如智能门锁定价800-1200元，低于A公司的2800元，高于D公司的600元，符合中端高性价比定位）"
        },
        "content_spec": "制定有竞争力的定价策略"
      },
      "is_final_node": false
    },
    {
      "id": "plan_core_features",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_users",
            "output_field_name": "core_pains_ranking"
          }
        },
        {
          "source_type": "original_material",
          "material_name": "user_survey",
          "output_of_another_node": null
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_market",
            "output_field_name": "key_trends"
          }
        }
      ],
      "requirements": "结合用户核心痛点（如设备太多，APP太乱）、期望功能（如统一控制平台）及市场技术趋势（如Matter协议），规划产品核心功能（需具体可落地）并说明每个功能解决的用户痛点",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "core_features": "核心功能列表（如统一控制APP、支持Matter协议联动、智能场景自动化、AI语音助手集成大模型、15分钟快速安装）",
          "features_pain_solution": "每个核心功能解决的用户痛点（如统一控制APP解决设备太多APP太乱的痛点；Matter协议联动解决不同品牌不能联动的痛点）"
        },
        "content_spec": "规划解决用户痛点的核心功能"
      },
      "is_final_node": false
    },
    {
      "id": "identify_success_risk",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_market",
            "output_field_name": "key_trends"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_competitors",
            "output_field_name": "competitor_summary"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "analyze_users",
            "output_field_name": "core_pains_ranking"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_target_market",
            "output_field_name": "target_market"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_product_positioning",
            "output_field_name": "differentiation_selling_points"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_product_portfolio",
            "output_field_name": "product_portfolio"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "set_pricing_strategy",
            "output_field_name": "price_ranges"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_core_features",
            "output_field_name": "core_features"
          }
        }
      ],
      "requirements": "基于市场趋势、竞品情况、用户需求及产品策略各部分（目标市场、产品定位、产品组合、定价、核心功能），识别进入市场的关键成功要素（需具体可执行）及风险提示（需明确风险点及应对建议）",
      "output_constraints": {
        "output_type": "model",
        "fields": {
          "key_success_factors": "进入市场的关键成功要素列表（如快速建立线上线下渠道覆盖、确保产品支持Matter协议联动、提供1对1安装指导服务）",
          "risk_tips": "风险提示列表及应对建议（如数据隐私问题：采用端到端加密技术；安装复杂度：开发智能引导式安装APP）"
        },
        "content_spec": "识别关键成功要素和潜在风险"
      },
      "is_final_node": false
    },
    {
      "id": "compile_strategy",
      "input_fields": [
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_target_market",
            "output_field_name": "target_market"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_target_market",
            "output_field_name": "target_market_reason"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_user_profile",
            "output_field_name": "core_user_profile"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_product_positioning",
            "output_field_name": "product_positioning"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "define_product_positioning",
            "output_field_name": "differentiation_selling_points"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_product_portfolio",
            "output_field_name": "product_portfolio"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_product_portfolio",
            "output_field_name": "portfolio_priority"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "set_pricing_strategy",
            "output_field_name": "price_ranges"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "set_pricing_strategy",
            "output_field_name": "pricing_reason"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_core_features",
            "output_field_name": "core_features"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "plan_core_features",
            "output_field_name": "features_pain_solution"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "identify_success_risk",
            "output_field_name": "key_success_factors"
          }
        },
        {
          "source_type": "output_of_another_node",
          "material_name": "",
          "output_of_another_node": {
            "node_id": "identify_success_risk",
            "output_field_name": "risk_tips"
          }
        }
      ],
      "requirements": "将目标市场定位、目标用户画像、产品定位与差异化策略、产品组合建议、定价策略、核心功能规划、关键成功要素及风险提示整合，形成符合用户原始要求的完整产品策略方案（需逻辑清晰、数据驱动、可执行性强）",
      "output_constraints": {
        "output_type": "text",
        "fields": null,
        "content_spec": "一份完整的产品策略方案，包含目标市场定位、用户画像、产品定位与差异化、产品组合、定价策略、核心功能、关键成功要素及风险提示等章节，逻辑清晰、数据驱动、可执行性强"
      },
      "is_final_node": true
    }
  ]
}
"""

plan_example = json.loads(plan_example_json)
