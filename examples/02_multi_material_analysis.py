"""
进阶示例：多物料分析任务

展示如何使用多个 Material 输入，让 Agent 进行综合分析。
"""

import os

from coralmind import Agent, LLMConfig, Material, Task


def main():
    llm = LLMConfig(
        model_id="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    agent = Agent(default_llm=llm)

    market_report = """
2024年市场分析报告

市场规模：全球市场达到 500 亿美元，同比增长 25%。
主要驱动因素：企业数字化转型需求、AI 技术成熟度提升。
竞争格局：头部企业市场份额集中，CR5 达到 60%。
"""

    competitor_analysis = """
竞品分析报告

A公司：市场份额 25%，主打企业级解决方案，价格较高。
B公司：市场份额 18%，专注中小企业，性价比优势明显。
C公司：市场份额 12%，技术创新领先，但渠道建设不足。
"""

    user_survey = """
用户调研报告

样本量：5000 份有效问卷
核心发现：
1. 60% 用户最关注产品易用性
2. 45% 用户愿意为 AI 功能支付溢价
3. 30% 用户对现有解决方案不满意
"""

    task = Task(
        materials=[
            Material(name="market_report", content=market_report),
            Material(name="competitor_analysis", content=competitor_analysis),
            Material(name="user_survey", content=user_survey),
        ],
        requirements="综合分析市场报告、竞品分析和用户调研，制定产品策略建议"
    )

    result = agent.run(task)

    print("产品策略建议：")
    print(result)


if __name__ == "__main__":
    main()
