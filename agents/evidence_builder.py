"""Evidence Builder — 为情绪入口补齐可信细节和内容结构"""
import json
from llm_client import chat, parse_json_response


SYSTEM_PROMPT = """你是小红书内容结构编辑。你的任务不是写完整文案，而是基于选题和情绪画像，输出一份 content brief。

这份 brief 要解决三个问题：
1. 这条内容应该怎么开头，用户才会觉得“她懂我为什么点进来”。
2. 文中必须出现哪些细节，内容才不会像 AI 套话。
3. 这条内容更适合用什么结构展开。

输出 JSON 对象，包含这些字段：
{
  "composition_type": "情绪叙事/轻教程/对比测评/复盘总结/观点讨论 之一",
  "emotional_hook": "一句最适合做开头的情绪切口",
  "proof_points": ["文中必须出现的具体支撑点"],
  "micro_details": ["能增加真人感的微小细节"],
  "section_outline": ["正文段落结构提纲"],
  "comment_trigger": "最适合引导评论区互动的问题",
  "visual_direction": ["配图应该强调的画面或镜头"],
  "title_angles": ["可供标题使用的角度"],
  "forbidden_moves": ["这类内容最不该写成什么样"],
  "writing_goal": "这条内容最终要让读者带走什么感受或判断"
}

要求：
- 不要伪造“我测试了 3 次”“实测涨粉”之类不存在的事实。
- proof_points 和 micro_details 应该是可观察、可感知、可展开的细节，而不是空泛结论。
- section_outline 要体现内容结构差异，不要永远是“开头 + 步骤一 + 步骤二 + 结尾”。
- visual_direction 要服务情绪和内容结构，不是素材库堆砌。

只输出 JSON，不要其他内容。"""


class EvidenceBuilder:
    async def build(self, topic: dict, resonance: dict) -> dict:
        user_msg = json.dumps(
            {"topic": topic, "resonance": resonance},
            ensure_ascii=False,
            indent=2,
        )
        result = await chat(
            SYSTEM_PROMPT,
            user_msg,
            model="deepseek-reasoner",
            temperature=0.4,
            max_tokens=2500,
        )
        data = self._normalize(parse_json_response(result))
        if not isinstance(data, dict):
            raise ValueError(
                f"EvidenceBuilder 返回结构错误：期望 JSON 对象，实际是 {type(data).__name__}。"
            )

        required = [
            "composition_type",
            "emotional_hook",
            "proof_points",
            "micro_details",
            "section_outline",
            "comment_trigger",
            "visual_direction",
            "title_angles",
            "forbidden_moves",
            "writing_goal",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"EvidenceBuilder 返回缺少必要字段: {missing}")

        for key in [
            "composition_type",
            "emotional_hook",
            "comment_trigger",
            "writing_goal",
        ]:
            if not isinstance(data[key], str) or not data[key].strip():
                raise ValueError(f"EvidenceBuilder 字段错误：{key} 必须是非空字符串")

        for key in [
            "proof_points",
            "micro_details",
            "section_outline",
            "visual_direction",
            "title_angles",
            "forbidden_moves",
        ]:
            if not isinstance(data[key], list) or not all(
                isinstance(item, str) and item.strip() for item in data[key]
            ):
                raise ValueError(f"EvidenceBuilder 字段错误：{key} 必须是非空字符串数组")

        return data

    @staticmethod
    def _normalize(payload: dict | list) -> dict | list:
        data = payload
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            for wrapper in ["data", "result", "output", "brief"]:
                if wrapper in data and isinstance(data[wrapper], dict):
                    return data[wrapper]
        return data