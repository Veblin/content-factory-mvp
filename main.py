"""
内容工厂 MVP — 一键执行入口

用法:
    python main.py "五条悟复活, ComfyUI新教程, DeepSeek发布新模型"
    python main.py                   # 使用默认关键词
    python main.py --image-backend nano
    python main.py --image-backend sdxl
    python main.py "AI绘画, 二次元" --topic-count 10
"""
import argparse
import asyncio
from config import (
    ART_DIRECTOR_MODEL,
    EVIDENCE_MODEL,
    RESONANCE_MODEL,
    SCOUT_MODEL,
    STRATEGIST_MODEL,
    WRITER_MODEL,
)
from agents.resonance_analyst import ResonanceAnalyst
from agents.evidence_builder import EvidenceBuilder
from agents.scout import ScoutAgent
from agents.strategist import StrategistAgent
from agents.writer import WriterAgent
from agents.art_director import ArtDirectorAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="内容工厂 MVP — 小红书图文生成流水线")
    parser.add_argument(
        "ideas",
        nargs="?",
        default="AI绘画, 二次元",
        help="用户关键词，如: AI绘画, 二次元",
    )
    parser.add_argument(
        "--image-backend",
        choices=["nano", "sdxl"],
        default="nano",
        help="配图模型后端（默认 nano，可切换 sdxl）",
    )
    parser.add_argument(
        "--topic-count",
        type=int,
        default=10,
        help="候选选题数量（默认 10）",
    )
    return parser.parse_args()


def _parse_selection(choice: str, total: int, *, max_choices: int = 3) -> list[int]:
    indexes: list[int] = []
    for part in choice.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        idx = int(part)
        if idx < 1 or idx > total:
            raise IndexError(idx)
        if idx not in indexes:
            indexes.append(idx)
    if not indexes:
        raise ValueError("empty selection")
    return indexes[:max_choices]


async def run(user_ideas: str, image_backend: str = "nano", topic_count: int = 10):
    print("=" * 50)
    print("  内容工厂 MVP — 小红书图文生成流水线")
    print("=" * 50)
    print(f"\n📌 用户关键词: {user_ideas}\n")
    print("[LLM] 当前模型配置:")
    print(f"  · Scout: {SCOUT_MODEL}")
    print(f"  · Strategist: {STRATEGIST_MODEL}")
    print(f"  · Resonance: {RESONANCE_MODEL}")
    print(f"  · Evidence: {EVIDENCE_MODEL}")
    print(f"  · Writer: {WRITER_MODEL}")
    print(f"  · ArtDirector: {ART_DIRECTOR_MODEL}\n")

    # Step 1: 采集热点
    print("[Scout] 正在采集 B站 + 微博热点...")
    scout = ScoutAgent()
    hot_trends = await scout.crawl_and_filter()
    print(f"[Scout] ✅ 采集到 {len(hot_trends)} 条相关热点")
    for t in hot_trends[:5]:
        print(f"  · {t.get('topic', '')} ({t.get('source', '')}, 热度:{t.get('heat_score', 0)})")
    if len(hot_trends) > 5:
        print(f"  ... 共 {len(hot_trends)} 条")

    # Step 2: 选题评分
    keywords = [k.strip() for k in user_ideas.split(",") if k.strip()]
    if len(keywords) > 1:
        print(f"\n[Strategist] 检测到 {len(keywords)} 个独立主题，分别生成选题...")
        for kw in keywords:
            print(f"  · {kw}")
    else:
        print("\n[Strategist] 正在生成候选选题...")
    strategist = StrategistAgent()
    topics = await strategist.score(user_ideas, hot_trends, candidate_count=max(3, topic_count))
    print(f"[Strategist] ✅ 筛选完成，推荐 {len(topics)} 个选题\n")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t['title']}（{t['score']}/10）— {t.get('reason', '')}")

    # Step 3: 用户选择
    if len(topics) == 1:
        selected_topics = [topics[0]]
        print(f"\n只有 1 个选题，自动选择: {selected_topics[0]['title']}")
    else:
        choice = input("\n选哪些？输入编号，支持逗号分隔，最多 3 个: ").strip()
        try:
            selected_indexes = _parse_selection(choice, len(topics))
        except (ValueError, IndexError):
            print("无效选择，默认使用第 1 个")
            selected_indexes = [1]
        selected_topics = [topics[i - 1] for i in selected_indexes]
    print("\n✅ 已选择:")
    for selected in selected_topics:
        print(f"  - {selected['title']}")

    generated_files: list[str] = []
    resonance_analyst = ResonanceAnalyst()
    evidence_builder = EvidenceBuilder()
    writer = WriterAgent()
    art_director = ArtDirectorAgent()

    for i, selected in enumerate(selected_topics, 1):
        print(f"\n[Resonance] 正在分析第 {i}/{len(selected_topics)} 个选题的情绪入口...")
        resonance = await resonance_analyst.analyze(selected)
        print(f"[Resonance] 情绪入口: {resonance['emotional_need']}")
        print(f"[Resonance] 切入场景: {resonance['entry_scene']}")

        print("\n[Evidence] 正在生成内容 brief...")
        evidence = await evidence_builder.build(selected, resonance)
        print(f"[Evidence] 内容结构: {evidence['composition_type']}")
        print(f"[Evidence] 评论引导: {evidence['comment_trigger']}")

        print(f"\n[Writer] 正在生成第 {i}/{len(selected_topics)} 篇草稿...")
        draft = await writer.create(selected, resonance=resonance, evidence=evidence)
        generated_files.append(draft["file_path"])
        print(f"[Writer] ✅ 草稿已生成: {draft['file_path']}")

        print("\n[ArtDirector] 正在扩写配图候选 Prompt...")
        print(f"[ArtDirector] 当前配图模型后端: {image_backend}")
        try:
            prompt_pack = await art_director.expand_prompts(
                draft["base_image_prompts"], image_backend=image_backend
            )
            print(f"[ArtDirector] ✅ 已生成 {len(prompt_pack)} 条候选配图 Prompt")
            art_director.append_to_draft(draft["file_path"], prompt_pack)
            print(f"[ArtDirector] 候选 Prompt 已追加到草稿文件")
        except Exception as exc:
            print(f"[ArtDirector] ⚠️ 扩写失败，已保留 Writer 草稿。错误: {exc}")

    # 完成
    print("\n" + "=" * 50)
    print("  🎉 流程完成！")
    print("  草稿文件:")
    for file_path in generated_files:
        print(f"  - {file_path}")
    print("  下一步: 打开草稿 → 审核文字 → 用配图 Prompt 去 liblib 出图 → 发布")
    print("=" * 50)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.ideas, args.image_backend, args.topic_count))
