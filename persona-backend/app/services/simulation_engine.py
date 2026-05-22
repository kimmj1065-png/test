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
