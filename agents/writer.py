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
        last_error: str | None = None
        data: dict | None = None
        for attempt in range(2):
            result = await chat(
                SYSTEM_PROMPT,
                user_msg,
                model="deepseek-reasoner",
                temperature=0.7 if attempt == 0 else 0.3,
                max_tokens=4000,
            )
            try:
                parsed = parse_json_response(result)
                data = self._normalize_and_validate(parsed)
                break
            except ValueError as exc:
                last_error = f"第 {attempt + 1} 次解析失败: {exc}. 原始响应前 500 字符: {result[:500]}"

        if data is None:
            raise ValueError(
                "Writer 连续 2 次生成结果都不符合结构要求。"
                f"最后一次错误: {last_error}"
            )

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
    def _normalize_and_validate(payload: dict | list) -> dict:
        data = payload
        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], dict):
                data = data[0]
            else:
                raise ValueError("Writer 返回结构错误：数组无法映射为单个对象")

        if not isinstance(data, dict):
            raise ValueError(
                f"Writer 返回结构错误：期望 JSON 对象，实际是 {type(data).__name__}"
            )

        for wrapper in ["data", "result", "output"]:
            if wrapper in data and isinstance(data[wrapper], dict):
                data = data[wrapper]
                break

        required = ["title", "content", "tags", "base_image_prompts"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Writer 返回缺少必要字段: {missing}")

        if not isinstance(data["title"], str) or not data["title"].strip():
            raise ValueError("Writer 返回字段错误：title 必须是非空字符串")
        if not isinstance(data["content"], str) or not data["content"].strip():
            raise ValueError("Writer 返回字段错误：content 必须是非空字符串")

        tags = data["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in re.split(r"[,，\s]+", tags) if t.strip()]
        if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
            raise ValueError("Writer 返回字段错误：tags 必须是非空字符串数组")
        data["tags"] = tags[:8]

        prompts = data["base_image_prompts"]
        if isinstance(prompts, str):
            prompts = [p.strip("- ") for p in prompts.splitlines() if p.strip()]
        if not isinstance(prompts, list) or not all(isinstance(p, str) and p.strip() for p in prompts):
            raise ValueError("Writer 返回字段错误：base_image_prompts 必须是字符串数组")
        if len(prompts) < 5:
            raise ValueError("Writer 返回字段错误：base_image_prompts 少于 5 条")
        data["base_image_prompts"] = prompts[:5]

        return data

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
