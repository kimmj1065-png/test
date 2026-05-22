# -*- coding: utf-8 -*-
import json
from typing import Dict, List, Optional

import anthropic

from app.config import settings

_SYSTEM_PROMPT = """\
당신은 {name}입니다. 아래는 {name}의 심리 프로파일입니다:
- 말투 스타일: {speech_style_desc} ({speech_style:.0%})
- 감정 표현 빈도: {emotion_frequency:.0%}
- 주요 반응 패턴: {response_pattern_desc}
- 자주 쓰는 표현: {top_expressions}
- 대화 주도성: {initiative_score:.0%}
- 요약: {summary}

시나리오: {situation}
목표: {goal}
대화 톤: {tone}

반드시 {name}의 말투와 성격을 유지하며 자연스러운 한국어로 대화하세요.
상대방의 메시지에 자연스럽게 반응하세요. 한 번에 1-3문장만 답하세요."""

_FEEDBACK_PROMPT = """\
아래는 대화 기록입니다 (user = 앱 사용자, assistant = 페르소나):

{turns_text}

위 대화에서 user의 발화 패턴을 분석해 **반드시 아래 JSON 형식만** 출력하세요:

{{
  "avoidant_count": <회피형 반응 횟수 정수>,
  "empathy_count": <공감 시도 횟수 정수>,
  "direct_expression_count": <감정 직접 표현 횟수 정수>,
  "insight": "<user의 대화 패턴에 대한 한 문장 인사이트>",
  "replay_recommendation": "<특정 턴에서 다르게 말해보라는 추천, 턴 번호 포함>"
}}"""

_RESPONSE_PATTERN_DESC = {
    "empathetic": "공감형",
    "solution": "해결형",
    "avoidant": "회피형",
}


_MOCK_REPLIES = [
    "그렇구나, 나도 그런 적 있어.",
    "ㅋㅋ 진짜? 어떻게 된 거야?",
    "음... 좀 더 얘기해줄 수 있어?",
    "맞아, 나도 그 생각 해봤는데.",
    "아 그래? 근데 그게 쉽지 않잖아.",
    "ㅇㅇ 충분히 이해돼.",
    "솔직히 말해줘서 고마워.",
]

_mock_reply_index = 0


def _get_client(claude_client=None):
    if claude_client is not None:
        return claude_client
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _build_system_prompt(name: str, profile: Dict, config: Dict) -> str:
    speech_style = profile.get("speech_style", 0.5)
    speech_style_desc = "직접적" if speech_style >= 0.6 else "우회적"
    response_pattern = profile.get("response_pattern", "empathetic")
    return _SYSTEM_PROMPT.format(
        name=name,
        speech_style=speech_style,
        speech_style_desc=speech_style_desc,
        emotion_frequency=profile.get("emotion_frequency", 0.5),
        response_pattern_desc=_RESPONSE_PATTERN_DESC.get(response_pattern, response_pattern),
        top_expressions=", ".join(profile.get("top_expressions", [])[:5]),
        initiative_score=profile.get("initiative_score", 0.5),
        summary=profile.get("summary", ""),
        situation=config.get("situation", "일상 대화"),
        goal=config.get("goal", "자연스러운 대화"),
        tone=config.get("tone", "자연스럽게"),
    )


def generate_opening(
    persona_name: str,
    profile: Dict,
    scenario_config: Dict,
    claude_client=None,
) -> str:
    if settings.mock_ai and not claude_client:
        scenario_type = scenario_config.get("scenario_type", "daily")
        openings = {
            "apology": f"있잖아... 저번에 내가 한 말, 좀 생각해봤는데. 미안했어. (Mock - {persona_name})",
            "conflict": f"솔직히 나는 좀 다르게 생각하거든. 얘기해도 될까? (Mock - {persona_name})",
            "confession": f"음... 할 말이 있는데, 들어줄 수 있어? (Mock - {persona_name})",
            "daily": f"오늘 어떻게 지냈어? ㅋㅋ (Mock - {persona_name})",
            "comfort": f"요즘 많이 힘들어 보이더라. 괜찮아? (Mock - {persona_name})",
            "request": f"부탁 하나 해도 돼? 좀 도움이 필요해서. (Mock - {persona_name})",
        }
        return openings.get(scenario_type, f"안녕! 오늘 대화해볼까? (Mock - {persona_name})")

    client = _get_client(claude_client)
    system = _build_system_prompt(persona_name, profile, scenario_config)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": "[대화를 시작해주세요]"}],
    )
    return response.content[0].text.strip()


def generate_reply(
    persona_name: str,
    profile: Dict,
    scenario_config: Dict,
    turns: List[Dict],
    claude_client=None,
) -> str:
    global _mock_reply_index
    if settings.mock_ai and not claude_client:
        reply = _MOCK_REPLIES[_mock_reply_index % len(_MOCK_REPLIES)]
        _mock_reply_index += 1
        return f"{reply} (Mock - {persona_name})"

    client = _get_client(claude_client)
    system = _build_system_prompt(persona_name, profile, scenario_config)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=system,
        messages=turns,
    )
    return response.content[0].text.strip()


def generate_feedback(
    turns: List[Dict],
    claude_client=None,
) -> Dict:
    if not turns:
        return {}

    user_turns = [t for t in turns if t["role"] == "user"]
    if not user_turns:
        return {}

    if settings.mock_ai and not claude_client:
        return {
            "score": 72,
            "avoidant_count": 1,
            "empathy_count": len(user_turns),
            "direct_expression_count": max(1, len(user_turns) // 2),
            "strengths": ["감정을 솔직하게 표현했습니다.", "상대방 말을 끝까지 들었습니다."],
            "improvements": ["좀 더 구체적인 공감 표현을 사용해보세요.", "회피하지 말고 직접 의견을 말해보세요."],
            "insight": "전반적으로 공감 능력이 좋으나 자기 표현을 더 강화하면 좋겠습니다. (Mock 데이터)",
            "replay_recommendation": f"2번째 대화에서 더 직접적으로 감정을 표현해보세요. (Mock 데이터)",
            "summary": "이번 대화에서 공감과 경청을 잘 하셨습니다. 자기 표현도 늘려보세요. (Mock 데이터)",
        }

    client = _get_client(claude_client)
    turns_text = "\n".join(f"[{t['role']}] {t['content']}" for t in turns)
    prompt = _FEEDBACK_PROMPT.format(turns_text=turns_text)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    try:
        feedback = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        feedback = json.loads(raw[start:end]) if start != -1 else {}

    return feedback
