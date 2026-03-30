"""统一的 LLM API 调用封装。"""
import json
import re
from providers import get_provider


def _try_repair_truncated_array(text: str) -> list | None:
    """Try to recover as many complete items as possible from a truncated JSON array."""
    m = re.search(r'\[', text)
    if not m:
        return None
    decoder = json.JSONDecoder()
    items: list = []
    tail = text[m.start() + 1:]  # content after opening '['
    while True:
        tail = tail.lstrip()
        if not tail or tail[0] == ']':
            break
        if tail[0] == ',':
            tail = tail[1:].lstrip()
        try:
            item, end = decoder.raw_decode(tail)
            items.append(item)
            tail = tail[end:]
        except json.JSONDecodeError:
            break  # truncated — stop here, keep what we have
    return items if items else None


def _extract_first_json_block(text: str) -> list | dict:
    """Extract the first valid JSON object/array from mixed text.
    Tries the outermost array first (with truncation repair), then falls back
    to scanning for the first parseable block.
    """
    decoder = json.JSONDecoder()
    # First pass: try to find the outermost '[' and repair if truncated
    outer_bracket = text.find('[')
    if outer_bracket != -1:
        try:
            data, _ = decoder.raw_decode(text[outer_bracket:])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            repaired = _try_repair_truncated_array(text[outer_bracket:])
            if repaired and len(repaired) >= 1:
                return repaired
    # Second pass: scan char-by-char for any parseable block, prefer objects over arrays of strings
    for i, ch in enumerate(text):
        if ch not in '[{':
            continue
        try:
            data, _ = decoder.raw_decode(text[i:])
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return data
        except json.JSONDecodeError:
            continue
    raise ValueError(f"无法从 LLM 返回中解析 JSON。原文前 500 字符:\n{text[:500]}")


async def chat(
    system_prompt: str,
    user_message: str,
    *,
    model: str = "deepseek-chat",
    temperature: float = 0.5,
    max_tokens: int = 4000,
    json_mode: bool = False,
) -> str:
    """调用 LLM Chat API，返回文本内容。

    支持模型:
        DeepSeek: 'deepseek-chat', 'deepseek-reasoner'
        Qwen:     'qwen-plus', 'qwen-max', 'qwen-turbo'
        MiniMax:  'MiniMax-M2.7', 'MiniMax-M2.7-highspeed', 'MiniMax-M2.5'
    """
    provider = get_provider(model)
    return await provider.chat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )


def parse_json_response(text: str) -> list | dict:
    """解析 LLM 返回的 JSON（兼容 markdown 代码块包裹、前后多余文本）。"""
    # 去除可能的 ```json ... ``` 包裹
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _extract_first_json_block(cleaned)
