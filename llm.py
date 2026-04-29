"""LLM 聊天模块"""
import os
import json
from typing import List, Iterator

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LLMError(Exception):
    """LLM 异常"""
    pass


class ChatMessage:
    """聊天消息"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class ChatClient:
    """LLM 聊天客户端"""

    API_URL = "https://luckyapi.chat"
    MODEL = "z-ai/glm-4.5-air:free"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.messages: List[ChatMessage] = []

    def _build_messages(self, user_input: str, system_prompt: str = "") -> List[dict]:
        """构建消息列表"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend([m.to_dict() for m in self.messages])
        messages.append({"role": "user", "content": user_input})
        return messages

    def chat(self, user_input: str, system_prompt: str = "") -> str:
        """发送聊天消息（非流式）"""
        messages = self._build_messages(user_input, system_prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.MODEL,
            "messages": messages,
            "stream": False
        }

        try:
            session = requests.Session()
            session.trust_env = False

            resp = session.post(
                f"{self.API_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]

            self.messages.append(ChatMessage("user", user_input))
            self.messages.append(ChatMessage("assistant", reply))

            return reply
        except Exception as e:
            raise LLMError(f"LLM API 调用失败: {e}")

    def chat_stream(self, user_input: str, system_prompt: str = "") -> Iterator[str]:
        """发送聊天消息（流式）

        Args:
            user_input: 用户输入
            system_prompt: 系统提示词

        Yields:
            每次返回一个文本片段
        """
        messages = self._build_messages(user_input, system_prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.MODEL,
            "messages": messages,
            "stream": True
        }

        try:
            session = requests.Session()
            session.trust_env = False

            resp = session.post(
                f"{self.API_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
                stream=True
            )
            resp.raise_for_status()

            full_reply = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            chunk = delta["content"]
                            full_reply += chunk
                            yield chunk
                    except json.JSONDecodeError:
                        continue

            # 保存到历史
            self.messages.append(ChatMessage("user", user_input))
            self.messages.append(ChatMessage("assistant", full_reply))

        except Exception as e:
            raise LLMError(f"LLM API 调用失败: {e}")

    def reset(self):
        """重置对话历史"""
        self.messages = []


def get_llm_client() -> ChatClient:
    """获取 LLM 客户端"""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("未设置 LLM_API_KEY")
    return ChatClient(api_key)
