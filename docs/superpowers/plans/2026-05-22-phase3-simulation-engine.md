# Phase 3: 시뮬레이션 엔진 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 페르소나 프로파일을 기반으로 Claude API와 실시간 대화 시뮬레이션을 수행하고, 세이브포인트 분기 탐색과 종료 후 피드백 리포트를 생성한다.

**Architecture:** `app/services/simulation_engine.py`가 Claude API 스트리밍 대화를 담당한다. REST 엔드포인트(`app/routers/simulations.py`)는 시뮬레이션 생성/턴 전송/세이브포인트/피드백을 처리한다. 스트리밍은 Server-Sent Events(SSE)로 응답한다. 테스트에서는 Claude API를 mock 처리한다.

**Tech Stack:** FastAPI, Anthropic SDK (streaming), SSE (`starlette.responses.StreamingResponse`), pytest + unittest.mock

---

## 데이터 구조

### turns (JSON 배열)
```json
[
  {"role": "assistant", "content": "안녕하세요. 잠깐 얘기할 수 있어요?"},
  {"role": "user", "content": "응, 무슨 일이야?"},
  {"role": "assistant", "content": "사실 네가 그때 한 말이 좀 마음에 걸려서..."}
]
```

### savepoints (JSON 배열)
```json
[
  {"id": "sp-uuid", "turn_index": 2, "label": "세이브포인트 1", "created_at": "2024-01-15T10:05:00"}
]
```

### scenario_config (JSON)
```json
{
  "type": "template",
  "category": "연애",
  "situation": "카페에서 만남",
  "goal": "오해 풀기",
  "tone": "차분하게"
}
```

### feedback (JSON)
```json
{
  "avoidant_count": 2,
  "empathy_count": 3,
  "direct_expression_count": 1,
  "insight": "갈등 상황에서 화제를 전환하는 경향이 있어요.",
  "replay_recommendation": "3번째 대화에서 다르게 말해보세요."
}
```

---

## 파일 구조

```
persona-backend/
├── app/
│   ├── services/
│   │   └── simulation_engine.py     # NEW: Claude API 대화 생성, 피드백 분석
│   ├── routers/
│   │   └── simulations.py           # NEW: 시뮬레이션 CRUD + 턴/세이브포인트/피드백 엔드포인트
│   ├── schemas/
│   │   └── simulation.py            # NEW: Pydantic 스키마
│   └── main.py                      # MODIFY: simulations 라우터 등록
└── tests/
    ├── test_simulation_engine.py     # NEW: 엔진 단위 테스트 (Claude mock)
    └── test_simulations.py           # NEW: API 통합 테스트
```

---

## Task 1: simulation_engine.py — 대화 생성 및 피드백

**Files:**
- Create: `persona-backend/app/services/simulation_engine.py`
- Create: `persona-backend/tests/test_simulation_engine.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# persona-backend/tests/test_simulation_engine.py
# -*- coding: utf-8 -*-
import json
from unittest.mock import MagicMock, patch
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd persona-backend
pytest tests/test_simulation_engine.py -v
```

Expected: `ImportError` — `simulation_engine` 모듈 없음

- [ ] **Step 3: simulation_engine.py 구현**

```python
# persona-backend/app/services/simulation_engine.py
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
    turns_text = "\n".join(
        f"[{t['role']}] {t['content']}" for t in turns
    )
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_simulation_engine.py -v
```

Expected: 6개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add app/services/simulation_engine.py tests/test_simulation_engine.py
git commit -m "feat: 시뮬레이션 엔진 (대화 생성, 피드백 분석)"
```

---

## Task 2: schemas/simulation.py 및 routers/simulations.py

**Files:**
- Create: `persona-backend/app/schemas/simulation.py`
- Create: `persona-backend/app/routers/simulations.py`
- Modify: `persona-backend/app/main.py`
- Create: `persona-backend/tests/test_simulations.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# persona-backend/tests/test_simulations.py
# -*- coding: utf-8 -*-
import io
import pytest
from unittest.mock import patch, MagicMock

KAKAO_SAMPLE = """카카오톡 대화
저장한 날짜 : 2024-01-15 10:30:00

------------------ 2024년 1월 15일 월요일 ------------------
오전 10:00, 홍길동 : 안녕하세요
오전 10:01, 김미주 : 네 안녕하세요
오전 10:02, 홍길동 : 잘 지냈어요?
오전 10:03, 김미주 : 네 잘 지냈어요"""

