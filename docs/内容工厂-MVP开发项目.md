# 内容工厂 MVP — 开发项目文档

> 本文档包含 MVP 的全部开发相关内容：架构、代码结构、核心代码、环境配置、演进路径和日常工作流。
> Agent 的详细配置（System Prompt / 参数 / 工具）见 [[内容工厂-MVP AI Agents]]。

---

## 1. 架构简化：6 Agent → 4 Agent

```
完整方案                           MVP 方案
─────────                         ─────────
Dispatcher ←── 用户入口            ❌ 砍掉 → CLI 脚本直接调用
Scout      ←── 热点采集            ✅ 保留（简化为 2 源）
Strategist ←── 选题评分            ✅ 保留（简化评分）
Writer     ←── 内容创作            ✅ 保留（只做小红书）
ArtDirector ← 配图生成            ✅ 保留（轻量版，多候选供选择）
Compliance ←── 合规审核            ❌ 砍掉 → 人工肉眼审核
```

**全部 Agent 统一使用 DeepSeek Provider（Scout/ArtDirector: `deepseek-chat`；Strategist/Writer: `deepseek-reansoner`），只需 1 个 API Key。**

---

## 2. 架构图

```
                    你（CLI 终端）
                        │
                  python main.py
                        │
               ┌────────┴────────┐
               │                 │
            ┌────▼────┐     ┌─────▼──────┐
            │  Scout   │     │ Strategist │
            │ DS V3.2  │     │  DS V3.2   │
            └────┬─────┘     └─────┬──────┘
               │                 │
               └───────┬─────────┘
                     │
                 ┌─────▼─────┐
                 │  Writer   │
                 │  DS V3.2  │
                 └─────┬─────┘
                     │
                ┌──────▼──────┐
                │ ArtDirector │
                │ Lite (DS)   │
                └──────┬──────┘
                     │
            Markdown 草稿 + 多候选配图 Prompt
                     │
              你手动出图 + 审核 + 发布
```

---

## 3. 代码结构（~12 个文件）

```
content-factory-mvp/
├── main.py                  # 入口：一键跑完全流程
├── agents/
│   ├── scout.py             # 热点采集（B站+微博）
│   ├── strategist.py        # 选题评分
│   ├── writer.py            # 小红书图文生成
│   └── art_director.py      # 配图 Prompt 扩写（多候选）
├── crawlers/
│   ├── bilibili.py          # B站热门 API
│   └── weibo.py             # 微博热搜解析
├── llm_client.py            # DeepSeek API 封装（统一）
├── config.py                # 配置加载
├── output/                  # 生成的草稿
│   └── 2026-03-28-xxx.md
├── data/
│   └── manual_topics.json   # 手动录入的话题
├── .env                     # API Key
├── .env.example
└── requirements.txt
```

---

## 4. 核心代码

### main.py — 一键执行入口

```python
"""
用法: python main.py "五条悟复活, ComfyUI新教程, DeepSeek发布新模型"
"""
import sys, asyncio
from agents.scout import ScoutAgent
from agents.strategist import StrategistAgent
from agents.writer import WriterAgent
from agents.art_director import ArtDirectorAgent

async def run(user_ideas: str):
    # Step 1: 采集热点
    scout = ScoutAgent()
    hot_trends = await scout.crawl_and_filter()
    print(f"[Scout] 采集到 {len(hot_trends)} 条相关热点")

    # Step 2: 选题评分
    strategist = StrategistAgent()
    topics = await strategist.score(user_ideas, hot_trends)
    print(f"[Strategist] 推荐 {len(topics)} 个选题")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t['title']}（{t['score']}/10）")

    # Step 3: 用户选择（CLI 交互）
    choice = input("\n选哪个？输入编号: ")
    selected = topics[int(choice) - 1]

    # Step 4: 生成内容
    writer = WriterAgent()
    draft = await writer.create(selected)
    print(f"\n[Writer] 草稿已生成: {draft['file_path']}")

    # Step 5: 扩写配图候选（ArtDirector Lite）
    art_director = ArtDirectorAgent()
    prompt_pack = await art_director.expand_prompts(draft["base_image_prompts"])
    print(f"[ArtDirector] 已生成 {len(prompt_pack)} 条候选配图 Prompt")

if __name__ == "__main__":
    ideas = sys.argv[1] if len(sys.argv) > 1 else "AI绘画, 二次元"
    asyncio.run(run(ideas))
```

### llm_client.py — 统一 LLM 封装

```python
"""统一的 DeepSeek API 调用（MVP 只用这一个模型）"""
import httpx, os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com/v1"

async def chat(system_prompt: str, user_message: str,
               temperature: float = 0.5, max_tokens: int = 4000) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
```

### agents/scout.py — 热点采集

```python
"""Scout MVP: B站 + 微博，关键词过滤"""
from crawlers.bilibili import fetch_bilibili_hot
from crawlers.weibo import fetch_weibo_hot
from llm_client import chat

SYSTEM_PROMPT = """你是热点采集助手。我会给你 B站和微博的原始热点数据。
请只保留 AI/AIGC/二次元/技术 相关的条目，给每条打热度分(0-100)。
输出 JSON 数组: [{"source":"bilibili","topic":"...","heat_score":80,"tags":["AI"]}]
不相关的全部丢弃。只输出 JSON，不要其他内容。"""

class ScoutAgent:
    async def crawl_and_filter(self) -> list[dict]:
        bilibili = await fetch_bilibili_hot()
        weibo = await fetch_weibo_hot()
        raw = f"## B站热门\n{bilibili}\n\n## 微博热搜\n{weibo}"
        result = await chat(SYSTEM_PROMPT, raw, temperature=0.1)
        import json
        return json.loads(result)
```

