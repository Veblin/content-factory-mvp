"""Writer Agent — 小红书图文内容生成"""
import json
import re
from datetime import date
from config import OUTPUT_DIR
from llm_client import chat, parse_json_response

SYSTEM_PROMPT = """你是小红书内容创作编辑。你会收到：
1. topic：选题对象
2. resonance：用户为什么会点进来的情绪画像
3. evidence：这条内容该如何展开的 content brief

要求：
1. **标题**: 20字以内，可以有 emoji，但不是必需。优先真实、具体、有代入感。
2. **正文**: 600-1200 字，必须满足：
    - 开头必须是具体场景，不要空喊“姐妹们、谁懂啊、幸福感爆棚”这类套话
    - 要先承接情绪，再给信息；不是写说明书，也不是堆感叹词
    - 至少出现 1 个真实瞬间、1 个细节锚点、1 个轻结论
    - 可以有轻教程或轻信息，但不要装作做了不存在的实测
    - 结尾互动必须具体，像在问同好，而不是泛泛 CTA
3. **tags**: 5-8 个标签，优先“情绪/场景/工具”组合
4. **base_image_prompts**: 5 条英文配图描述，用于 AI 生成配图。
    这些描述要和正文的情绪线、场景线一致，不要只是泛泛人物立绘。

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
- 不要伪造“我实测了多久/我涨粉了/我用了几次”这类事实
- 除非上下文有支撑，否则不要使用“幸福感爆棚 / 谁懂啊 / 治愈一整天 / 姐妹们冲”等空泛情绪表达

只输出 JSON，不要其他内容。"""

REVISION_PROMPT = """你是内容总编，请根据问题清单重写这篇内容，使其更像真人会发的小红书内容。

重写要求：
- 保留原主题，但去掉空泛煽情和模板口吻
- 必须补足具体场景、细节锚点和更自然的互动问题
- 不能捏造实测数据和夸张结果
- 如果没有真实测试证据，不要写成“我亲测/我实测/我试了一圈/我踩雷后发现”这类第一人称经验帖
- 输出格式仍然只能是 JSON 对象，字段保持 title/content/tags/base_image_prompts
"""


class WriterAgent:
    async def create(
        self,
        topic: dict,
        *,
        resonance: dict | None = None,
        evidence: dict | None = None,
    ) -> dict:
        payload = {
            "topic": topic,
            "resonance": resonance or {},
            "evidence": evidence or {},
        }
        user_msg = json.dumps(payload, ensure_ascii=False, indent=2)
        last_error: str | None = None
        data: dict | None = None
        for attempt in range(2):
            result = await chat(
                SYSTEM_PROMPT,
                user_msg,
                model="deepseek-chat",
                temperature=0.7 if attempt == 0 else 0.3,
                max_tokens=4000,
                json_mode=True,
            )
            try:
                parsed = parse_json_response(result)
                data = self._normalize_and_validate(parsed)
                critique = self._self_review(data, resonance or {}, evidence or {})
                if critique:
                    revised = await chat(
                        REVISION_PROMPT,
                        json.dumps(
                            {
                                "draft": data,
                                "topic": topic,
                                "resonance": resonance or {},
                                "evidence": evidence or {},
                                "issues": critique,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        model="deepseek-chat",
                        temperature=0.3,
                        max_tokens=4000,
                        json_mode=True,
                    )
                    data = self._normalize_and_validate(parse_json_response(revised))
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

        content_type = topic.get("content_type", "图文")
        composition_type = (evidence or {}).get("composition_type", "")
        md_content = self._to_markdown(data, content_type=content_type, composition_type=composition_type)
        file_path.write_text(md_content, encoding="utf-8")

        return {
            "file_path": str(file_path),
            "base_image_prompts": data["base_image_prompts"],
        }

    @staticmethod
    def _self_review(data: dict, resonance: dict, evidence: dict) -> list[str]:
        issues: list[str] = []
        content = str(data.get("content", ""))
        banned_phrases = ["幸福感爆棚", "谁懂啊", "治愈一整天", "姐妹们", "简直了"]

        # 开头第一行出现空泛情绪词，一条就触发
        first_line = content.split("\n")[0]
        if any(phrase in first_line for phrase in banned_phrases):
            issues.append("开头第一行出现了空泛情绪词（谁懂啊/姐妹们等），读者可能直接划走。")

        hit_count = sum(1 for phrase in banned_phrases if phrase in content)
        if hit_count >= 2:
            issues.append("正文出现过多空泛情绪词，容易显得像 AI 套话。")

        fake_experience_phrases = ["亲身踩雷", "实测", "我试了一圈", "我亲测", "我生成一个"]
        if any(phrase in content for phrase in fake_experience_phrases):
            issues.append("正文出现了未经证据支持的第一人称实测/踩雷表达。")

        has_anchor = any(detail in content for detail in evidence.get("micro_details", []))
        if evidence.get("micro_details") and not has_anchor:
            issues.append("正文缺少来自 brief 的微小细节锚点。")

        if resonance.get("entry_scene") and resonance["entry_scene"] not in content:
            issues.append("开头没有承接 resonance 提供的具体场景。")

        if evidence.get("comment_trigger") and evidence["comment_trigger"] not in content:
            issues.append("结尾互动问题不够具体，没有使用预设的 comment_trigger。")

        return issues

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
    def _to_markdown(
        data: dict,
        *,
        content_type: str = "图文",
        composition_type: str = "",
    ) -> str:
        type_line = f"**内容形式:** {content_type}"
        if composition_type:
            type_line += f" · {composition_type}"
        lines = [
            f"# {data['title']}",
            "",
            type_line,
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
