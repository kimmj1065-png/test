# -*- coding: utf-8 -*-
import json
from typing import Dict, List, Optional

import anthropic

from app.config import settings

_PROFILE_PROMPT = """\
아래는 카카오톡 대화에서 {name}이(가) 보낸 메시지 {count}개입니다.

메시지 목록:
{messages}

위 메시지를 분석해 {name}의 심리 프로파일을 **반드시 아래 JSON 형식만** 출력하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "speech_style": <0.0(우회적)~1.0(직접적) 소수>,
  "emotion_frequency": <0.0~1.0 소수>,
  "response_pattern": "<empathetic|solution|avoidant>",
  "top_expressions": [<자주 쓰는 표현 최대 10개 문자열 배열>],
  "initiative_score": <0.0(수동적)~1.0(주도적) 소수>,
  "summary": "<한 문장 요약>"
}}"""

_MERGE_PROMPT = """\
기존 프로파일과 신규 프로파일을 가중치 병합하세요.
기존 데이터가 {old_weight}%, 신규 데이터가 {new_weight}% 비중입니다.

기존 프로파일:
{old_profile}

신규 프로파일:
{new_profile}

숫자 필드는 가중 평균, top_expressions는 신규 우선 합산 후 상위 10개, response_pattern과 summary는 신규 기준으로 **반드시 아래 JSON 형식만** 출력하세요.

{{
  "speech_style": <소수>,
  "emotion_frequency": <소수>,
  "response_pattern": "<empathetic|solution|avoidant>",
  "top_expressions": [<최대 10개>],
  "initiative_score": <소수>,
  "summary": "<한 문장 요약>"
}}"""


def _get_client(claude_client=None):
    if claude_client is not None:
        return claude_client
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _mock_profile(name: str, messages: List[Dict]) -> Dict:
    expressions = list({m["text"][:10] for m in messages[:5] if m.get("text")})[:5]
    return _validate_profile({
        "speech_style": 0.65,
        "emotion_frequency": 0.5,
        "response_pattern": "empathetic",
        "top_expressions": expressions or ["ㅋㅋ", "ㅇㅇ", "진짜?", "맞아", "그렇구나"],
        "initiative_score": 0.55,
        "summary": f"{name}은(는) 친근하고 공감을 잘 하는 스타일입니다. (Mock 데이터)",
    })


def generate_profile(
    messages: List[Dict[str, str]],
    name: str,
    claude_client=None,
) -> Dict:
    if not messages:
        return {}

    if settings.mock_ai and not claude_client:
        return _mock_profile(name, messages)

    client = _get_client(claude_client)
    messages_text = "\n".join(
        f"[{m['date']} {m['time']}] {m['text']}" for m in messages[:200]
    )
    prompt = _PROFILE_PROMPT.format(
        name=name,
        count=len(messages),
        messages=messages_text,
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        profile = json.loads(raw[start:end]) if start != -1 else {}

    return _validate_profile(profile)


def merge_profiles(
    old_profile: Dict,
    new_profile: Dict,
    old_message_count: int,
    new_message_count: int,
    claude_client=None,
) -> Dict:
    if not old_profile:
        return new_profile
    if not new_profile:
        return old_profile

    total = old_message_count + new_message_count
    old_weight = round(old_message_count / total * 100)
    new_weight = 100 - old_weight

    if settings.mock_ai and not claude_client:
        ow, nw = old_weight / 100, new_weight / 100
        expressions = list(dict.fromkeys(
            new_profile.get("top_expressions", []) + old_profile.get("top_expressions", [])
        ))[:10]
        return _validate_profile({
            "speech_style": old_profile.get("speech_style", 0.5) * ow + new_profile.get("speech_style", 0.5) * nw,
            "emotion_frequency": old_profile.get("emotion_frequency", 0.5) * ow + new_profile.get("emotion_frequency", 0.5) * nw,
            "response_pattern": new_profile.get("response_pattern", "empathetic"),
            "top_expressions": expressions,
            "initiative_score": old_profile.get("initiative_score", 0.5) * ow + new_profile.get("initiative_score", 0.5) * nw,
            "summary": new_profile.get("summary", ""),
        })

    client = _get_client(claude_client)
    prompt = _MERGE_PROMPT.format(
        old_weight=old_weight,
        new_weight=new_weight,
        old_profile=json.dumps(old_profile, ensure_ascii=False),
        new_profile=json.dumps(new_profile, ensure_ascii=False),
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    try:
        merged = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        merged = json.loads(raw[start:end]) if start != -1 else new_profile

    return _validate_profile(merged)


def _validate_profile(profile: Dict) -> Dict:
    profile["speech_style"] = max(0.0, min(1.0, float(profile.get("speech_style", 0.5))))
    profile["emotion_frequency"] = max(0.0, min(1.0, float(profile.get("emotion_frequency", 0.5))))
    profile["initiative_score"] = max(0.0, min(1.0, float(profile.get("initiative_score", 0.5))))
    if profile.get("response_pattern") not in ("empathetic", "solution", "avoidant"):
        profile["response_pattern"] = "empathetic"
    if not isinstance(profile.get("top_expressions"), list):
        profile["top_expressions"] = []
    profile["top_expressions"] = profile["top_expressions"][:10]
    if not isinstance(profile.get("summary"), str):
        profile["summary"] = ""
    return profile
