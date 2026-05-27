# AI 에이전트 인수인계 가이드

이 문서는 이 프로젝트를 이어받는 AI 에이전트를 위한 기술 가이드입니다.

---

## 이 시스템이 무엇을 하는가

반도체 Fab에서 OHT(천장 주행 로봇) 와 Storage(버퍼 장치)의 월별 수급 과부족을 예측합니다.
현재 회사에서는 12개월 이동평균 선형 회귀를 쓰고 있고, 이 시스템은 그것을 아래 방식으로 고도화합니다.

---

## 핵심 도메인 지식 (반드시 이해해야 할 것)

### 1. 예측 체인 구조
현재 담당자들이 실제로 쓰는 예측 순서:
```
생산계획 (wafer 투입량) → movement (lot 이동 횟수) → 반송량 → 반송시간
```
- **생산계획 ≠ movement**: movement는 중간 변수입니다 (lot이 몇 번 이동하는지)
- **투입계획(input_plan)은 예측에 사용하지 않음**: 주 3회 이상 변경되어 신뢰도 없음. DB에 이력만 저장.

### 2. OHT 부하율 항상 70% 이상
현장에서 OHT 부하율이 70% 아래로 내려간 적이 없습니다.
따라서 `model_trainer.py`의 `train_transport_time_model`에서 저부하 데이터로 `base_time`을 추정할 수 없습니다.
해결책: `scipy.curve_fit`으로 `base_time`과 `a_line` **동시 추정** (2개 파라미터, 전체 데이터 사용).

### 3. OHT는 floor 단위로 배치됨
- 대부분: 1 fab = 1 floor (1:1)
- 일부: 1 floor에 2개 라인이 공존 (OHT 공유)
- **OHT 과부족은 반드시 (site, floor) 단위로 합산**해야 합니다
- `aggregate_oht_by_floor()` 함수가 이 역할을 합니다

### 4. Storage 구성 = Product + Non-Product
```
total_storage = product_FOUP + NPW_FOUP + empty_FOUP
```
- product: 재공(WIP) 기반 예측 → LightGBM
- non_product (NPW + empty): `total_actual - product_actual`의 3개월 평균으로 추정
- 실적 데이터에 `storage_product_actual`과 `storage_total_actual` 둘 다 있음 (분리 가능 확인됨)
- 제조 작업 종류에 따라 NPW 비중이 달라서 total만으로 예측하면 모델이 흔들림

---

## 파일별 역할 요약

| 파일 | 역할 | 주의사항 |
|---|---|---|
| `app/database.py` | SQLAlchemy 모델 정의 + DB 초기화 | SQLite 사용. 운영 전환 시 PostgreSQL로 변경 필요 |
| `app/services/excel_parser.py` | Excel 파싱. 한국어/영어 컬럼명 모두 처리 | `PLAN_COL_MAP`, `ACTUAL_COL_MAP` 딕셔너리 확인 |
| `app/services/model_trainer.py` | Step 1~3 + Storage 모델 학습 | `_ewma_weights()`: 감쇠 계수 λ=0.1 (조정 가능), `_detect_breakpoint()`: 15% 변동 시 감지 |
| `app/services/oht_calculator.py` | OHT 수요 계산 + floor 집계 | `aggregate_oht_by_floor()`가 핵심. line 단위 수요를 floor 단위로 sum |
| `app/services/storage_calculator.py` | Storage 수요 계산 | `_rolling_non_product()`: 최근 3개월 avg |
| `app/routers/capacity.py` | OHT/Storage 과부족 API | `movement_delta` 파라미터로 시나리오 분석 지원 (현재 라우터에 미구현 — 추가 필요) |

---

## 미완성/개선 필요 항목

### 즉시 구현 필요
1. **`capacity.py`의 `movement_delta` 파라미터 처리**
   - 현재 `/capacity/oht`와 `/capacity/storage`는 `movement_delta` 파라미터를 받지만 실제로 plan_df에 적용하지 않음
   - `_load_plan()` 이후 `plan_df["movement_plan"] *= (1 + movement_delta)` 추가 필요

