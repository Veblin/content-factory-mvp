from __future__ import annotations

from .deepseek import DeepSeekProvider
from .minimax import MiniMaxProvider
from .qwen import QwenProvider


_DEEPSEEK_PROVIDER = DeepSeekProvider()
_QWEN_PROVIDER = QwenProvider()
_MINIMAX_PROVIDER = MiniMaxProvider()


def get_provider(model: str):
    if model in QwenProvider.MODEL_NAMES:
        return _QWEN_PROVIDER
    if model in MiniMaxProvider.MODEL_NAMES:
        return _MINIMAX_PROVIDER
    return _DEEPSEEK_PROVIDER