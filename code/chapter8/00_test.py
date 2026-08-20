# 配置好同级文件夹下.env中的大模型API
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import MemoryTool, RAGTool

# 创建LLM实例
llm = HelloAgentsLLM()

# 创建工具注册表
tool_registry = ToolRegistry()

# 添加记忆工具
memory_tool = MemoryTool(user_id="user123")
tool_registry.register_tool(memory_tool)

# 添加RAG工具
rag_tool = RAGTool(knowledge_base_path="./knowledge_base")
tool_registry.register_tool(rag_tool)

# 创建Agent并配置工具
agent = SimpleAgent(
    name="智能助手",
    llm=llm,
    system_prompt="你是一个有记忆和知识检索能力的AI助手",
    tool_registry=tool_registry
)

# 原来的写法依赖大模型自动生成 MemoryTool 参数。
# 当前模型调用时遗漏了必需的 action 参数，导致“参数验证失败”，因此先注释保留。
# response = agent.run("你好！请记住我叫张三，我是一名Python开发者")
# print(response)

# 直接调用 MemoryTool，明确传入必需参数，验证记忆能否持久化。
add_result = memory_tool.run({
    "action": "add",
    "content": "用户叫张三，是一名Python开发者",
    "memory_type": "episodic",
    "importance": 0.8,
})
print("记忆写入结果:", add_result)

# 搜索刚刚写入的记忆，验证存储和语义检索是否正常。
search_result = memory_tool.run({
    "action": "search",
    "query": "用户叫什么，是做什么工作的？",
    "memory_type": "episodic",
    "limit": 5,
})
print("记忆搜索结果:", search_result)
