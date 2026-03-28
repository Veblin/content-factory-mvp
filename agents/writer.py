"""Writer Agent — 小红书图文内容生成"""
import json
import re
from datetime import date
from config import OUTPUT_DIR
from llm_client import chat, parse_json_response

SYSTEM_PROMPT = """你是小红书爆款内容创作专家。你会收到一个选题信息（JSON），请据此创作一篇小红书图文内容。

要求：
1. **标题**: 20字以内，吸引眼球，包含 1-2 个 emoji，有悬念感或获得感
2. **正文**: 800-1500 字，符合小红书风格：
   - 开头用 hook 抓住注意力
   - 分段清晰，每段 2-3 句话
   - 适当使用 emoji 增加可读性（不要过多）
   - 口语化表达，像朋友聊天
   - 包含实用干货或共鸣点
   - 结尾引导互动（提问/征集评论）
3. **tags**: 5-8 个小红书标签（带#号）
4. **base_image_prompts**: 5 条英文配图描述，用于 AI 生成配图。
   每条描述应具体、有画面感，适合 Stable Diffusion 生成。

输出 JSON：
{
  "title": "标题",
  "content": "正文内容",
  "tags": ["#标签1", "#标签2"],
  "base_image_prompts": ["prompt1", "prompt2", "prompt3", "prompt4", "prompt5"]
}

重要约束：
- 必须输出 JSON 对象（不是数组）
- 必须包含且仅包含以上 4 个字段
- tags 必须是字符串数组，base_image_prompts 必须是长度为 5 的字符串数组

只输出 JSON，不要其他内容。"""


class WriterAgent:
    async def create(self, topic: dict) -> dict:
        user_msg = json.dumps(topic, ensure_ascii=False, indent=2)
        result = await chat(
            SYSTEM_PROMPT, user_msg, model="deepseek-reasoner", temperature=0.7, max_tokens=4000
        )
        data = parse_json_response(result)
        if not isinstance(data, dict):
            raise ValueError(
                f"Writer 返回结构错误：期望 JSON 对象，实际是 {type(data).__name__}。"
            )

        required = ["title", "content", "tags", "base_image_prompts"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(
                "Writer 返回缺少必要字段: "
                f"{missing}。原始响应前 500 字符: {result[:500]}"
            )

        if not isinstance(data["title"], str) or not data["title"].strip():
            raise ValueError("Writer 返回字段错误：title 必须是非空字符串。")
        if not isinstance(data["content"], str) or not data["content"].strip():
            raise ValueError("Writer 返回字段错误：content 必须是非空字符串。")
        if not isinstance(data["tags"], list) or not all(isinstance(t, str) for t in data["tags"]):
            raise ValueError("Writer 返回字段错误：tags 必须是字符串数组。")
        if (
            not isinstance(data["base_image_prompts"], list)
            or len(data["base_image_prompts"]) != 5
            or not all(isinstance(p, str) for p in data["base_image_prompts"])
        ):
            raise ValueError("Writer 返回字段错误：base_image_prompts 必须是长度为 5 的字符串数组。")

        # 保存为 Markdown 草稿
        slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", data["title"])[:30].strip("-")
        filename = f"{date.today().isoformat()}-{slug}.md"
        file_path = OUTPUT_DIR / filename

        md_content = self._to_markdown(data)
        file_path.write_text(md_content, encoding="utf-8")

        return {
            "file_path": str(file_path),
            "base_image_prompts": data["base_image_prompts"],
        }

    @staticmethod
    def _to_markdown(data: dict) -> str:
        lines = [
            f"# {data['title']}",
            "",
            data["content"],
            "",
            "---",
            "",
            "**标签:** " + " ".join(data["tags"]),
            "",
            "---",
            "",
            "## 配图基础描述",
            "",
        ]
        for i, prompt in enumerate(data.get("base_image_prompts", []), 1):
            lines.append(f"{i}. {prompt}")
        lines.append("")
        return "\n".join(lines)
