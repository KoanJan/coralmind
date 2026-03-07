"""
高级示例：多材料综合分析任务（带输出格式约束）

展示一个复杂任务：分析多个代码文件，生成符合指定 JSON Schema 的结构化审查报告。
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

import json
import logging
import os
from pathlib import Path

from coralmind import Agent, LLMConfig, Material, OutputFormat, Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("coralmind").setLevel(logging.DEBUG)


COMPLEX_JSON_SCHEMA = '''
{
    "$defs": {
        "Severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"]
        },
        "IssueCategory": {
            "type": "string",
            "enum": ["security", "performance", "maintainability", "design", "error_handling"]
        },
        "FileLocation": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 255
                },
                "line_start": {
                    "type": "integer",
                    "minimum": 1
                },
                "line_end": {
                    "type": "integer",
                    "minimum": 1
                }
            },
            "required": ["file", "line_start"],
            "additionalProperties": false
        },
        "SecurityIssue": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^SEC-[0-9]{3}$"
                },
                "location": {
                    "$ref": "#/$defs/FileLocation"
                },
                "severity": {
                    "$ref": "#/$defs/Severity"
                },
                "vulnerability_type": {
                    "type": "string",
                    "enum": ["sql_injection", "xss", "csrf", "auth_bypass", "data_exposure", "other"]
                },
                "description": {
                    "type": "string",
                    "minLength": 10,
                    "maxLength": 1000
                },
                "cwe_reference": {
                    "anyOf": [
                        {"type": "string", "pattern": "^CWE-[0-9]+$"},
                        {"type": "null"}
                    ]
                },
                "fix_suggestion": {
                    "type": "string",
                    "minLength": 20
                },
                "references": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "uri"
                    },
                    "minItems": 0,
                    "maxItems": 5
                }
            },
            "required": ["id", "location", "severity", "vulnerability_type", "description", "fix_suggestion"],
            "additionalProperties": false
        },
        "QualityIssue": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^QTY-[0-9]{3}$"
                },
                "location": {
                    "$ref": "#/$defs/FileLocation"
                },
                "category": {
                    "$ref": "#/$defs/IssueCategory"
                },
                "severity": {
                    "$ref": "#/$defs/Severity"
                },
                "description": {
                    "type": "string",
                    "minLength": 10,
                    "maxLength": 1000
                },
                "fix_suggestion": {
                    "type": "string",
                    "minLength": 20
                },
                "estimated_effort": {
                    "type": "string",
                    "enum": ["trivial", "small", "medium", "large"]
                }
            },
            "required": ["id", "location", "category", "severity", "description", "fix_suggestion"],
            "additionalProperties": false
        },
        "Metrics": {
            "type": "object",
            "properties": {
                "total_files_reviewed": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100
                },
                "total_issues_found": {
                    "type": "integer",
                    "minimum": 0
                },
                "security_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100
                },
                "quality_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100
                },
                "lines_analyzed": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": ["total_files_reviewed", "total_issues_found", "security_score", "quality_score"],
            "additionalProperties": false
        }
    },
    "type": "object",
    "properties": {
        "report_version": {
            "const": "2.0"
        },
        "generated_at": {
            "type": "string",
            "format": "date-time"
        },
        "security_issues": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/SecurityIssue"
            },
            "minItems": 0,
            "maxItems": 50
        },
        "quality_issues": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/QualityIssue"
            },
            "minItems": 0,
            "maxItems": 50
        },
        "metrics": {
            "$ref": "#/$defs/Metrics"
        },
        "priority_order": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^(SEC|QTY)-[0-9]{3}$"
            },
            "minItems": 0
        },
        "summary": {
            "type": "string",
            "minLength": 50,
            "maxLength": 2000
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 10
            },
            "minItems": 1,
            "maxItems": 10
        },
        "contact_email": {
            "anyOf": [
                {"type": "string", "format": "email"},
                {"type": "null"}
            ]
        }
    },
    "required": [
        "report_version",
        "generated_at",
        "security_issues",
        "quality_issues",
        "metrics",
        "priority_order",
        "summary",
        "recommendations"
    ],
    "additionalProperties": false
}
'''


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

    json_schema = COMPLEX_JSON_SCHEMA

    task = Task(
        materials=[
            Material(name="user_service.py", content=user_service_code),
            Material(name="order_service.py", content=order_service_code),
            Material(name="payment_service.py", content=payment_service_code),
        ],
        requirements="""
请对提供的三个服务类进行全面的代码审查，重点关注：

1. **安全问题**：识别所有安全漏洞（如SQL注入、敏感信息暴露等），按严重程度排序

2. **代码质量**：分析代码设计问题（如职责划分、错误处理、代码重复等）

3. **改进建议**：针对每个问题提供具体的修复方案

4. **优先级排序**：将所有问题按修复优先级分类
""",
        output_format=OutputFormat(json_schema=json_schema),
    )

    result = agent.run(task)

    print("=" * 60)
    print("代码审查报告 (JSON)")
    print("=" * 60)
    print(result)

    print("\n" + "=" * 60)
    print("验证输出格式")
    print("=" * 60)
    try:
        parsed_data = json.loads(result)
        print("✅ 输出符合 JSON Schema")
        print(f"  - 报告版本: {parsed_data.get('report_version')}")
        print(f"  - 安全问题数量: {len(parsed_data.get('security_issues', []))}")
        print(f"  - 代码质量问题数量: {len(parsed_data.get('quality_issues', []))}")
        print(f"  - 安全评分: {parsed_data.get('metrics', {}).get('security_score')}")
        print(f"  - 质量评分: {parsed_data.get('metrics', {}).get('quality_score')}")
        print(f"  - 摘要: {parsed_data.get('summary', '')[:100]}...")
        print(f"  - 建议数量: {len(parsed_data.get('recommendations', []))}")
    except Exception as e:
        print(f"❌ 输出不符合 JSON Schema: {e}")


if __name__ == "__main__":
    main()