### agents/art_director.py — 配图候选扩写

```python
"""ArtDirector MVP Lite: 将基础配图描述扩写成多候选 Prompt"""
from llm_client import chat

SYSTEM_PROMPT = """你是配图导演助手。基于 5 条基础描述，扩写成 20 条候选 Prompt。
每条需包含: positive prompt, negative prompt, model, size, style_tag。
按稳妥优先排序。只输出 JSON 数组。"""

class ArtDirectorAgent:
    async def expand_prompts(self, base_prompts: list[str]) -> list[dict]:
        user_input = "\n".join([f"- {p}" for p in base_prompts])
        result = await chat(SYSTEM_PROMPT, user_input, temperature=0.8, max_tokens=3000)
        import json
        return json.loads(result)
```

---

## 5. 环境配置 & 运行

### 环境变量

```bash
# .env — MVP 只需要这一个
DEEPSEEK_API_KEY=sk-xxx
```

### 安装 & 运行

```bash
# 1. 创建项目
mkdir content-factory-mvp && cd content-factory-mvp
python3 -m venv .venv && source .venv/bin/activate

# 2. 安装依赖（只有 3 个）
pip install httpx beautifulsoup4 python-dotenv

# 3. 配置 API Key
echo "DEEPSEEK_API_KEY=sk-xxx" > .env

# 4. 运行
python main.py "五条悟复活, ComfyUI新教程"
```

### 成本

| 项       | MVP 月成本 | 说明                                        |
| -------- | ---------- | ------------------------------------------- |
| DeepSeek | **¥25-50** | 所有 Agent 共用（含 ArtDirector Lite 扩写） |
| 图片生成 | **¥0**     | 手动用 liblib 网页版免费额度                |
| 服务器   | ¥0         | 本地 MBP                                    |
| **合计** | **¥25-50** | vs 完整方案 ¥200-280                        |

---

## 6. 从 MVP → 完整方案的演进路径

```
MVP（你在这里）          Phase 2              Phase 3              完整方案
──────────────          ─────────            ─────────            ─────────
4 Agent + CLI            + 图片API自动化      + Compliance         + Dispatcher
DS V3.2 only             + liblib API         + 违禁词库           + MiniMax M2.5
B站 + 微博               + 知乎 + GitHub      + 向量去重           + IM 机器人
只做小红书               + Nano Banana        + 公众号模板         + 三平台自动化
手动审核/手动出图        + Qwen-VL 评分       + IP 版权库          + 全自动流水线
12 个文件                ~30 个文件           ~45 个文件           ~60 个文件
¥20-40/月               ¥80-150/月          ¥150-250/月         ¥200-400/月
```

### 每个阶段的升级触发条件

| 升级               | 时机                 | 原因                               |
| ------------------ | -------------------- | ---------------------------------- |
| MVP → Phase 2      | **产出 5 篇内容后**  | 手动配图变成瓶颈，需要自动化       |
| Phase 2 → Phase 3  | **小红书粉丝过 500** | 内容量增大，需要合规审核避免封号   |
| Phase 3 → 完整方案 | **三平台同时运营**   | 需要手机操作、跨平台改写、全自动化 |

---

## 7. MVP 日常工作流

```
每周一次（约 30 分钟）:

1. [2分钟] 打开小红书 app，浏览热门话题，记到 manual_topics.json
2. [1分钟] 在终端运行:
   python main.py "本周想法关键词"
3. [3分钟] 看 Scout 输出的热点 + Strategist 推荐的选题，选一个
4. [等 30 秒] Writer 自动生成小红书图文草稿
5. [5分钟] 打开 output/ 目录，审核 Markdown 草稿，微调措辞
6. [8分钟] 用配图 Prompt 去 liblib 网页版生成 6-9 张图，筛出最终 3 张图
7. [5分钟] 复制文字 + 图片到小红书 app，发布

一周重复 1-2 次 = 每周 40-80 分钟产出 1-2 篇内容
```

---

## 8. 与完整方案的对照

| 维度       | 完整方案                               | MVP                             |
| ---------- | -------------------------------------- | ------------------------------- |
| Agent 数量 | 6 个                                   | **4 个**（含 ArtDirector Lite） |
| LLM 模型数 | 5 个（MiniMax/DS/Qwen/Qwen-VL/Claude） | **1 个**（DeepSeek V3.2）       |
| API Key    | 6 个                                   | **1 个**                        |
| 数据源     | 4 个 + 手动                            | **2 个**（B站+微博）            |
| 平台       | 小红书 + 公众号 + 视频号               | **小红书** only                 |
| 图片生成   | liblib API + Nano Banana API           | **手动**（但 Prompt 候选更多）  |
| 合规       | AC 自动机 + LLM 语义审核               | **人工**                        |
| 交互       | IM 机器人（手机）                      | **CLI**（终端）                 |
| MCP Server | 3 个（25 个工具）                      | **0 个**（直接函数调用）        |
| 依赖包     | ~15 个                                 | **3 个**（httpx/bs4/dotenv）    |
| 文件数     | ~60 个                                 | **~12 个**                      |
| 月成本     | ¥200-400                               | **¥25-50**                      |
| 搭建时间   | 3-4 周                                 | **3 天**                        |
