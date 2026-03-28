"""微博热搜采集 — 优先 AJAX API，降级 HTML 解析"""
import httpx
from bs4 import BeautifulSoup

AJAX_URL = "https://weibo.com/ajax/side/hotSearch"
FALLBACK_URL = "https://s.weibo.com/top/summary"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://weibo.com",
}


async def fetch_weibo_hot(limit: int = 30) -> str:
    """获取微博热搜，返回格式化文本摘要。"""
    try:
        return await _fetch_via_ajax(limit)
    except Exception:
        return await _fetch_via_html(limit)


async def _fetch_via_ajax(limit: int) -> str:
    """通过 AJAX 接口获取热搜。"""
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        resp = await client.get(AJAX_URL)
        resp.raise_for_status()
        data = resp.json()

    realtime = data.get("data", {}).get("realtime", [])[:limit]
    lines = []
    for item in realtime:
        word = item.get("word", "")
        num = item.get("num", 0)
        label = item.get("label_name", "")
        tag = f" [{label}]" if label else ""
        lines.append(f"{word} | 热度:{num}{tag}")

    return "\n".join(lines)


async def _fetch_via_html(limit: int) -> str:
    """降级方案：HTML 解析微博热搜榜。"""
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        resp = await client.get(FALLBACK_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select("td.td-02 a")[:limit]
    lines = [a.get_text(strip=True) for a in items if a.get_text(strip=True)]
    return "\n".join(lines)
