"""统一的 DeepSeek API 调用封装（MVP 全部 Agent 共用）"""
import json
import re
import httpx
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


def _extract_first_json_block(text: str) -> list | dict:
    """Extract the first valid JSON object/array from mixed text."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            data, _ = decoder.raw_decode(text[i:])
            if isinstance(data, (dict, list)):
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
) -> str:
    """调用 DeepSeek Chat API，返回文本内容。

    Args:
        model: 'deepseek-chat'（Scout/ArtDirector）或 'deepseek-reasoner'（Strategist/Writer）
    """
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
    }
    # deepseek-reasoner 不支持 temperature 参数
    if model != "deepseek-reasoner":
        payload["temperature"] = temperature

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
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


def parse_json_response(text: str) -> list | dict:
    """解析 LLM 返回的 JSON（兼容 markdown 代码块包裹、前后多余文本）。"""
    # 去除可能的 ```json ... ``` 包裹
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _extract_first_json_block(cleaned)
