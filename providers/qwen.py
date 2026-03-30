from __future__ import annotations

from config import QWEN_API_KEY, QWEN_BASE_URL

from .base import BaseProvider, ProviderSettings


class QwenProvider(BaseProvider):
    MODEL_NAMES = {"qwen-plus", "qwen-max", "qwen-turbo"}

    def __init__(self) -> None:
        super().__init__(
            ProviderSettings(
                name="qwen",
                base_url=QWEN_BASE_URL,
                api_key=QWEN_API_KEY,
            )
        )