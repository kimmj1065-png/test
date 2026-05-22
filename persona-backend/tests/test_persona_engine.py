# -*- coding: utf-8 -*-
import json
from unittest.mock import MagicMock, patch
from app.services.persona_engine import generate_profile, merge_profiles


SAMPLE_MESSAGES = [
    {"date": "2024-01-15", "time": "오전 10:00", "sender": "홍길동", "text": "안녕하세요"},
    {"date": "2024-01-15", "time": "오전 10:01", "sender": "홍길동", "text": "오늘 시간 있어요?"},
    {"date": "2024-01-15", "time": "오전 10:02", "sender": "홍길동", "text": "같이 밥 먹어요"},
]

MOCK_CLAUDE_RESPONSE = """{
  "speech_style": 0.7,
  "emotion_frequency": 0.4,
  "response_pattern": "solution",
  "top_expressions": ["안녕하세요", "있어요", "먹어요"],
  "initiative_score": 0.8,
  "summary": "직접적이고 목표 지향적인 대화 패턴을 보입니다."
}"""

OLD_PROFILE = {
    "speech_style": 0.6,
    "emotion_frequency": 0.4,
    "response_pattern": "solution",
    "top_expressions": ["네", "알겠어요", "맞아요"],
    "initiative_score": 0.7,
    "summary": "기존 요약",
}

NEW_PROFILE = {
    "speech_style": 0.8,
    "emotion_frequency": 0.6,
    "response_pattern": "empathetic",
    "top_expressions": ["그렇군요", "정말요?", "네"],
    "initiative_score": 0.5,
    "summary": "신규 요약",
}

MOCK_MERGED = {
    "speech_style": 0.7,
    "emotion_frequency": 0.5,
    "response_pattern": "empathetic",
    "top_expressions": ["네", "그렇군요", "정말요?", "알겠어요", "맞아요"],
    "initiative_score": 0.6,
    "summary": "병합된 요약",
}


def test_generate_profile_returns_dict():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
    )
    result = generate_profile(SAMPLE_MESSAGES, "홍길동", claude_client=mock_client)
    assert isinstance(result, dict)
    assert "speech_style" in result
    assert "emotion_frequency" in result
    assert "response_pattern" in result
    assert "top_expressions" in result
    assert "initiative_score" in result
    assert "summary" in result


def test_generate_profile_values_in_range():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
    )
    result = generate_profile(SAMPLE_MESSAGES, "홍길동", claude_client=mock_client)
    assert 0.0 <= result["speech_style"] <= 1.0
    assert 0.0 <= result["emotion_frequency"] <= 1.0
    assert result["response_pattern"] in ("empathetic", "solution", "avoidant")
    assert isinstance(result["top_expressions"], list)
    assert 0.0 <= result["initiative_score"] <= 1.0


def test_generate_profile_calls_claude_once():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_CLAUDE_RESPONSE)]
    )
    generate_profile(SAMPLE_MESSAGES, "홍길동", claude_client=mock_client)
    mock_client.messages.create.assert_called_once()


def test_generate_profile_empty_messages():
    mock_client = MagicMock()
    result = generate_profile([], "홍길동", claude_client=mock_client)
    assert result == {}
    mock_client.messages.create.assert_not_called()


def test_merge_profiles_calls_claude():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(MOCK_MERGED, ensure_ascii=False))]
    )
    result = merge_profiles(OLD_PROFILE, NEW_PROFILE, 100, 50, claude_client=mock_client)
    mock_client.messages.create.assert_called_once()
    assert isinstance(result, dict)
    assert "speech_style" in result


def test_merge_profiles_empty_old():
    mock_client = MagicMock()
    result = merge_profiles({}, NEW_PROFILE, 0, 50, claude_client=mock_client)
    assert result == NEW_PROFILE
    mock_client.messages.create.assert_not_called()


def test_merge_profiles_empty_new():
    mock_client = MagicMock()
    result = merge_profiles(OLD_PROFILE, {}, 100, 0, claude_client=mock_client)
    assert result == OLD_PROFILE
    mock_client.messages.create.assert_not_called()
