from __future__ import annotations

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

from .base import BaseProvider, ProviderSettings


class DeepSeekProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(
            ProviderSettings(
                name="deepseek",
                base_url=DEEPSEEK_BASE_URL,
                api_key=DEEPSEEK_API_KEY,
            )
        )

    def supports_temperature(self, model: str) -> bool:
        return model != "deepseek-reasoner"

    def supports_json_mode(self, model: str) -> bool:
        return model != "deepseek-reasoner"