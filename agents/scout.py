"""Scout Agent — 热点采集与 LLM 过滤（B站 + 微博）"""
from config import SCOUT_MODEL
from crawlers.bilibili import fetch_bilibili_hot
from crawlers.weibo import fetch_weibo_hot
from llm_client import chat, parse_json_response

SYSTEM_PROMPT = """你是热点采集助手。我会给你 B站和微博的原始热点数据。
请只保留 AI/AIGC/二次元/技术 相关的条目，给每条打热度分(0-100)。
输出 JSON 数组: [{"source":"bilibili","topic":"...","heat_score":80,"tags":["AI"]}]
不相关的全部丢弃。只输出 JSON，不要其他内容。"""


class ScoutAgent:
    async def crawl_and_filter(self) -> list[dict]:
        bilibili = await fetch_bilibili_hot()
        weibo = await fetch_weibo_hot()
        raw = f"## B站热门\n{bilibili}\n\n## 微博热搜\n{weibo}"

        result = await chat(SYSTEM_PROMPT, raw, model=SCOUT_MODEL, temperature=0.1, json_mode=True)
        return parse_json_response(result)
