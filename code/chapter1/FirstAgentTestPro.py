# 系统提示词
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求, 并使用工具一步步解决问题。

# 用户偏好记忆
你拥有用户偏好记忆：{user_memory}
进行景点推荐时，必须优先结合用户喜好类型like_type、预算范围budget_range[低价/中端/高端]进行精准推荐
若用户对话提及喜欢/偏爱某种景点类型、消费价位，自动识别并更新存入用户记忆
推荐景点时主动避开用户讨厌、拒绝过的景点

# 景点票务状态全局记录
推荐过的景点票务状态情况：{spot_ticket_status}
1. can_recommend：已核实有门票、可正常预约出行，**可以直接推荐给用户**的景点
2. sold_out：已核实门票售罄、无法预约入园，**绝对不能再推荐**的景点黑名单
3. already_recommend：历史对话里已经给用户推荐过的全部景点，尽量不再重复推荐
结束任务使用Finish输出最终答案时，答案里的游玩景点必须全部取自can_recommend列表内容。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市、天气搜索推荐旅游景点 **只有city和weather两个参数, 禁止额外传入其他参数**
- `check_ticket_status(spot_name: str)`: 查询推荐的景点门票是否售罄, 传入多个景点用中文顿号隔开。例: 故宫、天坛、颐和园

# 执行固定流程
1. 先调用get_weather查询天气
2. 再调用get_attraction获取推荐景点
3. 提取主推景点名，调用check_ticket_status查验票务
4. 统计can_recommend内景点数量，**数量不足2个则重新调用get_attraction更换景点再次核验**
5. spot_ticket_status中can_recommend有2个及以上景点后，整理信息用Finish结束对话

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束
- 调用景点工具时，务必带上用户喜好类型、预算、避雷景点全部参数

# 正确示例
# 完整流程正确示例
Thought: 用户需要查询北京的天气，首先需要调用天气工具获取实时天气信息，然后再根据天气和用户喜好推荐景点。
Action: get_weather(city="北京")

Thought: 已成功获取北京天气，结合用户偏好、预算与避雷景点调用景点推荐工具
Action: get_attraction(city="北京",weather="晴")

Thought: 已经拿到推荐景点，现在调用票务工具查询该景点门票售卖状态
Action: check_ticket_status(spot_name="故宫、天坛")

Thought: 核验得知天坛景点门票充足可游玩，故宫本票已售禁, 重新调用景点推荐工具
Action: get_attraction(city="北京",weather="晴")

Thought: 已经拿到推荐景点，现在调用票务工具查询该景点门票售卖状态
Action: check_ticket_status(spot_name="颐和园、恭王府")

Action: Finish[北京今日天气晴朗，结合你偏爱历史文化、中端出行预算，优先推荐前往故宫游玩，目前门票充足可正常预约出行]

Thought: 核验得知推荐景点门票已售罄，将该景点加入黑名单，重新推荐同类型游玩地点


Thought: 核验得知颐和园、恭王府景点门票充足可游玩，整合所有信息整理答案结束对话
Action: Finish[北京今日晴天，结合你的喜好优先推荐天坛、颐和园、恭王府游玩...]

请开始吧！
"""

# 整体新增全局环境变量(记忆+统计)
# 1.用户偏好记忆库(长期记忆)
user_memory = {
    "like_type": [],         # 偏好景点类型：历史文化/自然风光/美食打卡/文艺休闲
    "budget_range": None,    # 预算：低价/中端/高端
    "hate_spot": [],         # 用户不喜欢/拒绝过的景点列表
}
# 2. 已推荐景点票务状态全局字典
spot_ticket_status = {
    "can_recommend": [],        # 存放有票、可正常游玩的景点
    "sold_out": [],             # 存放已售罄、无法游玩的景点
    "already_recommend": []     # 存放已经推荐过的所有景点（避免重复推荐）
}

# 3. 拒绝推荐计数器 + 策略标记
refuse_count = 0            # 连续拒绝推荐次数
is_adjust_strategy = False  # 是否开启调整推荐策略

# 工具1: 查询真实天气
import requests
def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息
    """
    # wttr.in 是一个免费的天气 API 服务，支持全球城市查询
    # API端点, 我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"
    print("get_weather city: ", city)
    try:
        # 发起网络请求
        response = requests.get(url)
        print(f"get_weather response: {response}")
        # 检查响应码: 200(成功)
        response.raise_for_status()
        # 解析返回的JSON数据 | 把 API 返回的 JSON 格式数据，转换成 Python 里的字典（dict）对象
        data = response.json()
        # print(f"get_weather data: {data}")
        # 提取当前天气状况
        current_condition = data["current_condition"][0]
        weather_desc = current_condition["weatherDesc"][0]["value"]
        temp_c = current_condition["temp_C"]

        # 格式化成自然语言返回

        return f"{city}当前天气: {weather_desc}, 气温{temp_c}摄氏度"
    except requests.exceptions.RequestException as e:
        # 处理网络错误

        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误: 解析天气数据失败, 可能是城市名称无效 - {e}"

