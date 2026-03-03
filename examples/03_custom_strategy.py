"""
高级示例：自定义策略配置

展示如何自定义 ThresholdStrategy 参数，调整计划复用行为。
"""

import os
from coralmind import Agent, Task, Material, LLMConfig, ThresholdStrategy


def main():
    llm = LLMConfig(
        model_id="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    strategy = ThresholdStrategy(
        s0=7.0,   # 平均分 >= 7.0 时，参考优化
        s1=8.5,   # 平均分 >= 8.5 时，直接复用
        c=2,      # 最少 2 条历史记录才开始复用
    )
    
    agent = Agent(
        default_llm=llm,
        advising_strategy=strategy,
        max_retry_times_per_node=5,
    )
    
    article_content = """
深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的表示。
与传统的机器学习方法不同，深度学习能够自动从原始数据中提取特征，
无需人工特征工程。

深度学习在图像识别、语音识别、自然语言处理等领域取得了突破性进展。
著名的应用包括：人脸识别、机器翻译、自动驾驶等。
"""
    
    task = Task(
        materials=[Material(name="article", content=article_content)],
        requirements="解释深度学习的核心概念，并列出三个典型应用"
    )
    
    result = agent.run(task)
    
    print("分析结果：")
    print(result)
    
    print("\n提示：多次运行相同类型的任务，观察计划复用效果")


if __name__ == "__main__":
    main()
