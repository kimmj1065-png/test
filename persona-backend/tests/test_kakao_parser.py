from app.services.kakao_parser import parse_kakao_export, extract_speakers, filter_by_sender

NEW_FORMAT_SAMPLE = """카카오톡 대화
저장한 날짜 : 2024-01-15 10:30:00

------------------ 2024년 1월 15일 월요일 ------------------
오전 10:00, 홍길동 : 안녕하세요
오전 10:01, 김미주 : 네 안녕하세요
오전 10:02, 홍길동 : 오늘 시간 있어요?
오후 2:00, 김미주 : 네 있어요"""

OLD_FORMAT_SAMPLE = """------------------ 2024년 2월 1일 목요일 ------------------
[홍길동] [오전 9:00] 좋은 아침이에요
[김미주] [오전 9:01] 안녕하세요!"""


def test_parse_new_format():
    messages = parse_kakao_export(NEW_FORMAT_SAMPLE)
    assert len(messages) == 4
    assert messages[0]["sender"] == "홍길동"
    assert messages[0]["text"] == "안녕하세요"
    assert messages[0]["date"] == "2024-01-15"


def test_parse_old_format():
    messages = parse_kakao_export(OLD_FORMAT_SAMPLE)
    assert len(messages) == 2
    assert messages[0]["sender"] == "홍길동"
    assert messages[1]["sender"] == "김미주"


def test_extract_speakers():
    messages = parse_kakao_export(NEW_FORMAT_SAMPLE)
    speakers = extract_speakers(messages)
    assert "홍길동" in speakers
    assert "김미주" in speakers
    assert len(speakers) == 2


def test_filter_by_sender():
    messages = parse_kakao_export(NEW_FORMAT_SAMPLE)
    filtered = filter_by_sender(messages, "홍길동")
    assert len(filtered) == 2
    assert all(m["sender"] == "홍길동" for m in filtered)


def test_empty_content():
    messages = parse_kakao_export("")
    assert messages == []
