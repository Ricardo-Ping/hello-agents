# my_llm.py
import os
from typing import Optional
from openai import OpenAI
from hello_agents import HelloAgentsLLM

class MyLLM(HelloAgentsLLM):
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "deepseek",
        **kwargs
    ):
        # 使用 DeepSeek 的 OpenAI 兼容接口
        if provider == "deepseek":
            print("正在使用自定义的 DeepSeek Provider")
            self.provider = "deepseek"
            
            # 解析 DeepSeek 的配置和凭证
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
            
            # 验证凭证是否存在
            if not self.api_key:
                raise ValueError("DeepSeek API key not found. Please set DEEPSEEK_API_KEY environment variable.")

            # 设置默认模型和其他参数
            self.model = model or os.getenv("DEEPSEEK_MODEL")
            self.temperature = kwargs.get('temperature', 0.7)
            self.max_tokens = kwargs.get('max_tokens')
            self.timeout = kwargs.get('timeout', 60)
            
            # 使用获取的参数创建OpenAI客户端实例
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

        else:
            # 其他 provider 完全使用父类的原始逻辑处理
            super().__init__(model=model, api_key=api_key, base_url=base_url, provider=provider, **kwargs)
