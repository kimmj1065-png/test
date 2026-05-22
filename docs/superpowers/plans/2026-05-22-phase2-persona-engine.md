# Phase 2: 페르소나 엔진 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude API를 연동해 카카오톡 대화 메시지를 분석하고 심리 프로파일(profile_json)을 생성하며, 신규 대화 업로드 시 기존 프로파일과 가중치 병합 업데이트를 지원한다.

**Architecture:** `app/services/persona_engine.py`가 Claude API 호출을 담당하고, 업로드 라우터(`/personas/upload`)가 파일 파싱 후 엔진을 호출해 profile_json을 채운다. 업데이트 엔드포인트(`POST /personas/{id}/update`)는 신규 파일을 받아 기존 프로파일과 가중치 병합한다. Claude API 호출은 테스트에서 mock 처리한다.

**Tech Stack:** Python FastAPI, Anthropic SDK (`anthropic==0.34.0`), pytest + unittest.mock

---

## 파일 구조

```
persona-backend/
├── app/
│   ├── services/
│   │   ├── kakao_parser.py          # 기존 (수정 없음)
│   │   └── persona_engine.py        # NEW: Claude API 호출, 프로파일 생성/병합
│   ├── routers/
│   │   └── personas.py              # MODIFY: upload 시 엔진 호출, update 엔드포인트 추가
│   └── schemas/
│       └── persona.py               # MODIFY: PersonaResponse에 profile_json 상세 스키마 추가
└── tests/
    ├── test_persona_engine.py        # NEW: 엔진 단위 테스트 (Claude mock)
    └── test_personas.py              # MODIFY: upload 시 profile_json 검증, update 테스트 추가
```

---

## profile_json 스키마 (설계 문서 기반)

```json
{
  "speech_style": 0.8,
  "emotion_frequency": 0.5,
  "response_pattern": "empathetic",
  "top_expressions": ["네", "그렇군요", "정말요?", "알겠어요", "맞아요"],
  "initiative_score": 0.6,
  "summary": "직접적이고 감정 표현이 중간 수준이며 공감형 반응 패턴을 보입니다."
}
```

필드 설명:
- `speech_style`: 0.0(우회적) ~ 1.0(직접적)
- `emotion_frequency`: 0.0 ~ 1.0
- `response_pattern`: "empathetic" | "solution" | "avoidant"
- `top_expressions`: 자주 쓰는 표현 최대 10개
- `initiative_score`: 0.0(수동적) ~ 1.0(주도적)
- `summary`: 한 문장 요약

---

## Task 1: persona_engine.py — 프로파일 생성

**Files:**
- Create: `persona-backend/app/services/persona_engine.py`
- Create: `persona-backend/tests/test_persona_engine.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# persona-backend/tests/test_persona_engine.py
# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch
from app.services.persona_engine import generate_profile


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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd persona-backend
pytest tests/test_persona_engine.py -v
```

Expected: `ImportError` — `persona_engine` 모듈 없음

- [ ] **Step 3: persona_engine.py 구현**

```python
# persona-backend/app/services/persona_engine.py
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


def generate_profile(
    messages: List[Dict[str, str]],
    name: str,
    claude_client=None,
) -> Dict:
    if not messages:
        return {}

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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_persona_engine.py -v
```

Expected: 4개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add app/services/persona_engine.py tests/test_persona_engine.py
git commit -m "feat: 페르소나 프로파일 생성 엔진 (Claude API)"
```

---

## Task 2: upload 엔드포인트에 프로파일 생성 연동

**Files:**
- Modify: `persona-backend/app/routers/personas.py`
- Modify: `persona-backend/tests/test_personas.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_personas.py` 파일 끝에 아래 테스트를 추가한다:

```python
from unittest.mock import patch, MagicMock

MOCK_PROFILE = {
    "speech_style": 0.7,
    "emotion_frequency": 0.5,
    "response_pattern": "empathetic",
    "top_expressions": ["네", "안녕하세요"],
    "initiative_score": 0.6,
    "summary": "공감형 대화 패턴입니다.",
}


