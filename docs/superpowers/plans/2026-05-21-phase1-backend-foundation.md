# Phase 1: 백엔드 기반 구축 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI 백엔드 기반 구축 — 프로젝트 셋업, PostgreSQL DB, JWT 인증, 카카오톡 파서, 기본 페르소나 CRUD API

**Architecture:** FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL(Docker Compose). JWT Bearer 인증. 카카오톡 .txt 파일을 파싱해 발화자별 메시지 분리 후 DB 저장. Claude API 연동은 Phase 2에서 처리하므로 이 단계에서 profile_json은 빈 dict로 저장.

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Alembic, PostgreSQL 15, python-jose(JWT), passlib(bcrypt), pytest, httpx

---

## 파일 구조

```
persona-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 앱 인스턴스, 라우터 등록
│   ├── config.py                # 환경변수 기반 설정
│   ├── database.py              # DB 엔진, 세션, Base
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User 테이블
│   │   ├── persona.py           # Persona 테이블
│   │   └── simulation.py        # Simulation 테이블 (Phase 3에서 사용)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py              # 인증 Pydantic 스키마
│   │   └── persona.py           # 페르소나 Pydantic 스키마
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # POST /auth/register, /auth/login
│   │   └── personas.py          # POST /personas/upload, GET/DELETE /personas
│   ├── services/
│   │   ├── __init__.py
│   │   └── kakao_parser.py      # 카카오톡 .txt 파싱 로직
│   └── core/
│       ├── __init__.py
│       ├── security.py          # 비밀번호 해시, JWT 생성/검증
│       └── deps.py              # FastAPI 의존성 (get_current_user)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures (테스트 DB, 클라이언트)
│   ├── test_kakao_parser.py     # 파서 단위 테스트
│   ├── test_auth.py             # 인증 API 테스트
│   └── test_personas.py         # 페르소나 API 테스트
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── requirements.txt
├── docker-compose.yml
└── .env.example
```

---

## Task 1: 프로젝트 파일 구조 및 의존성 설정

**Files:**
- Create: `persona-backend/requirements.txt`
- Create: `persona-backend/.env.example`
- Create: `persona-backend/app/__init__.py` (빈 파일)
- Create: `persona-backend/app/models/__init__.py` (빈 파일)
- Create: `persona-backend/app/schemas/__init__.py` (빈 파일)
- Create: `persona-backend/app/routers/__init__.py` (빈 파일)
- Create: `persona-backend/app/services/__init__.py` (빈 파일)
- Create: `persona-backend/app/core/__init__.py` (빈 파일)
- Create: `persona-backend/tests/__init__.py` (빈 파일)

- [ ] **Step 1: 프로젝트 루트 디렉토리 생성**

```bash
mkdir -p persona-backend/app/models
mkdir -p persona-backend/app/schemas
mkdir -p persona-backend/app/routers
mkdir -p persona-backend/app/services
mkdir -p persona-backend/app/core
mkdir -p persona-backend/tests
touch persona-backend/app/__init__.py
touch persona-backend/app/models/__init__.py
touch persona-backend/app/schemas/__init__.py
touch persona-backend/app/routers/__init__.py
touch persona-backend/app/services/__init__.py
touch persona-backend/app/core/__init__.py
touch persona-backend/tests/__init__.py
```

- [ ] **Step 2: requirements.txt 작성**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.12
pydantic[email]==2.9.2
pydantic-settings==2.5.2
httpx==0.27.0
pytest==8.3.3
pytest-asyncio==0.24.0
anthropic==0.34.0
```

- [ ] **Step 3: .env.example 작성**

```
DATABASE_URL=postgresql://persona_user:persona_pass@localhost:5432/persona_db
SECRET_KEY=change-this-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

- [ ] **Step 4: 의존성 설치**

```bash
cd persona-backend
pip install -r requirements.txt
```

Expected: 모든 패키지 설치 성공

- [ ] **Step 5: 커밋**

