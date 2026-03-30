"""ArtDirector Agent (Lite) — 配图 Prompt 候选扩写"""
import json
from llm_client import chat, parse_json_response

def _build_system_prompt(image_backend: str) -> str:
    if image_backend == "sdxl":
        return """你是配图导演助手。基于用户给出的基础配图描述，扩写成 20 条候选 Stable Diffusion XL Prompt。

每条需包含：
- positive_prompt: 正向提示词（英文，详细描述画面）
- negative_prompt: 反向提示词（英文，排除不想要的元素）
- model: 推荐模型（如 "sd_xl_base_1.0", "dreamshaperXL", "animagineXL"）
- size: 推荐尺寸（如 "1024x1024", "768x1024", "1024x768"）
- style_tag: 风格标签（如 "anime", "photorealistic", "illustration", "flat design"）

排序规则：稳妥安全的排前面，创意实验性的排后面。
只输出 JSON 数组，不要其他内容。"""

    return """你是配图导演助手。基于用户给出的基础配图描述，扩写成 20 条候选配图 Prompt。

目标平台：Nano Banana Pro（默认）

每条需包含：
- positive_prompt: 正向提示词（英文，详细描述画面）
- negative_prompt: 反向提示词（英文，排除不想要的元素）
- model: 固定写 "nano-banana-pro"
- size: 推荐尺寸（如 "1024x1024", "768x1024", "1024x768"）
- style_tag: 风格标签（如 "anime", "photorealistic", "illustration", "flat design"）

排序规则：稳妥安全的排前面，创意实验性的排后面。
只输出 JSON 数组，不要其他内容。"""


class ArtDirectorAgent:
    async def expand_prompts(self, base_prompts: list[str], *, image_backend: str = "nano") -> list[dict]:
        if image_backend not in {"nano", "sdxl"}:
            raise ValueError(
                f"不支持的 image_backend: {image_backend}。可选值: nano, sdxl"
            )

        user_input = "\n".join([f"- {p}" for p in base_prompts])
        system_prompt = _build_system_prompt(image_backend)
        last_error: str | None = None

        # LLM 偶发会输出被截断的 JSON，重试一次并降低随机性提升稳定性
        for attempt in range(2):
            final_prompt = system_prompt
            if attempt == 1:
                final_prompt += "\n\n补充约束：每条 positive_prompt / negative_prompt 请控制在 40 个英文词以内，避免冗长导致输出截断。"

            result = await chat(
                final_prompt,
                user_input,
                model="deepseek-chat",
                temperature=0.8 if attempt == 0 else 0.4,
                max_tokens=5000,
                json_mode=True,
            )

            try:
                data = parse_json_response(result)
                if not isinstance(data, list):
                    raise ValueError(
                        f"ArtDirector 返回结构错误：期望 JSON 数组，实际是 {type(data).__name__}。"
                    )
                required_keys = ["positive_prompt", "negative_prompt", "model", "size", "style_tag"]
                for i, item in enumerate(data, 1):
                    if not isinstance(item, dict):
                        raise ValueError(f"ArtDirector 第 {i} 项不是对象：{item}")
                    if image_backend == "nano":
                        item["model"] = "nano-banana-pro"
                    missing = [k for k in required_keys if k not in item]
                    if missing:
                        raise ValueError(f"ArtDirector 第 {i} 项缺少字段 {missing}：{item}")
                return data
            except ValueError as exc:
                last_error = f"第 {attempt + 1} 次失败: {exc}. 原始响应前 500 字符: {result[:500]}"

        raise ValueError(
            "ArtDirector 连续 2 次生成结果都不符合结构要求。"
            f"最后一次错误: {last_error}"
        )

    @staticmethod
    def append_to_draft(file_path: str, prompt_pack: list[dict]) -> None:
        """将候选配图 Prompt 追加到草稿 Markdown 文件。"""
        lines = [
            "",
            "---",
            "",
            "## 候选配图 Prompt（共 {} 条）".format(len(prompt_pack)),
            "",
        ]
        for i, p in enumerate(prompt_pack, 1):
            lines.append(f"### 候选 {i} [{p.get('style_tag', '')}]")
            lines.append(f"- **Positive:** {p.get('positive_prompt', '')}")
            lines.append(f"- **Negative:** {p.get('negative_prompt', '')}")
            lines.append(f"- **Model:** {p.get('model', '')} | **Size:** {p.get('size', '')}")
            lines.append("")

        from pathlib import Path

        with Path(file_path).open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
