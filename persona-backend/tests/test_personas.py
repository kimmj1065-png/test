# -*- coding: utf-8 -*-
import io
import pytest


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
