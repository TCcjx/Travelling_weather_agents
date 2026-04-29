"""Travel Agent - 智能天气穿搭助手

核心逻辑：
1. 非天气问题 → LLM 流式闲聊
2. 天气问题 → LLM提取城市 → 天气API → LLM流式回复 → 天气+穿搭建议 + 7天趋势图
3. 天气API失败 → LLM重新提取城市 → 重试(最多3次)
"""
import os
import sys
import time
import threading

from dotenv import load_dotenv
load_dotenv() 

from weather import get_weather, WeatherAPIError
from outfit import recommend_outfit
from chart import generate_forecast_chart, HAS_MATPLOTLIB
from llm import ChatClient, LLMError


MAX_CITY_EXTRACT_RETRIES = 3  # 最大重试次数


class ThinkingAnimation:
    """思考动画"""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
    SUCCESS = "✓"
    ERROR = "✗"

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.running = False
        self.thread = None

    def _animate(self):
        """动画线程"""
        i = 0
        while self.running:
            sys.stdout.write(f"\r{self.prefix} {self.FRAMES[i % len(self.FRAMES)]} ")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def start(self):
        """开始动画"""
        self.running = True
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()

    def stop(self, success: bool = True, message: str = ""):
        """停止动画"""
        self.running = False
        time.sleep(0.1)
        symbol = self.SUCCESS if success else self.ERROR
        sys.stdout.write(f"\r{self.prefix} {symbol} {message}\n")
        sys.stdout.flush()


