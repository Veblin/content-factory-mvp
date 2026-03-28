"""
内容工厂 MVP — 一键执行入口

用法:
    python main.py "五条悟复活, ComfyUI新教程, DeepSeek发布新模型"
    python main.py                   # 使用默认关键词
    python main.py --image-backend nano
    python main.py --image-backend sdxl
"""
import argparse
import asyncio
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
    return parser.parse_args()


async def run(user_ideas: str, image_backend: str = "nano"):
    print("=" * 50)
    print("  内容工厂 MVP — 小红书图文生成流水线")
    print("=" * 50)
    print(f"\n📌 用户关键词: {user_ideas}\n")

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
    print("\n[Strategist] 正在生成选题方案...")
    strategist = StrategistAgent()
    topics = await strategist.score(user_ideas, hot_trends)
    print(f"[Strategist] ✅ 推荐 {len(topics)} 个选题\n")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t['title']}（{t['score']}/10）— {t.get('reason', '')}")

    # Step 3: 用户选择
    if len(topics) == 1:
        selected = topics[0]
        print(f"\n只有 1 个选题，自动选择: {selected['title']}")
    else:
        choice = input("\n选哪个？输入编号: ").strip()
        try:
            selected = topics[int(choice) - 1]
        except (ValueError, IndexError):
            print("无效选择，默认使用第 1 个")
            selected = topics[0]
    print(f"\n✅ 已选择: {selected['title']}\n")

    # Step 4: 生成内容
    print("[Writer] 正在生成小红书图文草稿...")
    writer = WriterAgent()
    draft = await writer.create(selected)
    print(f"[Writer] ✅ 草稿已生成: {draft['file_path']}")

    # Step 5: 扩写配图候选
    print("\n[ArtDirector] 正在扩写配图候选 Prompt...")
    print(f"[ArtDirector] 当前配图模型后端: {image_backend}")
    art_director = ArtDirectorAgent()
    prompt_pack = await art_director.expand_prompts(
        draft["base_image_prompts"], image_backend=image_backend
    )
    print(f"[ArtDirector] ✅ 已生成 {len(prompt_pack)} 条候选配图 Prompt")

    # 将候选 Prompt 追加到草稿
    art_director.append_to_draft(draft["file_path"], prompt_pack)
    print(f"[ArtDirector] 候选 Prompt 已追加到草稿文件")

    # 完成
    print("\n" + "=" * 50)
    print("  🎉 流程完成！")
    print(f"  草稿文件: {draft['file_path']}")
    print("  下一步: 打开草稿 → 审核文字 → 用配图 Prompt 去 liblib 出图 → 发布")
    print("=" * 50)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.ideas, args.image_backend))
