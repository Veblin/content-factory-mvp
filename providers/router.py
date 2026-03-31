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
    if model.startswith("deepseek-"):
        return _DEEPSEEK_PROVIDER
    raise ValueError(
        f"未知模型: {model}。请检查 .env 中模型配置是否拼写正确。"
    )