```bash
git checkout -b phase1-backend-foundation
git add persona-backend/
git commit -m "chore: Phase1 프로젝트 구조 및 의존성 설정"
```

---

## Task 2: Docker Compose + PostgreSQL 설정

**Files:**
- Create: `persona-backend/docker-compose.yml`

- [ ] **Step 1: docker-compose.yml 작성**

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: persona_db
      POSTGRES_USER: persona_user
      POSTGRES_PASSWORD: persona_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U persona_user -d persona_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 2: DB 컨테이너 시작**

```bash
cd persona-backend
docker-compose up -d
```

Expected: `persona-backend-db-1` 컨테이너가 Up 상태

- [ ] **Step 3: 연결 확인**

```bash
docker-compose exec db psql -U persona_user -d persona_db -c "\l"
```

Expected: `persona_db` 데이터베이스 목록 출력

- [ ] **Step 4: 커밋**

```bash
git add persona-backend/docker-compose.yml
git commit -m "chore: Docker Compose PostgreSQL 설정"
```

---

## Task 3: 앱 설정 및 DB 연결

**Files:**
- Create: `persona-backend/app/config.py`
- Create: `persona-backend/app/database.py`

- [ ] **Step 1: config.py 작성**

```python
# persona-backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://persona_user:persona_pass@localhost:5432/persona_db"
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: database.py 작성**

```python
# persona-backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 커밋**

```bash
git add persona-backend/app/config.py persona-backend/app/database.py
git commit -m "feat: 앱 설정 및 DB 연결 모듈"
```

---

## Task 4: DB 모델 정의

**Files:**
- Create: `persona-backend/app/models/user.py`
- Create: `persona-backend/app/models/persona.py`
- Create: `persona-backend/app/models/simulation.py`

- [ ] **Step 1: User 모델 작성**

```python
# persona-backend/app/models/user.py
from uuid import uuid4
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    personas: Mapped[list["Persona"]] = relationship("Persona", back_populates="user")
```

- [ ] **Step 2: Persona 모델 작성**

```python
# persona-backend/app/models/persona.py
from uuid import uuid4
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "self" | "acquaintance"
    status: Mapped[str] = mapped_column(String, default="active")  # "active" | "archived"
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="personas")
    simulations: Mapped[list["Simulation"]] = relationship(
        "Simulation", back_populates="persona"
    )
```

- [ ] **Step 3: Simulation 모델 작성 (Phase 3에서 사용, 지금은 테이블만 정의)**

```python
# persona-backend/app/models/simulation.py
from uuid import uuid4
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    persona_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("personas.id"), nullable=False
    )
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)  # "template" | "free"
    scenario_config: Mapped[dict] = mapped_column(JSON, default=dict)
    turns: Mapped[list] = mapped_column(JSON, default=list)
    savepoints: Mapped[list] = mapped_column(JSON, default=list)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    persona: Mapped["Persona"] = relationship("Persona", back_populates="simulations")
```

- [ ] **Step 4: models/__init__.py에 임포트 등록**

```python
# persona-backend/app/models/__init__.py
from app.models.user import User
from app.models.persona import Persona
from app.models.simulation import Simulation

__all__ = ["User", "Persona", "Simulation"]
```

- [ ] **Step 5: 커밋**

```bash
git add persona-backend/app/models/
git commit -m "feat: DB 모델 정의 (User, Persona, Simulation)"
```

---

## Task 5: Alembic 마이그레이션 설정

**Files:**
- Create: `persona-backend/alembic.ini`
- Modify: `persona-backend/alembic/env.py`

- [ ] **Step 1: Alembic 초기화**

```bash
cd persona-backend
alembic init alembic
```

Expected: `alembic/` 디렉토리와 `alembic.ini` 생성

- [ ] **Step 2: alembic.ini의 sqlalchemy.url 수정**

`alembic.ini` 파일에서 아래 줄을 찾아 수정:
```ini
sqlalchemy.url = postgresql://persona_user:persona_pass@localhost:5432/persona_db
```