2. **`models.py`의 Step 1 학습 로직 수정**
   - 현재 `train_movement_model()`에 plan 데이터가 없음 (actual만 있음)
   - 실제로는 실적 DB + 계획 DB를 `actual_month == plan_month`로 join해서 사용해야 함
   - `PlanRecord`와 `ActualRecord`를 월로 join하는 로직 추가 필요

3. **Bootstrap 신뢰구간 UI 연동**
   - `uncertainty.py`는 구현되어 있으나 capacity API와 연동되지 않음
   - `/capacity/oht`에 `ci=true` 파라미터 추가 → Bootstrap 실행 후 ci_lower/ci_upper 반환

### 향후 개선
4. **NPW 계획 데이터 활용**: `npw_plan` 컬럼이 DB에 있지만 non_product 예측에 미사용. NPW 작업 계획이 있으면 별도 회귀 추가
5. **모델 버전 관리**: 현재 joblib 파일 덮어쓰기. 날짜별 버전 관리 추가 권장
6. **PostgreSQL 전환**: `database.py`의 `create_engine` URL만 변경하면 됨

---

## 테스트 방법 (실데이터 없이)

샘플 데이터를 생성하여 전체 흐름을 테스트하세요:

```python
# 테스트용 실적 데이터 생성 (Python)
import pandas as pd
import numpy as np

months = pd.date_range("2024-01", periods=24, freq="MS").strftime("%Y-%m")
rows = []
for m in months:
    for line in ["L1", "L2"]:
        movement = np.random.normal(10000, 500)
        tc = movement * 12 + np.random.normal(0, 500)      # transport_count
        rho = 0.75 + np.random.normal(0, 0.05)
        base_t = 45.0
        tt = base_t * (1 + 0.8 * rho / (1 - rho))          # queuing model
        rows.append({
            "사이트": "Fab1", "라인": line, "층": "F1", "DR타입": "DRAM",
            "실적월": m, "생산실적": movement,
            "반송량실적": tc, "반송시간실적": tt,
            "저장량실적(product)": movement * 0.5,
            "저장량실적(total)": movement * 0.5 + 300,
        })

df = pd.DataFrame(rows)
df.to_excel("test_actuals.xlsx", index=False)
```

---

## 주요 수식

### 반송시간 모델 (대기행렬)
```
반송시간 = base_time × (1 + a_line × ρ / (1 - ρ))
ρ = (반송량 × base_time) / (OHT_대수 × 월가동시간 × 3600)

학습: scipy.curve_fit(model_fn, X=반송량실적, y=반송시간실적)
파라미터: [base_time, a_line], bounds=([0,0], [inf,inf])
```

### EWMA 가중치
```python
ages = [n-1, n-2, ..., 1, 0]  # 오래된 데이터일수록 큰 age
weights = exp(-λ × ages)       # λ=0.1 기본값
# → 최신 달이 가장 높은 가중치
```

### OHT 과부족
```
필요_OHT_시간(floor) = Σ(라인별 반송량 × 반송시간 / 3600)
가용_OHT_시간(floor) = OHT_대수 × 월가동시간
과부족(대수) = (가용 - 필요) / 월가동시간
```

---

## 의존성 버전 (주요)

```
fastapi==0.115.0
streamlit==1.38.0
scipy==1.14.1       ← curve_fit 사용
lightgbm==4.5.0
scikit-learn==1.5.2
sqlalchemy==2.0.35
```

---

## 데이터 흐름 다이어그램

```
[Excel 업로드]
      │
      ▼
[excel_parser.py] ── 컬럼 정규화 ──► [DB: actuals / plans]
                                            │
                                            ▼
                                    [model_trainer.py]
                                    ├─ train_movement_model()      → model_store/movement/
                                    ├─ train_transport_count_model()→ model_store/transport_count/
                                    ├─ train_transport_time_model() → model_store/transport_time/
                                    └─ train_storage_model()       → model_store/storage_product/
                                            
[계획 업로드] → [DB: plans]
                    │
                    ▼
            [oht_calculator.py]
            ├─ predict_movement()
            ├─ predict_transport_count()
            └─ predict_transport_time()  ← 대기행렬 모델
                    │
                    ▼
            [aggregate_oht_by_floor()]
                    │
                    ▼
            [capacity.py API] → [Streamlit UI]
```
