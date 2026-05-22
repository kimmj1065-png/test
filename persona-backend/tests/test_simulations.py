# -*- coding: utf-8 -*-
import io
import pytest
from unittest.mock import patch

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
        assert len(data["turns"]) == 3
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

        resp = client.post(f"/simulations/{sim_id}/savepoint", headers=auth_headers)
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

        sp_resp = client.post(f"/simulations/{sim_id}/savepoint", headers=auth_headers)
        sp_id = sp_resp.json()["savepoints"][0]["id"]

        client.post(f"/simulations/{sim_id}/turn", json={"message": "응?"}, headers=auth_headers)

        resp = client.post(f"/simulations/{sim_id}/restore/{sp_id}", headers=auth_headers)
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
        assert resp.json()["feedback"] == MOCK_FEEDBACK


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
