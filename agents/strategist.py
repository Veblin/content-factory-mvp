"""Strategist Agent — 选题评分与推荐"""
from llm_client import chat, parse_json_response
import json

SYSTEM_PROMPT = """你是内容选题策略师，专注于小红书 AI/AIGC/二次元领域。你会收到：
1. 用户感兴趣的关键词
2. 经过筛选的热点列表（JSON）

## 行业认知（重要）
- **主流 AI 绘画工具 (2026)**：即梦（字节）、可灵（快手）、Nano Banana 是当前最活跃的平台，用户增长快，适合做教程和测评
- **ComfyUI**：偏技术向、受众窄，普通用户门槛高，除非结合极具话题性的案例否则不建议作为主选题
- **Midjourney**：仍有知名度但国内热度下降，可作为对比素材但不宜单独做主题
- **Stable Diffusion / SDXL**：开源生态仍在，但小红书受众更关注"开箱即用"的产品体验
- **AI 视频**：Seedance、可灵视频、Sora 等是热点方向

## 受众画像（小红书）
- 70%+ 女性用户，18-35 岁为主
- "二次元老公" 相关话题互动量是 "二次元老婆" 的 3-5 倍（女性用户驱动互动）
- 偏好：颜值向、实用教程、种草测评、情绪共鸣
- 反感：纯技术堆砌、男性视角自嗨内容

## 评分维度（共 4 项，每项 0-10）
1. 热度契合度：是否踩中当前热点
2. 内容差异化：是否有独特切入角度
3. 目标受众匹配：是否适合小红书女性用户群体
4. 互动潜力：是否容易引发评论、收藏、转发

请结合上述行业知识和受众画像，生成候选选题池。

生成要求：
- 默认按用户要求生成 8-10 个候选选题
- 强调多样性，不要只围绕同一个词反复改写
- 选题形式至少覆盖 4 种以上（教程/测评/对比/观点/清单/复盘/故事向/热点解读）
- 标题句式要有变化，避免连续出现同类模板
- 可以保留“二次元老公”这类高互动表达，但不要让整个候选池过度依赖单一词汇
- 每个选题尽量补充后续创作可用的信息：emotional_trigger、entry_scene、content_form、comment_trigger

输出 JSON 数组，按总分降序排列：
[{
  "title": "选题标题",
  "angle": "切入角度描述",
    "score": 8.5,
  "keywords": ["关键词1", "关键词2"],
    "reason": "推荐理由（一句话）",
    "emotional_trigger": "用户为什么会点进来",
    "entry_scene": "适合开头切入的场景",
    "content_form": "教程/测评/复盘/观点/故事向之一",
    "content_type": "图文/视频 之一",
    "comment_trigger": "适合引导互动的问题"
}]

注意：
- score 字段必须是最终总分，范围 0-10，可以保留 1 位小数
- 不要输出 4 个维度的分项分数，也不要把 4 个维度直接相加成 20 分、40 分之类的数值

只输出 JSON，不要其他内容。"""


class StrategistAgent:
    async def score(
        self,
        user_ideas: str,
        hot_trends: list[dict],
        *,
        candidate_count: int = 10,
    ) -> list[dict]:
        user_msg = (
            f"## 用户兴趣关键词\n{user_ideas}\n\n"
            f"## 目标候选数\n请输出 {candidate_count} 个候选选题。\n\n"
            f"## 热点数据\n{json.dumps(hot_trends, ensure_ascii=False, indent=2)}"
        )
        last_error: str | None = None
        for attempt in range(2):
            prompt = SYSTEM_PROMPT
            if attempt == 1:
                prompt += (
                    "\n\n补充约束：必须输出 JSON 对象数组；数组中的每一项都必须是对象，"
                    "禁止输出单独的关键词数组、字符串数组或额外说明。"
                )
            result = await chat(
                prompt,
                user_msg,
                model="deepseek-chat",
                temperature=0.3,
                max_tokens=6000,
                json_mode=True,
            )
            try:
                data = self._normalize_and_validate(parse_json_response(result))
                return data[:candidate_count]
            except ValueError as exc:
                last_error = f"第 {attempt + 1} 次失败: {exc}. 原始响应前 500 字符: {result[:500]}"

        raise ValueError(
            "Strategist 连续 2 次生成结果都不符合结构要求。"
            f"最后一次错误: {last_error}"
        )

    @staticmethod
    def _normalize_and_validate(payload: dict | list) -> list[dict]:
        data = payload
        if isinstance(data, dict):
            for wrapper in ["topics", "items", "data", "result", "output"]:
                if wrapper in data and isinstance(data[wrapper], list):
                    data = data[wrapper]
                    break
            else:
                if "title" in data and "score" in data:
                    data = [data]

        if not isinstance(data, list):
            raise ValueError(
                f"Strategist 返回结构错误：期望 JSON 数组，实际是 {type(data).__name__}。"
            )

        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                raise ValueError(f"Strategist 第 {i} 项不是对象：{item}")
            for key in ["title", "score"]:
                if key not in item:
                    raise ValueError(f"Strategist 第 {i} 项缺少字段 {key}：{item}")

        return data