def test_upload_generates_profile(client, auth_headers):
    with patch("app.routers.personas.generate_profile", return_value=MOCK_PROFILE) as mock_gen:
        file_content = KAKAO_SAMPLE.encode("utf-8")
        resp = client.post(
            "/personas/upload",
            files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
            data={"my_name": "김미주"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        for persona in data:
            assert persona["profile_json"] == MOCK_PROFILE
        assert mock_gen.call_count == 2  # self + acquaintance 각 1회
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_personas.py::test_upload_generates_profile -v
```

Expected: FAILED — profile_json이 `{}` 상태

- [ ] **Step 3: personas.py upload 엔드포인트 수정**

`app/routers/personas.py` 파일 상단 임포트에 추가:

```python
from app.services.persona_engine import generate_profile
```

`upload_kakao_file` 함수 내 self_persona 생성 부분을 아래로 교체:

```python
    my_messages = filter_by_sender(messages, my_name)
    self_profile = generate_profile(my_messages, my_name)
    self_persona = Persona(
        user_id=current_user.id,
        name=my_name,
        type="self",
        message_count=len(my_messages),
        profile_json=self_profile,
    )
    db.add(self_persona)
    created_personas.append(self_persona)

    for speaker in speakers:
        if speaker == my_name:
            continue
        their_messages = filter_by_sender(messages, speaker)
        acquaintance_profile = generate_profile(their_messages, speaker)
        acquaintance_persona = Persona(
            user_id=current_user.id,
            name=speaker,
            type="acquaintance",
            message_count=len(their_messages),
            profile_json=acquaintance_profile,
        )
        db.add(acquaintance_persona)
        created_personas.append(acquaintance_persona)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_personas.py -v
```

Expected: 6개 모두 PASSED

- [ ] **Step 5: 커밋**

```bash
git add app/routers/personas.py tests/test_personas.py
git commit -m "feat: 카카오톡 업로드 시 Claude API 프로파일 생성 연동"
```

---

## Task 3: 페르소나 업데이트 엔드포인트 (가중치 병합)

**Files:**
- Modify: `persona-backend/app/routers/personas.py`
- Modify: `persona-backend/tests/test_personas.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_personas.py` 파일 끝에 아래 테스트를 추가한다:

```python
def test_update_persona_merges_profile(client, auth_headers):
    MERGE_RESULT = {
        "speech_style": 0.75,
        "emotion_frequency": 0.55,
        "response_pattern": "empathetic",
        "top_expressions": ["네", "안녕하세요", "그렇군요"],
        "initiative_score": 0.65,
        "summary": "업데이트된 공감형 패턴입니다.",
    }
    with patch("app.routers.personas.generate_profile", return_value=MOCK_PROFILE), \
         patch("app.routers.personas.merge_profiles", return_value=MERGE_RESULT) as mock_merge:
        # 먼저 업로드
        file_content = KAKAO_SAMPLE.encode("utf-8")
        upload_resp = client.post(
            "/personas/upload",
            files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
            data={"my_name": "김미주"},
            headers=auth_headers,
        )
        persona_id = upload_resp.json()[0]["id"]

        # 추가 업로드로 업데이트
        resp = client.post(
            f"/personas/{persona_id}/update",
            files={"file": ("kakao2.txt", io.BytesIO(file_content), "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["profile_json"] == MERGE_RESULT
        mock_merge.assert_called_once()


def test_update_persona_not_found(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    resp = client.post(
        "/personas/nonexistent-id/update",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_personas.py::test_update_persona_merges_profile tests/test_personas.py::test_update_persona_not_found -v
```

Expected: FAILED — 404 라우트 없음

- [ ] **Step 3: personas.py에 update 엔드포인트 추가**

`app/routers/personas.py` 임포트에 `merge_profiles` 추가:

```python
from app.services.persona_engine import generate_profile, merge_profiles
```

`delete_persona` 함수 아래에 추가:

```python
@router.post("/{persona_id}/update", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")

    content = (await file.read()).decode("utf-8")
    messages = parse_kakao_export(content)
    new_messages = filter_by_sender(messages, persona.name)

    if not new_messages:
        raise HTTPException(status_code=400, detail="해당 발화자의 메시지가 없습니다.")

    new_profile = generate_profile(new_messages, persona.name)
    merged_profile = merge_profiles(
        old_profile=persona.profile_json,
        new_profile=new_profile,
        old_message_count=persona.message_count,
        new_message_count=len(new_messages),
    )

    persona.profile_json = merged_profile
    persona.message_count = persona.message_count + len(new_messages)
    db.commit()
    db.refresh(persona)
    return persona
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 전체 PASSED

- [ ] **Step 5: 커밋**

```bash
git add app/routers/personas.py tests/test_personas.py
git commit -m "feat: 페르소나 업데이트 API (신규 대화 가중치 병합)"
```

---

## Task 4: merge_profiles 단위 테스트

**Files:**
- Modify: `persona-backend/tests/test_persona_engine.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_persona_engine.py` 파일 끝에 추가:

```python
from app.services.persona_engine import merge_profiles

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
```

`test_persona_engine.py` 상단에 `import json` 추가가 빠진 경우를 위해 파일 첫 줄에:

```python
import json
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_persona_engine.py -v
```

Expected: 새로 추가한 3개 FAILED

- [ ] **Step 3: 테스트 통과 확인 (구현은 Task 1에서 완료)**

```bash
pytest tests/test_persona_engine.py -v
```

Expected: 7개 모두 PASSED

- [ ] **Step 4: 전체 테스트 최종 확인**

```bash
pytest tests/ -v
```

Expected: 전체 PASSED

- [ ] **Step 5: 커밋**

```bash
git add tests/test_persona_engine.py
git commit -m "test: merge_profiles 단위 테스트 추가"
```

---

## Task 5: Phase 2 최종 확인 및 완료 커밋

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd persona-backend
pytest tests/ -v
```

Expected: 전체 PASSED

- [ ] **Step 2: 앱 임포트 검증**

```bash
python -c "from app.main import app; from app.services.persona_engine import generate_profile, merge_profiles; print('Phase 2 로드 성공')"
```

Expected: `Phase 2 로드 성공`

- [ ] **Step 3: Phase 2 완료 커밋**

```bash
git add .
git commit -m "feat: Phase 2 페르소나 엔진 완료

- Claude API 기반 심리 프로파일 생성 (speech_style, emotion_frequency, response_pattern, top_expressions, initiative_score, summary)
- 카카오톡 업로드 시 자동 프로파일 생성
- 페르소나 업데이트 API (신규 대화 가중치 병합)"
```