# 工具2: 搜索并推荐旅游景点
import os
from tavily import TavilyClient
# def get_attraction(city: str, weather: str, like_type: str="", budget_range: str="", hate_spot: str="", already_recommend: str="") -> str:
def get_attraction(city: str, weather: str) -> str:
    """ 根据城市和天气, 使用Tavily Search API搜索并返回优化后的景点推荐 """
    # 1. 从环境变量中读取API秘钥
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误: 未配置TAVILY_API_KEY环境变量。"

    # 2. 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)

    # 拼接偏好文案
    like_type = "、".join(user_memory["like_type"])
    like_text = like_type if like_type else "无特定游玩偏好"

    budget_text = user_memory["budget_range"] if user_memory["budget_range"] else "无出行预算限制"

    # 黑名单: 用户讨厌 + 已经售禁
    forbid_list = list(set(user_memory["hate_spot"] + spot_ticket_status["sold_out"]))
    forbid_str = "、".join(forbid_list)

    # 已推荐过的景点文案(重点防重复)
    reced_str  = "、".join(spot_ticket_status["already_recommend"])

    # 3. 构造精准强约束查询
    query_parts = [
        f"{city}在{weather}天气下适合游玩的旅游景点，"
        f"游玩偏好类型：{like_text}，出行消费预算：{budget_text}",
    ]

    # 强制禁止类
    if forbid_str:
        query_parts.append(f"严格禁止推荐：{forbid_str}")
    if reced_str:
        query_parts.append(f"绝对不要再重复推荐：{reced_str}，请推荐全新同风格景点")
    # === 拒绝三次后调整推荐策略 ===
    if is_adjust_strategy:
        print(f"is_adjust_strategy: {is_adjust_strategy}, 已调整推荐策略为: 推荐小众冷门、人少清净、同价位全新景点;")
        query_parts.append("用户多次不满意之前推荐，彻底更换游玩风格，推荐小众冷门、人少清净、同价位全新景点，避开热门网红景区")
        query_parts.append("优先推荐本地人常去、游客较少、体验感更好的地点")
    else:
        query_parts.append("优先推荐城市热门经典知名景点")

    query_parts.append("每次必须推荐2个及以上全新景点，写明游玩特色与推荐理由，风格保持一致")
    query_parts.append("所有推荐和介绍**必须使用中文**，不要任何英文")

    query = "\n".join(query_parts)
    # print(query)
    try:
        # 4. 调用API, include_answer=True会返回一个综合整理后的回答
        # search_depth: 搜索深度, basic=轻量模式, 速度快，适合普通场景 | advanced = 搜索更深入但耗时更长
        response = tavily.search(query=query, search_depth="basic", include_answer=True, country="China")

        # 5. Tavily返回结果非常干净, 可直接使用
        # response['answer'] 是一个基于所有搜索结果的总结性回答.
        if response.get("answer"):
            return response["answer"]

        # 如果没有综合性回答, 这格式化原始结果
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉, 没有找到相关的旅游景点推荐。"

        return "根据搜索, 为你找到以下信息: \n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误: 执行Tavily搜索时出现问题 - {e}"


