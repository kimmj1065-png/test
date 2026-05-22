# -*- coding: utf-8 -*-
import json
from unittest.mock import MagicMock
from app.services.simulation_engine import generate_opening, generate_reply, generate_feedback

PERSONA_PROFILE = {
    "speech_style": 0.7,
    "emotion_frequency": 0.5,
    "response_pattern": "empathetic",
    "top_expressions": ["그렇구나", "정말?", "알았어"],
    "initiative_score": 0.6,
    "summary": "공감형이고 직접적인 대화 패턴",
}

SCENARIO_CONFIG = {
    "type": "template",
    "category": "친구",
    "situation": "카페에서 만남",
    "goal": "오해 풀기",
    "tone": "차분하게",
}

TURNS = [
    {"role": "assistant", "content": "어... 그날 일 때문에 얘기하고 싶었어."},
    {"role": "user", "content": "무슨 일? 갑자기?"},
    {"role": "assistant", "content": "네가 그때 한 말이 마음에 걸려서."},
]

MOCK_OPENING = "어, 왔어? 잠깐 얘기 좀 할 수 있어?"
MOCK_REPLY = "그렇구나... 나는 그냥 솔직하게 말한 건데."
MOCK_FEEDBACK = json.dumps({
    "avoidant_count": 1,
    "empathy_count": 2,
    "direct_expression_count": 1,
    "insight": "갈등 상황에서 다소 회피하는 경향이 있어요.",
    "replay_recommendation": "2번째 대화에서 감정을 더 직접적으로 표현해 보세요.",
}, ensure_ascii=False)


def test_generate_opening_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_OPENING)]
    )
    result = generate_opening("홍길동", PERSONA_PROFILE, SCENARIO_CONFIG, claude_client=mock_client)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_opening_calls_claude_once():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_OPENING)]
    )
    generate_opening("홍길동", PERSONA_PROFILE, SCENARIO_CONFIG, claude_client=mock_client)
    mock_client.messages.create.assert_called_once()


def test_generate_reply_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_REPLY)]
    )
    result = generate_reply("홍길동", PERSONA_PROFILE, SCENARIO_CONFIG, TURNS, claude_client=mock_client)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_reply_calls_claude_once():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_REPLY)]
    )
    generate_reply("홍길동", PERSONA_PROFILE, SCENARIO_CONFIG, TURNS, claude_client=mock_client)
    mock_client.messages.create.assert_called_once()


def test_generate_feedback_returns_dict():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_FEEDBACK)]
    )
    result = generate_feedback(TURNS, claude_client=mock_client)
    assert isinstance(result, dict)
    assert "avoidant_count" in result
    assert "empathy_count" in result
    assert "direct_expression_count" in result
    assert "insight" in result
    assert "replay_recommendation" in result


def test_generate_feedback_empty_turns():
    mock_client = MagicMock()
    result = generate_feedback([], claude_client=mock_client)
    assert result == {}
    mock_client.messages.create.assert_not_called()
