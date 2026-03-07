"""
基础示例：文本摘要任务

展示如何使用 coralmind 执行一个简单的文本摘要任务。
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

    article_content = """
人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
致力于创建能够执行通常需要人类智能的任务的系统。这些任务包括
学习、推理、问题解决、感知和语言理解等。

AI 的发展历程可以追溯到 20 世纪 50 年代，当时 Alan Turing 提出
了著名的图灵测试。此后，AI 经历了多次繁荣与萧条的周期。

近年来，深度学习和大规模语言模型的出现引发了 AI 的新一轮革命。
GPT、Claude 等模型展示了令人惊叹的语言理解和生成能力。
"""

    task = Task(
        materials=[Material(name="article", content=article_content)],
        requirements="对输入文章进行摘要，不超过100字，包含核心观点"
    )

    result = agent.run(task)

    print("摘要结果：")
    print(result)


if __name__ == "__main__":
    main()