# 工具3: 解析用户输入，自动存入记忆
def parse_user_preference(user_input: str):
    """
    从用户输入语句提取旅行偏好，自动存入全局用户记忆
    支持：景点类型、预算档位、讨厌景点
    """
    # todo: 用LLM实现解析用户输入。
    # === 1. 识别景点喜好类型 ===
    if any(word in user_input for word in ["历史", "古迹", "文物", "古城", "博物馆"]):
        if "历史文化" not in user_memory["like_type"]:
            user_memory["like_type"].append("历史文化")

    if any(word in user_input for word in ["山水", "自然", "风景", "森林", "湖泊", "海边"]):
        if "自然风光" not in user_memory["like_type"]:
            user_memory["like_type"].append("自然风光")

    if any(word in user_input for word in ["美食", "小吃", "探店", "吃吃喝喝"]):
        if "美食打卡" not in user_memory["like_type"]:
            user_memory["like_type"].append("美食打卡")

    if any(word in user_input for word in ["文艺", "拍照", "网红", "文创", "艺术馆"]):
        if "文艺休闲" not in user_memory["like_type"]:
            user_memory["like_type"].append("文艺休闲")

    if any(word in user_input for word in ["乐园", "游玩", "刺激", "亲子"]):
        if "休闲游乐" not in user_memory["like_type"]:
            user_memory["like_type"].append("休闲游乐")

    # ========== 2. 识别预算档位 ==========
    if any(word in user_input for word in ["便宜", "省钱", "平价", "穷游", "性价比"]):
        user_memory["budget_range"] = "低价"
    elif any(word in user_input for word in ["中等", "普通", "正常", "适中"]):
        user_memory["budget_range"] = "中端"
    elif any(word in user_input for word in ["高端", "轻奢", "豪华", "贵点没事", "品质"]):
        user_memory["budget_range"] = "高端"

    # ========== 3. 识别用户拒绝/不喜欢的景点（加入黑名单） ==========
    refuse_keywords = ["不去", "不想去", "不好玩", "没意思", "换一个", "不喜欢", "避雷"]
    spot_list = ["故宫", "长城", "颐和园", "天坛", "圆明园", "王府井", "798艺术区"]
    if any(k in user_input for k in refuse_keywords):
        # 可用大模型判断用户输入的不想去的景点是什么
        for spot in spot_list:
            if spot in user_input and spot not in user_memory["hate_spot"]:
                user_memory["hate_spot"].append(spot)

# 工具4: 查询景点是否有票
def check_ticket_status(spot_name: str):
    """
    查询指定景点门票是否可购买
    传入多个景点用中文顿号隔开：故宫、天坛、颐和园
    返回：有票 / 门票售罄 / 暂未查询到票务信息
    """
    # 模拟票务查询逻辑，实际可对接真实票务接口
    sell_out_list = ["故宫","八达岭长城"]
    # 分割多个景点
    spot_list = [s.strip() for s in spot_name.split("、") if s.strip()]
    res_list = []
    for spot_name in spot_list:
        # 1. 记录已推荐，去重
        if spot_name not in spot_ticket_status["already_recommend"]:
            spot_ticket_status["already_recommend"].append(spot_name)
        # 2. 优先判断是否已经标记售罄
        if spot_name in spot_ticket_status["sold_out"]:
            res_list.append(f"查询结果：{spot_name} 已判定门票售罄，无法预约购买")
            continue
        # 3. 优先判断是否在用户讨厌黑名单
        if spot_name in user_memory["hate_spot"]:
            res_list.append(f"查询结果：{spot_name} 为用户不想去景点，不予推荐")
            continue
        # 4. 模糊匹配是否属于固定售罄景点
        is_sold = any(key in spot_name for key in sell_out_list)
        if is_sold:
            spot_ticket_status["sold_out"].append(spot_name)
            res_list.append(f"查询结果：{spot_name} 当前门票已售罄，无法预约购买")
            # 售罄不加入可推荐列表
            continue
        # 5. 正常可推荐景点
        if spot_name not in spot_ticket_status["can_recommend"]:
            spot_ticket_status["can_recommend"].append(spot_name)
        res_list.append(f"查询结果：{spot_name} 门票充足，正常可购票游玩")

    return "\n".join(res_list)


