"""
高级示例：多材料综合分析任务

展示一个复杂任务：分析多个代码文件，生成综合审查报告。
通过环境变量配置 LLM，方便测试和部署。

运行方式：
    # 方式1：使用 .env 文件（需要安装 python-dotenv）
    pip install python-dotenv
    python 04_code_review.py

    # 方式2：命令行注入环境变量
    export $(grep -v '^#' ../.env | xargs) && python 04_code_review.py

    # 方式3：直接设置环境变量
    DEFAULT_MODEL_ID=gpt-4o-mini DEFAULT_BASE_URL=... DEFAULT_API_KEY=... python 04_code_review.py
"""

import logging
import os
from pathlib import Path

from coralmind import Agent, LLMConfig, Material, Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("coralmind").setLevel(logging.DEBUG)


def load_env() -> None:
    """Load .env file if python-dotenv is available"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        pass


def load_llm_from_env(prefix: str) -> LLMConfig:
    """从环境变量加载 LLM 配置

    环境变量格式：
    - {PREFIX}_MODEL_ID: 模型ID (必需)
    - {PREFIX}_BASE_URL: API地址 (必需)
    - {PREFIX}_API_KEY: API密钥 (必需)
    - {PREFIX}_MAX_TOKENS: 最大token数 (可选，默认8196)

    示例：
        DEFAULT_MODEL_ID=gpt-4o-mini
        DEFAULT_BASE_URL=https://api.openai.com/v1
        DEFAULT_API_KEY=sk-xxx
    """
    model_id = os.environ.get(f"{prefix}_MODEL_ID")
    base_url = os.environ.get(f"{prefix}_BASE_URL")
    api_key = os.environ.get(f"{prefix}_API_KEY")

    if not all([model_id, base_url, api_key]):
        raise ValueError(
            f"Missing required environment variables for {prefix}: "
            f"{prefix}_MODEL_ID, {prefix}_BASE_URL, {prefix}_API_KEY"
        )

    max_tokens = int(os.environ.get(f"{prefix}_MAX_TOKENS", "8196"))

    return LLMConfig(
        model_id=model_id,
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
    )


def main() -> None:
    load_env()
    default_llm = load_llm_from_env("DEFAULT")
    planner_llm_config = os.environ.get("PLANNER_MODEL_ID")
    planner_llm = load_llm_from_env("PLANNER") if planner_llm_config else None

    agent = Agent(
        default_llm=default_llm,
        planner_llm=planner_llm,
        max_retry_times_per_node=3,
    )

    user_service_code = '''
class UserService:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id):
        query = f"SELECT * FROM users WHERE id = {user_id}"
        return self.db.execute(query)

    def create_user(self, username, password):
        query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
        self.db.execute(query)

    def authenticate(self, username, password):
        user = self.get_user_by_username(username)
        if user and user.password == password:
            return True
        return False
'''

    order_service_code = '''
class OrderService:
    def __init__(self, db):
        self.db = db

    def get_orders(self, user_id):
        query = "SELECT * FROM orders WHERE user_id = " + str(user_id)
        return self.db.execute(query)

    def create_order(self, user_id, items):
        total = sum(item['price'] * item['quantity'] for item in items)
        query = f"INSERT INTO orders (user_id, total) VALUES ({user_id}, {total})"
        order_id = self.db.execute(query)
        for item in items:
            self.add_order_item(order_id, item)
        return order_id

    def add_order_item(self, order_id, item):
        query = f"INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ({order_id}, {item['id']}, {item['quantity']}, {item['price']})"
        self.db.execute(query)
'''

    payment_service_code = '''
class PaymentService:
    def __init__(self, db):
        self.db = db

    def process_payment(self, order_id, card_number, cvv, expiry):
        order = self.get_order(order_id)
        amount = order['total']

        result = self.call_payment_gateway(card_number, cvv, expiry, amount)

        if result['success']:
            self.update_order_status(order_id, 'paid')
            return {'success': True, 'transaction_id': result['transaction_id']}
        return {'success': False, 'error': result['error']}

    def call_payment_gateway(self, card_number, cvv, expiry, amount):
        import requests
        response = requests.post('https://payment.example.com/api/charge', json={
            'card_number': card_number,
            'cvv': cvv,
            'expiry': expiry,
            'amount': amount
        })
        return response.json()
'''

    task = Task(
        materials=[
            Material(name="user_service.py", content=user_service_code),
            Material(name="order_service.py", content=order_service_code),
            Material(name="payment_service.py", content=payment_service_code),
        ],
        requirements="""
请对提供的三个服务类进行全面的代码审查，生成结构化报告，包含以下部分：

1. **安全问题**：识别所有安全漏洞（如SQL注入、敏感信息暴露等），按严重程度排序

2. **代码质量**：分析代码设计问题（如职责划分、错误处理、代码重复等）

3. **改进建议**：针对每个问题提供具体的修复方案和示例代码

4. **优先级排序**：将所有问题按修复优先级（高/中/低）分类

输出格式要求：
- 使用 Markdown 格式
- 每个问题需标注所在文件和行号
- 改进建议需包含修复前后的代码对比
"""
    )

    result = agent.run(task)

    print("=" * 60)
    print("代码审查报告")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
