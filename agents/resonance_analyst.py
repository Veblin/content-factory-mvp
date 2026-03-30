"""Resonance Analyst — 将表层选题翻译成用户真实情绪入口"""
import json
from config import RESONANCE_MODEL
from llm_client import chat, parse_json_response


SYSTEM_PROMPT = """你是小红书内容情绪洞察师。你的任务不是写文案，而是回答：
用户为什么会点进来，为什么愿意停下来继续看。

你会收到一个选题对象，请输出一个 resonance profile，帮助后续 Writer 写出更像真人的内容。

输出 JSON 对象，包含这些字段：
{
  "emotional_need": "用户真正的情绪需求",
  "click_impulse": "用户点进来的那一下在想什么",
  "consumption_moment": "她通常在什么场景下看这条内容",
  "desired_payoff": "看完后她希望获得什么感受或结果",
  "persona_voice": "更贴近目标用户的表达口吻说明",
  "credibility_guardrails": ["为了避免假，写作时必须避免的表达或姿态"],
  "anti_patterns": ["最容易出现的 AI 味或空泛写法"],
  "entry_scene": "最适合开头切入的具体场景"
}

要求：
- 不要输出空泛的“陪伴感/情绪价值”四字词，尽量写成具体心理活动。
- 不要捏造具体数据和虚假实测结论。
- 重点描述“为什么点开”，不是“为什么应该学习”。

只输出 JSON，不要其他内容。"""


class ResonanceAnalyst:
    async def analyze(self, topic: dict) -> dict:
        user_msg = json.dumps(topic, ensure_ascii=False, indent=2)
        result = await chat(
            SYSTEM_PROMPT,
            user_msg,
            model=RESONANCE_MODEL,
            temperature=0.3,
            max_tokens=2000,
            json_mode=True,
        )
        data = self._normalize(parse_json_response(result))
        if not isinstance(data, dict):
            raise ValueError(
                f"ResonanceAnalyst 返回结构错误：期望 JSON 对象，实际是 {type(data).__name__}。"
            )

        required = [
            "emotional_need",
            "click_impulse",
            "consumption_moment",
            "desired_payoff",
            "persona_voice",
            "credibility_guardrails",
            "anti_patterns",
            "entry_scene",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"ResonanceAnalyst 返回缺少必要字段: {missing}")

        for key in [
            "emotional_need",
            "click_impulse",
            "consumption_moment",
            "desired_payoff",
            "persona_voice",
            "entry_scene",
        ]:
            if not isinstance(data[key], str) or not data[key].strip():
                raise ValueError(f"ResonanceAnalyst 字段错误：{key} 必须是非空字符串")

        for key in ["credibility_guardrails", "anti_patterns"]:
            if not isinstance(data[key], list) or not all(
                isinstance(item, str) and item.strip() for item in data[key]
            ):
                raise ValueError(f"ResonanceAnalyst 字段错误：{key} 必须是非空字符串数组")

        return data

    @staticmethod
    def _normalize(payload: dict | list) -> dict | list:
        data = payload
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            for wrapper in ["data", "result", "output", "profile"]:
                if wrapper in data and isinstance(data[wrapper], dict):
                    return data[wrapper]
        return data