- [ ] **Step 3: alembic/env.py 수정 — 모델 임포트 추가**

`alembic/env.py`에서 `target_metadata = None` 부분을 찾아 아래로 교체:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.models import User, Persona, Simulation  # noqa: F401

target_metadata = Base.metadata
```

- [ ] **Step 4: 첫 마이그레이션 생성 및 적용**

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

Expected: `alembic/versions/xxxx_initial_tables.py` 생성, DB에 테이블 3개 생성

- [ ] **Step 5: 테이블 확인**

```bash
docker-compose exec db psql -U persona_user -d persona_db -c "\dt"
```

Expected: `users`, `personas`, `simulations` 테이블 목록 출력

- [ ] **Step 6: 커밋**

```bash
git add alembic/ alembic.ini
git commit -m "feat: Alembic 마이그레이션 초기 설정"
```

---

## Task 6: JWT 보안 모듈

**Files:**
- Create: `persona-backend/app/core/security.py`
- Create: `persona-backend/app/core/deps.py`
- Create: `persona-backend/tests/conftest.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# persona-backend/tests/test_auth.py
import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hash_and_verify():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_token():
    token = create_access_token({"sub": "user-id-123"})
    user_id = decode_token(token)
    assert user_id == "user-id-123"


def test_decode_invalid_token():
    result = decode_token("invalid.token.here")
    assert result is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd persona-backend
