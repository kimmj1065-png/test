import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

DEFAULT_MOCK_PROFILE = {
    "speech_style": 0.5,
    "emotion_frequency": 0.5,
    "response_pattern": "empathetic",
    "top_expressions": [],
    "initiative_score": 0.5,
    "summary": "테스트용 프로파일",
}

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_generate_profile():
    with patch("app.routers.personas.generate_profile", return_value=DEFAULT_MOCK_PROFILE):
        yield


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    client.post("/auth/register", json={"email": "test@test.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "test@test.com", "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
