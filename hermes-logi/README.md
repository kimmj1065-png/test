# Hermes-Logi — 반도체 물류 중장기 Capa 분석 시스템

반도체 Fab 물류 담당자가 **월별 OHT·Storage 과부족을 예측**하는 웹 분석 도구입니다.

---

## 시스템 개요

### 예측 체인 (3단계 회귀)

```
생산계획(wafer 투입량)
    ↓ Step 1: EWMA 가중 OLS + 변곡점 감지
movement 예측 (lot 이동 횟수)
    ↓ Step 2: DR×라인별 EWMA OLS
반송량 예측 (OHT 반송 횟수)
    ↓ Step 3: 대기행렬 비선형 curve_fit
반송시간 예측 → OHT 필요 시간 → OHT 과부족
```

### 핵심 설계 결정 사항

| 항목 | 결정 | 이유 |
|---|---|---|
| 투입계획 미사용 | 이력 보관만 | 주 3회 이상 변경 → 예측 입력으로 부적합 |
| EWMA 가중 회귀 | 최신 데이터에 지수적 높은 가중치 | 12개월 평균은 급격한 증산/감산 시 정합성 붕괴 |
| base_time 동시 fitting | scipy.curve_fit으로 base_time + a_line 동시 추정 | OHT 부하율 항상 70%+ → 저부하 관측 데이터 없음 |
| OHT 집계 단위 = floor | 같은 floor 내 여러 라인 수요 합산 | OHT는 floor에 배치되며 라인 간 공유 가능 |
| Storage 분리 예측 | product + non_product 별도 계산 | NPW·Empty FOUP 혼재로 단순 total 예측 시 모델 붕괴 |

---

## 빠른 시작

### 1. 환경 설정

```bash
pip install -r requirements.txt
```

### 2. FastAPI 백엔드 실행

```bash
cd hermes-logi
uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000/docs` → Swagger UI 확인

### 3. Streamlit UI 실행

```bash
streamlit run streamlit_ui/app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 사용 순서

### Step A. 기준 데이터 입력 (최초 1회)

`기준데이터` 페이지 또는 API (`/reference/*`):

1. **OHT 대수** — (site, floor) 단위 등록. 같은 floor의 라인이 2개여도 OHT는 한 번만 등록
2. **Storage 용량** — (site, line, floor) 단위 등록
3. **DR별 Step 수** — DR 타입별 공정 step 수 등록

### Step B. 실적 데이터 업로드 + 모델 학습

`데이터업로드` 페이지:

1. 월별 실적 Excel 업로드 (`/actuals/upload`)
   - 컬럼: 사이트, 라인, 층, DR타입, 실적월, 생산실적, 반송량실적, 반송시간실적, 저장량실적(product), 저장량실적(total)
2. **모델 학습 실행** (`/models/train/all`)
   - 최소 6개월 데이터 필요. 2년 이상 권장.

### Step C. 생산계획 업로드

`데이터업로드` 페이지:

- 예측 대상 월의 계획 Excel 업로드 (`/planning/upload`)
- 컬럼: 사이트, 라인, 층, DR타입, 계획월, 생산계획, 재공계획, LOT크기 (투입계획은 이력 저장만)

### Step D. 과부족 조회

- `OHT Capa` 페이지: floor 단위 월별 과부족 바차트 + 라인별 기여 파이차트
- `Storage Capa` 페이지: product/non-product 스택 바 + 과부족 바
- `시나리오 분석` 페이지: 생산계획 ±% 변동 시뮬레이션

---

## 디렉토리 구조

```
hermes-logi/
├── app/
│   ├── main.py                  # FastAPI 진입점
│   ├── database.py              # SQLAlchemy 모델 (SQLite)
│   ├── services/
│   │   ├── excel_parser.py      # Excel 파싱, 컬럼 정규화 (한/영 모두 지원)
│   │   ├── model_trainer.py     # Step 1~3 + Storage 모델 학습
│   │   ├── oht_calculator.py    # OHT 산출 체인 + floor 집계
│   │   ├── storage_calculator.py# Storage 산출 (product + non_product)
│   │   └── uncertainty.py       # Bootstrap 신뢰구간 (향후 연동)
│   └── routers/
│       ├── actuals.py           # 실적 업로드/조회
│       ├── planning.py          # 계획 업로드/조회
│       ├── reference.py         # 기준 데이터 CRUD
│       ├── models.py            # 모델 학습/계수 조회
│       └── capacity.py          # OHT·Storage 과부족 산출
│
├── streamlit_ui/
│   ├── app.py                   # 메인 페이지
│   └── pages/
│       ├── 01_기준데이터.py
│       ├── 02_데이터업로드.py
│       ├── 03_OHT_Capa.py
│       ├── 04_Storage_Capa.py
│       ├── 05_시나리오분석.py
│       └── 06_모델현황.py
│
├── model_store/                 # 학습된 모델 저장 (joblib)
│   ├── movement/
│   ├── transport_count/
│   ├── transport_time/
│   └── storage_product/
│
├── data/
│   ├── sample_planning.xlsx     # 계획 업로드 샘플 양식
│   └── sample_actuals.xlsx      # 실적 업로드 샘플 양식
│
└── requirements.txt
```

---

## API 주요 엔드포인트

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/actuals/upload` | 실적 Excel 업로드 |
| GET | `/actuals/sample` | 실적 샘플 양식 다운로드 |
| POST | `/planning/upload` | 계획 Excel 업로드 |
| GET | `/planning/sample` | 계획 샘플 양식 다운로드 |
| POST | `/reference/floor-config` | OHT 기준 데이터 등록 |
| POST | `/reference/storage-config` | Storage 용량 등록 |
| POST | `/reference/dr-steps` | DR step 수 등록 |
| POST | `/models/train/all` | 전체 모델 학습 |
| GET | `/capacity/oht` | OHT 과부족 산출 |
| GET | `/capacity/storage` | Storage 과부족 산출 |

---

## 모델 상세

### Step 3. 반송시간 대기행렬 모델

OHT 부하율이 항상 70% 이상이므로 저부하 데이터 없음 → `scipy.optimize.curve_fit`으로 `base_time`과 `a_line`을 **동시 추정**합니다.

```python
반송시간 = base_time × (1 + a_line × ρ / (1 - ρ))
ρ = (반송량 × base_time) / (OHT_대수 × 월가동시간 × 3600)
```

- ρ → 0: 반송시간 → base_time (이론적 최소)
- ρ → 1: 반송시간 → ∞ (포화 상태)
- a_line: 라인별 혼잡 민감도 (데이터로 학습)

### Storage 분리 예측

```
total = product + non_product
product: LightGBM(재공, lot_size, DR_step, 월)
non_product: 최근 3개월 rolling avg of (total_actual - product_actual)
```

non_product에는 NPW FOUP + Empty FOUP이 포함됩니다.
제조 작업(NPW 비중)에 따라 변동이 크므로 별도 추정합니다.

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DB_PATH` | `hermes.db` | SQLite DB 파일 경로 |
| `MODEL_DIR` | `model_store` | 학습된 모델 저장 디렉토리 |

Streamlit 시크릿 (`streamlit_ui/.streamlit/secrets.toml`):
```toml
API_URL = "http://localhost:8000"
```