class TravelAgent:
    """旅行助手 Agent"""

    GREETING = """
========== Travel Agent ==========
Hello! I'm your weather & outfit assistant.
Ask me about weather/outfits or just chat!

Type "quit" to exit.

=================================
"""

    GOODBYE = """
Bye! Have a great day~
"""

    CITY_EXTRACT_PROMPT = """从用户问题中提取用户想查询天气的城市名。

规则：
1. 如果用户在当前问题或对话历史中提到了城市（包括"那边"、"这里"等模糊指代），提取对应城市
2. 当用户使用"那边"、"这里"、"那个城市"等模糊指代时，参考对话历史中的地点信息
3. 只返回一个城市名
4. 城市名必须是中文或英文名称
5. 优先从对话历史中匹配用户实际想查询的地点

对话历史：
{history}

当前问题：{user_input}

请提取用户想查询天气的城市名，如果无法确定，返回"未提供城市"。
只返回城市名，不要其他内容。"""

    def __init__(self, weather_api_key: str = None, llm_api_key: str = None):
        self.weather_api_key = weather_api_key or os.getenv("WEATHER_API_KEY")
        self.llm_client = None

        llm_key = llm_api_key or os.getenv("LLM_API_KEY")
        if llm_key:
            self.llm_client = ChatClient(llm_key)

        self.running = True
        self.last_weather = None
        self.conversation_context = ""  # 对话上下文（用于城市提取）

    def print_thinking(self, step: str):
        """打印思考步骤"""
        print(f"\n  🔄 {step}")

    def print_success(self, step: str, detail: str = ""):
        """打印成功信息"""
        msg = f"  ✓ {step}"
        if detail:
            msg += f" → {detail}"
        print(msg)

    def print_error(self, step: str, detail: str = ""):
        """打印错误信息"""
        msg = f"  ✗ {step}"
        if detail:
            msg += f" → {detail}"
        print(msg)

    def print_info(self, msg: str):
        """打印信息"""
        print(f"  ℹ  {msg}")

    def is_weather_related(self, text: str) -> bool:
        """判断是否是天气相关问题"""
        weather_keywords = ["天气", "温度", "气温", "气候", "下雨", "下雪", "晴天",
                          "穿什么", "穿搭", "衣服", "外套", "带什么", "出门"]
        return any(kw in text for kw in weather_keywords)

    def extract_city_with_llm(self, user_input: str, retry_count: int = 0, last_error: str = "") -> str:
        """使用 LLM 提取城市名（带上下文）"""

        if last_error and retry_count > 0:
            prompt = f"""从用户问题中提取城市名。

注意：上次尝试查询城市"{last_error}"失败（可能不是有效城市），请重新提取。

对话历史：
{self.conversation_context}

规则：
1. 如果用户在当前问题或对话历史中提到了城市，提取该城市
2. 如果用户只是模糊地说"这里"、"那边"等，但没有明确城市，返回"未提供城市"
3. 只返回一个城市名
4. 城市名必须是中文或英文名称

当前问题：{user_input}

只返回城市名，不要其他内容。"""
        else:
            prompt = self.CITY_EXTRACT_PROMPT.format(
                history=self.conversation_context,
                user_input=user_input
            )

        try:
            self.print_thinking(f"正在分析用户问题，提取城市名...")
            city = self.llm_client.chat(prompt,
                "你是一个城市名提取助手，只返回城市名，不要其他内容。")
            city = city.strip()

            if "未提供城市" in city or not city:
                return None

            self.print_success("城市名提取", city)
            return city
        except LLMError:
            return None

    def format_weather(self, weather) -> str:
        """格式化天气信息"""
        return f"""天气预报：
- 城市：{weather.city}
- 当前温度：{weather.temp}°C（体感 {weather.feels_like}°C）
- 天气状况：{weather.condition}
- 湿度：{weather.humidity}%
- 风速：{weather.wind_speed} km/h"""

    def format_forecast(self, weather) -> str:
        """格式化7天预报"""
        if not weather.forecast:
            return "无7天预报数据"

        text = "7天天气预报：\n"
        for i, day in enumerate(weather.forecast[:7]):
            text += f"- 第{i+1}天：{day['date']} {day['condition']} {day['temp_min']:.0f}-{day['temp_max']:.0f}°C\n"
        return text

    def format_outfit(self, weather, days_ahead: int = 0) -> str:
        """获取穿搭建议"""
        outfit = recommend_outfit(weather, days_ahead)
        return f"""穿搭建议：
- 上装：{outfit['top']}
- 下装：{outfit['bottom']}
- 鞋子：{outfit['shoes']}
- 配件：{outfit['accessories']}"""

    def handle_weather_stream(self, city: str, user_input: str):
        """处理天气相关问题（流式输出）"""
        try:
            self.print_thinking(f"正在查询 {city} 的天气数据...")
            weather = get_weather(city, self.weather_api_key)
            self.last_weather = weather
            self.print_success("天气数据获取", f"{weather.condition} {weather.temp}°C")
        except WeatherAPIError as e:
            print(f"\nAgent: 抱歉，天气获取失败：{e}")
            return

        # 生成图表
        chart_path = ""
        if HAS_MATPLOTLIB and weather.forecast:
            self.print_thinking("正在生成7天天气趋势图...")
            chart_path = generate_forecast_chart(city, weather.forecast)
            self.print_success("趋势图生成", chart_path)

        # 构建天气上下文
        weather_info = self.format_weather(weather)
        forecast_info = self.format_forecast(weather)
        outfit_info = self.format_outfit(weather)

        prompt = f"""用户问题：{user_input}

{weather_info}

{forecast_info}

{outfit_info}

请基于以上信息，用友好简洁的语言回复用户，结合天气给出穿搭建议。"""

        self.print_thinking("正在生成穿搭建议...")
        print()  # 空行分隔

        try:
            for chunk in self.llm_client.chat_stream(prompt,
                "你是一个友好的天气助手，请结合天气数据和穿搭建议回复用户。"):
                print(chunk, end="", flush=True)
        except LLMError as e:
            print(f"\n\nAgent: 抱歉，服务暂时不可用：{e}")
            return

        if chart_path:
            print(f"\n\n  📊 趋势图已保存：{chart_path}")

    def handle_weather_with_retry(self, user_input: str):
        """处理天气问题（带重试机制）"""
        last_error = ""
        city = None

        for retry in range(MAX_CITY_EXTRACT_RETRIES):
            # 使用 LLM 提取城市名
            city = self.extract_city_with_llm(user_input, retry, last_error)

            if not city:
                print("\nAgent: 请问你想查询哪个城市的天气呢？比如「北京天气怎么样」")
                return

            # 尝试获取天气
            try:
                self.print_thinking(f"正在连接天气API，获取 {city} 的天气数据...")
                weather = get_weather(city, self.weather_api_key)
                self.last_weather = weather
                self.print_success("天气API响应", f"{weather.condition} {weather.temp}°C")
            except WeatherAPIError as e:
                last_error = city
                self.print_error("天气API调用", str(e))
                print(f"\n  🔄 重试中... ({retry + 1}/{MAX_CITY_EXTRACT_RETRIES})")
                time.sleep(1)
                continue

            # 成功获取天气，生成回复
            weather_info = self.format_weather(weather)
            forecast_info = self.format_forecast(weather)
            outfit_info = self.format_outfit(weather)

            # 生成图表
            chart_path = ""
            if HAS_MATPLOTLIB and weather.forecast:
                self.print_thinking("正在生成7天天气趋势图...")
                chart_path = generate_forecast_chart(city, weather.forecast)
                self.print_success("趋势图生成", chart_path)

            prompt = f"""用户问题：{user_input}

{weather_info}

{forecast_info}

{outfit_info}

请基于以上信息，用友好简洁的语言回复用户，结合天气给出穿搭建议。"""

            self.print_thinking("正在生成穿搭建议...")
            print()  # 空行分隔

            full_reply = ""
            try:
                for chunk in self.llm_client.chat_stream(prompt,
                    "你是一个友好的天气助手，请结合天气数据和穿搭建议回复用户。"):
                    print(chunk, end="", flush=True)
                    full_reply += chunk
            except LLMError as e:
                print(f"\n\nAgent: 抱歉，服务暂时不可用：{e}")
                return

            # 更新对话上下文
            self._update_conversation_context(user_input, full_reply)
            self.conversation_context = f"用户所在地：{city}\n最近的对话：\n用户：{user_input}\n助手：{full_reply[:100]}..."

            if chart_path:
                print(f"\n\n  📊 趋势图已保存：{chart_path}")
            return

        # 所有重试都失败
        print(f"\n\nAgent: 抱歉，无法找到有效的城市信息。请明确提供城市名，例如「北京天气怎么样」。")

    def handle_chat_stream(self, user_input: str):
        """处理闲聊（流式输出）"""
        if not self.llm_client:
            print("\nAgent: 抱歉，聊天功能暂时不可用。")
            return

        self.print_thinking("正在思考...")

        context = ""
        if self.last_weather:
            context = f"\n\n附：上次查询的天气（{self.last_weather.city}）\n{self.format_weather(self.last_weather)}"

        prompt = f"用户：{user_input}{context}"

        print()  # 空行分隔

        try:
            full_reply = ""
            for chunk in self.llm_client.chat_stream(prompt,
                "你是一个友好的助手 named Travel Agent，帮助用户回答天气和穿搭问题，也可以日常闲聊。"):
                print(chunk, end="", flush=True)
                full_reply += chunk
        except LLMError as e:
            print(f"\n\nAgent: 抱歉，服务暂时不可用：{e}")
            full_reply = ""

        # 更新对话上下文
        self._update_conversation_context(user_input, full_reply)

    def _update_conversation_context(self, user_input: str, assistant_reply: str):
        """更新对话上下文"""
        # 提取用户提到的地点信息
        locations = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉",
                    "西安", "南京", "天津", "苏州", "郑州", "长沙", "沈阳", "青岛",
                    "东京", "纽约", "巴黎", "伦敦", "新加坡", "首尔", "曼谷", "悉尼"]

        user_location = None
        for loc in locations:
            if loc in user_input:
                user_location = loc
                break

        # 更新上下文
        if user_location:
            # 如果用户在输入中提到了地点，更新当前位置
            self.conversation_context = f"用户所在地：{user_location}\n最近的对话：\n用户：{user_input}\n助手：{assistant_reply[:100]}..."
        elif user_input and assistant_reply:
            # 保留之前的上下文，添加新对话
            self.conversation_context += f"\n用户：{user_input}\n助手：{assistant_reply[:100]}..."
            # 限制上下文长度,只保留最新的history对话信息
            if len(self.conversation_context) > 500:
                self.conversation_context = self.conversation_context[-400:]

    def run(self):
        """运行 Agent"""
        print(self.GREETING)

        while self.running:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "q", "退出"]:
                    print(self.GOODBYE)
                    self.running = False
                    continue

                print()  # 空行分隔思考过程

                # 判断是否是天气相关问题
                if self.is_weather_related(user_input):
                    self.handle_weather_with_retry(user_input)
                else:
                    self.handle_chat_stream(user_input)

            except KeyboardInterrupt:
                print("\n" + self.GOODBYE)
                self.running = False
            except Exception as e:
                print(f"\nAgent: Error: {e}")


def main():
    weather_key = os.getenv("WEATHER_API_KEY")
    llm_key = os.getenv("LLM_API_KEY")
    agent = TravelAgent(weather_key, llm_key)
    agent.run()


if __name__ == "__main__":
    main()
