# test_my_calculator.py
import re

from dotenv import load_dotenv
from my_calculator_tool import create_calculator_registry

# 加载环境变量
load_dotenv()

def test_calculator_tool():
    """测试自定义计算器工具"""

    # 创建包含计算器的注册表
    registry = create_calculator_registry()

    print("🧪 测试自定义计算器工具\n")

    # 简单测试用例
    test_cases = [
        "2 + 3",           # 基本加法
        "10 - 4",          # 基本减法
        "5 * 6",           # 基本乘法
        "15 / 3",          # 基本除法
        "sqrt(16)",        # 平方根
    ]

    for i, expression in enumerate(test_cases, 1):
        print(f"测试 {i}: {expression}")
        result = registry.execute_tool("my_calculator", expression)
        print(f"结果: {result}\n")

def test_with_simple_agent():
    """测试与SimpleAgent的集成"""
    from hello_agents import HelloAgentsLLM

    # 创建LLM客户端
    llm = HelloAgentsLLM()

    # 创建包含计算器的注册表
    registry = create_calculator_registry()

    print("🤖 与SimpleAgent集成测试:")

    # 模拟SimpleAgent使用工具的场景
    user_question = "请帮我计算 sqrt(16) + 2 * 3"

    print(f"用户问题: {user_question}")

    # 从用户问题中提取“计算”后面的数学表达式
    match = re.search(r"计算\s*(.+?)[？?。]?$", user_question)
    if not match:
        raise ValueError(f"无法从用户问题中提取计算表达式: {user_question}")

    expression = match.group(1).strip()
    print(f"提取的表达式: {expression}")

    # 使用提取出来的表达式调用计算工具
    calc_result = registry.execute_tool("my_calculator", expression)
    print(f"计算结果: {calc_result}")

    # 构建最终回答
    final_messages = [
        {"role": "user", "content": f"计算结果是 {calc_result}，请用自然语言回答用户的问题：{user_question}"}
    ]

    print("\n🎯 SimpleAgent的回答:")
    response = llm.invoke(final_messages)
    print(response)

if __name__ == "__main__":
    test_calculator_tool()
    test_with_simple_agent()
