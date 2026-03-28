"""B站热门视频采集 — 调用公开 popular API"""
import httpx

API_URL = "https://api.bilibili.com/x/web-interface/popular"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
}


async def fetch_bilibili_hot(limit: int = 30) -> str:
    """获取 B站热门视频，返回格式化文本摘要。"""
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        resp = await client.get(API_URL, params={"ps": 50, "pn": 1})
        resp.raise_for_status()
        data = resp.json()

    items = data.get("data", {}).get("list", [])[:limit]
    lines = []
    for item in items:
        title = item.get("title", "")
        tname = item.get("tname", "")
        owner = item.get("owner", {}).get("name", "")
        view = item.get("stat", {}).get("view", 0)
        desc = (item.get("desc") or "")[:80]
        lines.append(f"[{tname}] {title} | UP主:{owner} | 播放:{view} | {desc}")

    return "\n".join(lines)