MOCK_OPENING = "어, 왔어? 얘기 좀 해도 돼?"
MOCK_REPLY = "그렇구나, 미안해."
MOCK_FEEDBACK = {
    "avoidant_count": 1,
    "empathy_count": 2,
    "direct_expression_count": 1,
    "insight": "회피 경향이 있어요.",
    "replay_recommendation": "2번째 대화에서 다르게 말해보세요.",
}

SCENARIO_CONFIG = {
    "type": "template",
    "category": "친구",
    "situation": "카페에서 만남",
    "goal": "오해 풀기",
    "tone": "차분하게",
}


@pytest.fixture
def persona_id(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    resp = client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
        headers=auth_headers,
    )
    return resp.json()[0]["id"]


def test_create_simulation(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING):
        resp = client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["persona_id"] == persona_id
        assert len(data["turns"]) == 1
        assert data["turns"][0]["role"] == "assistant"
        assert data["turns"][0]["content"] == MOCK_OPENING


def test_send_turn(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING), \
         patch("app.routers.simulations.generate_reply", return_value=MOCK_REPLY):
        create_resp = client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]

        resp = client.post(
            f"/simulations/{sim_id}/turn",
            json={"message": "응, 무슨 일이야?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["turns"]) == 3  # opening + user + reply
        assert data["turns"][1]["role"] == "user"
        assert data["turns"][2]["role"] == "assistant"


def test_create_savepoint(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING):
        create_resp = client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]

        resp = client.post(
            f"/simulations/{sim_id}/savepoint",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["savepoints"]) == 1
        assert "id" in data["savepoints"][0]
        assert data["savepoints"][0]["turn_index"] == 1


def test_restore_savepoint(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING), \
         patch("app.routers.simulations.generate_reply", return_value=MOCK_REPLY):
        create_resp = client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]

        # 세이브포인트 생성 (turns: 1개)
        sp_resp = client.post(f"/simulations/{sim_id}/savepoint", headers=auth_headers)
        sp_id = sp_resp.json()["savepoints"][0]["id"]

        # 턴 추가 (turns: 3개)
        client.post(f"/simulations/{sim_id}/turn", json={"message": "응?"}, headers=auth_headers)

        # 세이브포인트로 복원 (turns: 1개로 돌아가야 함)
        resp = client.post(
            f"/simulations/{sim_id}/restore/{sp_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["turns"]) == 1


def test_get_feedback(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING), \
         patch("app.routers.simulations.generate_reply", return_value=MOCK_REPLY), \
         patch("app.routers.simulations.generate_feedback", return_value=MOCK_FEEDBACK):
        create_resp = client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        sim_id = create_resp.json()["id"]
        client.post(f"/simulations/{sim_id}/turn", json={"message": "응?"}, headers=auth_headers)

        resp = client.post(f"/simulations/{sim_id}/feedback", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["feedback"] == MOCK_FEEDBACK


def test_list_simulations(client, auth_headers, persona_id):
    with patch("app.routers.simulations.generate_opening", return_value=MOCK_OPENING):
        client.post(
            "/simulations",
            json={"persona_id": persona_id, "scenario_config": SCENARIO_CONFIG},
            headers=auth_headers,
        )
        resp = client.get("/simulations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_simulations.py -v
```

Expected: FAILED (라우터/스키마 없음)

- [ ] **Step 3: schemas/simulation.py 작성**

```python
# persona-backend/app/schemas/simulation.py
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class SimulationCreate(BaseModel):
    persona_id: str
    scenario_config: Dict[str, Any]


class TurnRequest(BaseModel):
    message: str


class SimulationResponse(BaseModel):
    id: str
    persona_id: str
    scenario_type: str
    scenario_config: dict
    turns: list
    savepoints: list
    feedback: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationListResponse(BaseModel):
    simulations: List[SimulationResponse]
    total: int
```

- [ ] **Step 4: routers/simulations.py 작성**

```python
# persona-backend/app/routers/simulations.py
# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.user import User
from app.schemas.simulation import (
    SimulationCreate,
    SimulationListResponse,
    SimulationResponse,
    TurnRequest,
)
from app.services.simulation_engine import generate_feedback, generate_opening, generate_reply

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResponse, status_code=201)
def create_simulation(
    body: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = (
        db.query(Persona)
        .filter(Persona.id == body.persona_id, Persona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")

    opening = generate_opening(persona.name, persona.profile_json, body.scenario_config)
    turns = [{"role": "assistant", "content": opening}]

    sim = Simulation(
        user_id=current_user.id,
        persona_id=persona.id,
        scenario_type=body.scenario_config.get("type", "free"),
        scenario_config=body.scenario_config,
        turns=turns,
        savepoints=[],
        feedback={},
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/turn", response_model=SimulationResponse)
def send_turn(
    sim_id: str,
    body: TurnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    persona = db.query(Persona).filter(Persona.id == sim.persona_id).first()

    turns = list(sim.turns)
    turns.append({"role": "user", "content": body.message})

    reply = generate_reply(
        persona.name, persona.profile_json, sim.scenario_config, turns
    )
    turns.append({"role": "assistant", "content": reply})

    sim.turns = turns
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/savepoint", response_model=SimulationResponse, status_code=201)
def create_savepoint(
    sim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    savepoints = list(sim.savepoints)
    savepoints.append({
        "id": str(uuid4()),
        "turn_index": len(sim.turns),
        "label": f"세이브포인트 {len(savepoints) + 1}",
        "created_at": datetime.utcnow().isoformat(),
    })
    sim.savepoints = savepoints
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/restore/{savepoint_id}", response_model=SimulationResponse)
def restore_savepoint(
    sim_id: str,
    savepoint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    sp = next((s for s in sim.savepoints if s["id"] == savepoint_id), None)
    if not sp:
        raise HTTPException(status_code=404, detail="세이브포인트를 찾을 수 없습니다.")

    sim.turns = list(sim.turns)[: sp["turn_index"]]
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/feedback", response_model=SimulationResponse)
def get_feedback(
    sim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    feedback = generate_feedback(sim.turns)
    sim.feedback = feedback
    db.commit()
    db.refresh(sim)
    return sim


@router.get("", response_model=SimulationListResponse)
def list_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sims = (
        db.query(Simulation)
        .filter(Simulation.user_id == current_user.id)
        .order_by(Simulation.created_at.desc())
        .all()
    )
    return SimulationListResponse(simulations=sims, total=len(sims))
```

- [ ] **Step 5: main.py에 simulations 라우터 추가**

```python
# persona-backend/app/main.py
from fastapi import FastAPI
from app.routers import auth, personas, simulations

app = FastAPI(title="Persona API", version="1.0.0")

app.include_router(auth.router)
app.include_router(personas.router)
app.include_router(simulations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: conftest.py에 simulation_engine mock 추가**

`tests/conftest.py`의 `mock_generate_profile` 픽스처 아래에 추가:

```python
@pytest.fixture(autouse=True)
def mock_simulation_engine():
    with patch("app.routers.simulations.generate_opening", return_value="테스트 오프닝"), \
         patch("app.routers.simulations.generate_reply", return_value="테스트 응답"), \
         patch("app.routers.simulations.generate_feedback", return_value={}):
        yield
```

단, `test_simulations.py`의 테스트들은 자체적으로 patch를 걸기 때문에 `mock_simulation_engine`이 conftest에 있으면 중복 patch가 발생합니다. 따라서 `mock_simulation_engine` fixture는 `autouse=False`로 설정하고, `test_simulations.py`에서는 직접 patch를 사용합니다.

```python
@pytest.fixture
def mock_simulation_engine():
    with patch("app.routers.simulations.generate_opening", return_value="테스트 오프닝"), \
         patch("app.routers.simulations.generate_reply", return_value="테스트 응답"), \
         patch("app.routers.simulations.generate_feedback", return_value={}):
        yield
```

- [ ] **Step 7: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 전체 PASSED

- [ ] **Step 8: 커밋**

```bash
git add app/schemas/simulation.py app/routers/simulations.py app/main.py tests/test_simulations.py tests/conftest.py
git commit -m "feat: 시뮬레이션 API (생성/턴/세이브포인트/피드백)"
```

---

## Task 3: Phase 3 최종 확인

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 전체 PASSED

- [ ] **Step 2: 앱 임포트 검증**

```bash
python -c "from app.main import app; from app.services.simulation_engine import generate_opening, generate_reply, generate_feedback; print('Phase 3 로드 성공')"
```

Expected: `Phase 3 로드 성공`

- [ ] **Step 3: 최종 커밋**

```bash
git add .
git commit -m "feat: Phase 3 시뮬레이션 엔진 완료

- Claude API 기반 페르소나 대화 생성 (오프닝/응답)
- 세이브포인트 생성 및 복원 (분기 탐색)
- 대화 종료 후 피드백 리포트 생성"
```