pytest tests/test_auth.py -v
```

Expected: `ImportError` 또는 `ModuleNotFoundError` (security.py 없음)

- [ ] **Step 3: security.py 구현**

```python
# persona-backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_auth.py::test_password_hash_and_verify tests/test_auth.py::test_create_and_decode_token tests/test_auth.py::test_decode_invalid_token -v
```

Expected: 3개 PASSED

- [ ] **Step 5: deps.py 구현**

```python
# persona-backend/app/core/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user
```

- [ ] **Step 6: 커밋**

```bash
git add persona-backend/app/core/ persona-backend/tests/test_auth.py
git commit -m "feat: JWT 보안 모듈 (hash, token 생성/검증)"
```

---

## Task 7: 인증 API (register / login)

**Files:**
- Create: `persona-backend/app/schemas/user.py`
- Create: `persona-backend/app/routers/auth.py`
- Modify: `persona-backend/tests/conftest.py`
- Modify: `persona-backend/tests/test_auth.py`

- [ ] **Step 1: conftest.py 작성 (테스트용 SQLite in-memory DB)**

```python
# persona-backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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
```

- [ ] **Step 2: 인증 API 실패 테스트 추가**

`tests/test_auth.py` 파일에 아래 테스트 추가:

```python
def test_register_success(client):
    resp = client.post("/auth/register", json={"email": "new@test.com", "password": "pass123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@test.com"


def test_register_duplicate_email(client):
    client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    resp = client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={"email": "login@test.com", "password": "pass123"})
    resp = client.post("/auth/login", json={"email": "login@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "wp@test.com", "password": "pass123"})
    resp = client.post("/auth/login", json={"email": "wp@test.com", "password": "wrong"})
    assert resp.status_code == 401
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
pytest tests/test_auth.py -v -k "register or login"
```

Expected: FAILED (라우터 미구현)

- [ ] **Step 4: schemas/user.py 작성**

```python
# persona-backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: routers/auth.py 작성**

```python
# persona-backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
    user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    token = create_access_token({"sub": user.id})
    return Token(access_token=token)
```

- [ ] **Step 6: main.py 작성 (라우터 등록)**

```python
# persona-backend/app/main.py
from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="Persona API", version="1.0.0")

app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: 테스트 통과 확인**

```bash
pytest tests/test_auth.py -v
```

Expected: 모든 테스트 PASSED

- [ ] **Step 8: 커밋**

```bash
git add persona-backend/app/schemas/user.py persona-backend/app/routers/auth.py persona-backend/app/main.py persona-backend/tests/
git commit -m "feat: 사용자 인증 API (register/login)"
```

---

## Task 8: 카카오톡 파서

**Files:**
- Create: `persona-backend/app/services/kakao_parser.py`
- Create: `persona-backend/tests/test_kakao_parser.py`

- [ ] **Step 1: 실패하는 파서 테스트 작성**

```python
# persona-backend/tests/test_kakao_parser.py
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_kakao_parser.py -v
```

Expected: FAILED (kakao_parser.py 없음)

- [ ] **Step 3: kakao_parser.py 구현**

```python
# persona-backend/app/services/kakao_parser.py
import re
from typing import Dict, List

_DATE_PATTERN = re.compile(r"(\d{4})년\s+(\d{1,2})월\s+(\d{1,2})일")
_NEW_MSG_PATTERN = re.compile(r"^(오전|오후)\s+(\d{1,2}:\d{2}),\s+(.+?)\s+:\s+(.+)$")
_OLD_MSG_PATTERN = re.compile(r"^\[(.+?)\]\s+\[(오전|오후)\s+(\d{1,2}:\d{2})\]\s+(.+)$")


def parse_kakao_export(content: str) -> List[Dict[str, str]]:
    """카카오톡 .txt 내보내기 파일을 파싱해 메시지 목록 반환."""
    messages = []
    current_date = ""

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        date_match = _DATE_PATTERN.search(line)
        if date_match:
            year, month, day = date_match.groups()
            current_date = f"{year}-{int(month):02d}-{int(day):02d}"
            continue

        new_match = _NEW_MSG_PATTERN.match(line)
        if new_match:
            ampm, time, sender, text = new_match.groups()
            messages.append(
                {
                    "date": current_date,
                    "time": f"{ampm} {time}",
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
            )
            continue

        old_match = _OLD_MSG_PATTERN.match(line)
        if old_match:
            sender, ampm, time, text = old_match.groups()
            messages.append(
                {
                    "date": current_date,
                    "time": f"{ampm} {time}",
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
            )

    return messages


def extract_speakers(messages: List[Dict[str, str]]) -> List[str]:
    """메시지 목록에서 발화자 목록 반환 (순서 유지, 중복 제거)."""
    return list(dict.fromkeys(m["sender"] for m in messages))


def filter_by_sender(messages: List[Dict[str, str]], sender: str) -> List[Dict[str, str]]:
    """특정 발화자의 메시지만 필터링."""
    return [m for m in messages if m["sender"] == sender]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_kakao_parser.py -v
```

Expected: 5개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add persona-backend/app/services/kakao_parser.py persona-backend/tests/test_kakao_parser.py
git commit -m "feat: 카카오톡 .txt 파싱 서비스 (신/구 포맷 지원)"
```

---

## Task 9: 페르소나 업로드 및 CRUD API

**Files:**
- Create: `persona-backend/app/schemas/persona.py`
- Create: `persona-backend/app/routers/personas.py`
- Modify: `persona-backend/app/main.py`
- Create: `persona-backend/tests/test_personas.py`

- [ ] **Step 1: 실패하는 페르소나 API 테스트 작성**

```python
# persona-backend/tests/test_personas.py
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
    assert len(data) == 2  # self + acquaintance
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_personas.py -v
```

Expected: FAILED (라우터 미구현)

- [ ] **Step 3: schemas/persona.py 작성**

```python
# persona-backend/app/schemas/persona.py
from datetime import datetime
from typing import List

from pydantic import BaseModel


class PersonaResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    profile_json: dict
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaListResponse(BaseModel):
    personas: List[PersonaResponse]
    total: int
```

- [ ] **Step 4: routers/personas.py 작성**

```python
# persona-backend/app/routers/personas.py
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.persona import Persona
from app.models.user import User
from app.schemas.persona import PersonaListResponse, PersonaResponse
from app.services.kakao_parser import (
    extract_speakers,
    filter_by_sender,
    parse_kakao_export,
)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("/upload", response_model=List[PersonaResponse], status_code=201)
async def upload_kakao_file(
    file: UploadFile = File(...),
    my_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = (await file.read()).decode("utf-8")
    messages = parse_kakao_export(content)

    if not messages:
        raise HTTPException(status_code=400, detail="파싱 가능한 메시지가 없습니다.")

    speakers = extract_speakers(messages)
    if my_name not in speakers:
        raise HTTPException(status_code=400, detail=f"'{my_name}' 발화자를 찾을 수 없습니다.")

    created_personas = []

    # 나의 페르소나
    my_messages = filter_by_sender(messages, my_name)
    self_persona = Persona(
        user_id=current_user.id,
        name=my_name,
        type="self",
        message_count=len(my_messages),
        profile_json={},  # Phase 2에서 Claude API로 채움
    )
    db.add(self_persona)
    created_personas.append(self_persona)

    # 지인 페르소나 (나를 제외한 발화자들)
    for speaker in speakers:
        if speaker == my_name:
            continue
        their_messages = filter_by_sender(messages, speaker)
        acquaintance_persona = Persona(
            user_id=current_user.id,
            name=speaker,
            type="acquaintance",
            message_count=len(their_messages),
            profile_json={},  # Phase 2에서 Claude API로 채움
        )
        db.add(acquaintance_persona)
        created_personas.append(acquaintance_persona)

    db.commit()
    for p in created_personas:
        db.refresh(p)

    return created_personas


@router.get("", response_model=PersonaListResponse)
def list_personas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personas = (
        db.query(Persona)
        .filter(Persona.user_id == current_user.id, Persona.status == "active")
        .all()
    )
    return PersonaListResponse(personas=personas, total=len(personas))


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: str,
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
    return persona


@router.delete("/{persona_id}", status_code=204)
def delete_persona(
    persona_id: str,
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
    db.delete(persona)
    db.commit()
```

- [ ] **Step 5: main.py에 personas 라우터 추가**

```python
# persona-backend/app/main.py
from fastapi import FastAPI
from app.routers import auth, personas

app = FastAPI(title="Persona API", version="1.0.0")

app.include_router(auth.router)
app.include_router(personas.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
pytest tests/test_personas.py -v
```

Expected: 5개 PASSED

- [ ] **Step 7: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모든 테스트 PASSED

- [ ] **Step 8: 커밋**

```bash
git add persona-backend/app/schemas/persona.py persona-backend/app/routers/personas.py persona-backend/app/main.py persona-backend/tests/test_personas.py
git commit -m "feat: 페르소나 업로드 및 CRUD API"
```

---

## Task 10: 서버 실행 확인 및 Phase 1 완료

- [ ] **Step 1: .env 파일 생성**

```bash
cd persona-backend
cp .env.example .env
# SECRET_KEY를 랜덤 값으로 교체
python -c "import secrets; print(secrets.token_hex(32))"
# 출력된 값을 .env의 SECRET_KEY에 붙여넣기
```

- [ ] **Step 2: 서버 실행**

```bash
uvicorn app.main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 3: Swagger UI 확인**

브라우저에서 `http://127.0.0.1:8000/docs` 열기

Expected: `/auth/register`, `/auth/login`, `/personas/upload`, `/personas` 엔드포인트 목록 확인

- [ ] **Step 4: Phase 1 최종 커밋**

```bash
git add .
git commit -m "feat: Phase 1 백엔드 기반 구축 완료

- FastAPI 프로젝트 구조
- PostgreSQL + Alembic 마이그레이션
- JWT 인증 (register/login)
- 카카오톡 .txt 파서 (신/구 포맷)
- 페르소나 CRUD API (profile_json은 Phase 2에서 채움)"
```

---

## 다음 단계

**Phase 2: 페르소나 엔진** — Claude API를 연동해 `profile_json`을 실제 심리 프로파일로 채우고, 페르소나 업데이트(가중치 병합) 로직 구현
