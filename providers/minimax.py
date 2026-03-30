from __future__ import annotations

from config import MINIMAX_API_KEY, MINIMAX_BASE_URL

from .base import BaseProvider, ProviderSettings


class MiniMaxProvider(BaseProvider):
    MODEL_NAMES = {
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
        "minimax-m2.7",
        "minimax-m2.7-highspeed",
        "minimax-m2.5",
        "minimax-m2.5-highspeed",
        "minimax-m2.1",
        "minimax-m2.1-highspeed",
        "minimax-m2",
    }

    def __init__(self) -> None:
        super().__init__(
            ProviderSettings(
                name="minimax",
                base_url=MINIMAX_BASE_URL,
                api_key=MINIMAX_API_KEY,
            )
        )

    def supports_json_mode(self, model: str) -> bool:
        # MiniMax OpenAI-compatible chat 接口目前未明确声明支持 response_format。
        return False