from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    base_url: str
    api_key: str


class BaseProvider:
    def __init__(self, settings: ProviderSettings) -> None:
        self.settings = settings

    def validate(self, model: str) -> None:
        if not self.settings.api_key:
            raise ValueError(
                f"使用模型 {model} 需要在 .env 中配置 {self.settings.name.upper()}_API_KEY"
            )

    def supports_temperature(self, model: str) -> bool:
        return True

    def supports_json_mode(self, model: str) -> bool:
        return True

    def build_payload(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> dict:
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
        }
        if self.supports_temperature(model):
            payload["temperature"] = temperature
        if json_mode:
            if not self.supports_json_mode(model):
                raise ValueError(
                    f"模型 {model} 不支持 JSON mode，但当前任务要求结构化 JSON 输出。"
                )
            payload["response_format"] = {"type": "json_object"}
        return payload

    def endpoint(self) -> str:
        return f"{self.settings.base_url}/chat/completions"

    async def chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        self.validate(model)
        payload = self.build_payload(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                self.endpoint(),
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise ValueError(
                f"LLM returned empty content. "
                f"Model: {model}, finish_reason: {data['choices'][0].get('finish_reason')}"
            )
        return content