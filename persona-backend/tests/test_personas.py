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


def test_upload_kakao_file(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    resp = client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    types = {p["type"] for p in data}
    assert "self" in types
    assert "acquaintance" in types


def test_list_personas(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
        headers=auth_headers,
    )
    resp = client.get("/personas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_get_persona_detail(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    upload_resp = client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
        headers=auth_headers,
    )
    persona_id = upload_resp.json()[0]["id"]
    resp = client.get(f"/personas/{persona_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == persona_id


def test_delete_persona(client, auth_headers):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    upload_resp = client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
        headers=auth_headers,
    )
    persona_id = upload_resp.json()[0]["id"]
    resp = client.delete(f"/personas/{persona_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = client.get(f"/personas/{persona_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_upload_requires_auth(client):
    file_content = KAKAO_SAMPLE.encode("utf-8")
    resp = client.post(
        "/personas/upload",
        files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
        data={"my_name": "김미주"},
    )
    assert resp.status_code == 401


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
        assert mock_gen.call_count == 2


MERGE_RESULT = {
    "speech_style": 0.75,
    "emotion_frequency": 0.55,
    "response_pattern": "empathetic",
    "top_expressions": ["네", "안녕하세요", "그렇군요"],
    "initiative_score": 0.65,
    "summary": "업데이트된 공감형 패턴입니다.",
}


def test_update_persona_merges_profile(client, auth_headers):
    with patch("app.routers.personas.generate_profile", return_value=MOCK_PROFILE), \
         patch("app.routers.personas.merge_profiles", return_value=MERGE_RESULT) as mock_merge:
        file_content = KAKAO_SAMPLE.encode("utf-8")
        upload_resp = client.post(
            "/personas/upload",
            files={"file": ("kakao.txt", io.BytesIO(file_content), "text/plain")},
            data={"my_name": "김미주"},
            headers=auth_headers,
        )
        persona_id = upload_resp.json()[0]["id"]

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