# 工具5: 用户拒绝交互函数
def user_refuse_operate(user_refuse_input: str):
    """
    处理用户拒绝景点操作
    1. 提取拒绝景点加入黑名单
    2. 累加拒绝次数
    3. 满3次自动开启策略调整
    """
    global refuse_count, is_adjust_strategy

    # 复用已有偏好解析里的拒绝关键词+景点库 | 不想去/换一个/拒绝该景点/不喜欢
    refuse_keywords = ["不想去", "换一个", "不喜欢", "拒绝该景点"]
    # 命中拒绝话术
    if any(k in user_refuse_input for k in refuse_keywords):
        refuse_count += 1
        print(f"⚠️ 用户已连续拒绝推荐次数：{refuse_count}")

        # 将推荐的景点(can_recommend)添加到hate_spot中
        # 提取用户明确拒绝的景点， 添加到hate_spot中，在can_recommend中去除
        for spot in spot_ticket_status["can_recommend"]:
            if spot in user_refuse_input:
                spot_ticket_status["can_recommend"].remove(spot)
                print(f"✅ 已将【{spot}】从推荐景点中删除")
                if spot not in user_memory["hate_spot"]:
                    user_memory["hate_spot"].append(spot)
                    print(f"✅ 已将【{spot}】加入游玩黑名单")
    else:
        refuse_count = 0

    # 连续拒绝满3次，切换推荐策略
    if refuse_count >= 3 and not is_adjust_strategy:
        is_adjust_strategy = True
        refuse_count = 0
        print("🎉 已连续拒绝3次推荐，智能体开始调整整体推荐策略！")
    else:
        is_adjust_strategy = False


# 将所有工具函数放入一个字典, 方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "check_ticket_status": check_ticket_status,
}


from openai import OpenAI
class OpenAICompatibleClient:
    """一个用于调用任何兼容OpenAI接口的LLM服务客户端."""
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用LLM API来生成回应"""
        print("正在调用大语言模型...")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            # print(f"response: {response}")
            answer = response.choices[0].message.content
            print("大语言模型响应成功...")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误: 调用语言模型服务时出错。"



import re
from dotenv import load_dotenv
# 加载.env
load_dotenv()
# --- 1. 配置LLM客户端 ---
# 请根据你使用的服务, 将这里替换成对应的凭证和地址
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
MODEL_ID = os.getenv("DEEPSEEK_MODEL")
os.environ['TAVILY_API_KEY'] = os.environ.get("TAVILY_API_KEY")
# print(f"API_KEY: {API_KEY}")

llm = OpenAICompatibleClient(model=MODEL_ID, api_key=API_KEY, base_url=BASE_URL)


# ---2. 初始化 ---
user_prompt = "你好, 请帮我查询一下今天北京的天气, 然后根据天气推荐一个合适的旅游景点。预算：中等, 喜欢历史文化、自然风光、博物馆、特色小吃。"
prompt_history = [f"用户请求: {user_prompt}"]

print(f"用户输入: {user_prompt}\n" + "="*40)
# ===== 新增1：解析用户编号存入记忆 =====
parse_user_preference(user_prompt)


# ---3. 运行主循环 ---
for i in range(20): # 设置最大循环次数
    print(f"--- 循环 {i+1} ---\n")

    # 3.1 构建Prompt
    full_prompt = "\n".join(prompt_history)

    # 3.2 调用LLM进行思考
    # ===== 新增2：将用户偏好记忆和已推荐景点状态加入系统提示词 =====
    memory_str = str(user_memory)
    print(f"用户偏好信息: {memory_str}\n")
    ticket_str = str(spot_ticket_status)
    print(f"已景点情况: {ticket_str}\n" + "="*40)
    system_prompt = AGENT_SYSTEM_PROMPT.format(user_memory=memory_str, spot_ticket_status=ticket_str)
    llm_output = llm.generate(prompt=full_prompt, system_prompt=system_prompt)
    # 模型可能会输出多余的Thought-Action, 需要截断
    # 强制约束大模型一次只输出一次思考 + 一次行动，截断多余多轮思考，保证智能体按顺序串行执行工具。
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")
    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3 解析并执行行动
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL).group(1)
        print(f"任务完成: 最终答案: {final_answer}\n")
        # ===== 新增3：用户手动拒绝交互 =====
        user_refuse_input = input("\n请输入你的想法（不想去/换一个/不喜欢，无则直接回车结束）:")

        if user_refuse_input.strip() and any(k in user_refuse_input for k in ["不想去", "换一个", "不喜欢"]):
            user_refuse_operate(user_refuse_input)
            # 把用户拒绝话术加入对话历史，让大模型感知
            prompt_history.append(f"用户反馈：{user_refuse_input}")
            continue  # 继续下一轮循环重新推荐
        break
    # get_attraction(city="北京", weather="晴")
    tool_name = re.search(r"(\w+)\(", action_str).group(1)  # tool_name: get_attraction
    args_str = re.search(r"\((.*)\)", action_str).group(1)  # args_str: city="北京", weather="晴"
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str)) # kwargs: {'city': '北京', 'weather': '晴'}

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误: 未定义的工具'{tool_name}'"

    # 3.4 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)
