# OHT/Storage 예측 모델 — AI 에이전트 작업 가이드

이 문서는 이 프로젝트를 처음 보는 **AI 에이전트(하위 에이전트)** 를 위한 안내서입니다.  
사람이 읽어도 됩니다.

---

## 프로젝트 한 줄 요약

반도체 팹 OHT(Overhead Hoist Transport) 반송량·반송시간·부하율과  
Storage 점유율을 **월 단위**로 예측하는 물리식 기반 회귀 모델입니다.

---

## 디렉터리 구조

```
oht_predictor/
├── AGENT_GUIDE.md            ← 지금 읽고 있는 이 파일 (에이전트 가이드)
├── README.md                 ← 사람용 상세 사용 설명서
├── requirements.txt          ← pip 의존 패키지 목록
│
├── constants.py              ← 전역 상수 정의
├── data_loader.py            ← 데이터 로드 (★실적 교체 진입점★)
├── model.py                  ← 회귀 모델 학습 로직
├── predictor.py              ← 월별 예측 실행 로직
├── reporter.py               ← 산출물 생성 (CSV·그래프·리포트)
├── main.py                   ← 실행 진입점
│
├── generate_sample_data.py   ← 테스트용 합성 데이터 생성기
│
└── sample_data/
    ├── actuals.csv           ← 실적 데이터 (← 실제 데이터로 교체)
    └── plan.csv              ← 생산 계획 데이터
```

---

## 실행 순서 (에이전트가 따라야 할 절차)

```
1. pip install -r requirements.txt
2. sample_data/actuals.csv  →  실제 실적으로 교체
   sample_data/plan.csv     →  실제 계획으로 교체
3. python main.py
4. output/ 디렉터리에서 결과 확인
```

---

## 각 파일의 책임 (에이전트가 코드를 수정할 때 참고)

### `constants.py`
- 수정 대상: 경보 임계값, 슬롯 수, 저부하 기준 월 수 등
- 이 파일 하나만 바꾸면 전체 임계값이 일괄 변경됨
- 주요 상수:
  ```python
  TOTAL_SLOT  = 37938   # Storage 총 슬롯 수
  UTIL_WARN   = 0.85    # OHT 부하율 경보 임계
  OCC_WARN    = 0.85    # Storage 점유율 경보 임계
  LOWLOAD_N   = 6       # T0_ref 산정 저부하 월 수
  SENS_Z      = 1.0     # 불확실성 밴드 배수 (1σ)
  ```

---

### `data_loader.py` ← 실적 교체 시 수정할 파일

**함수 2개만 있습니다:**

```python
load_actuals(path)   # 실적 CSV → DataFrame 반환
load_plan(path)      # 계획 CSV → DataFrame 반환
```

**실적 교체 방법 3가지:**

| 방법 | 설명 |
|------|------|
| A. CSV 덮어쓰기 | `sample_data/actuals.csv`를 실제 데이터로 덮어쓰기 |
| B. CLI 인자 | `python main.py --actuals /경로/real.csv` |
| C. 함수 수정 | `load_actuals()` 내부를 DB 조회로 교체 |

**반환 DataFrame이 반드시 가져야 할 컬럼:**

```
actuals 필수 컬럼:
  month        (str, YYYY-MM)
  prod         (float/int)
  wip          (float/int)
  lot_size     (float)
  move_qty     (float) — 회/hr
  move_time    (float) — 초
  load_dist    (float) — mm
  oht_count    (int)
  storage_prod (float/int) — 캐리어
  storage_npw  (float/int) — 캐리어

plan 필수 컬럼:
  month         (str, YYYY-MM)
  prod_plan     (float/int)
  lot_size_plan (float)
  wip_plan      (float/int)
```

---

### `model.py`

**공개 함수 2개:**

```python
fit(df: pd.DataFrame) -> tuple[ModelParams, ModelMetrics]
    # actuals DataFrame을 받아 모델을 학습
    # → ModelParams(파라미터), ModelMetrics(R², MAPE) 반환

calc_congestion(move_qty, T0_ref, oht_count) -> np.ndarray
    # 혼잡도 계산: cong = move_qty·T0_ref / (oht_count·3600)
    # cong ≥ 1.0 이면 물리적 포화
```

**학습하는 모델 4종:**

| # | 수식 | 파라미터 |
|---|------|----------|
| ① 반송량 | `move_qty = k·(prod/lot_size)` | k |
| ② 반송시간 | `move_time = t0 + v_load·load_dist + b·cong/(1-cong)` | t0, v_load, b |
| ③ 생산FOUP | `storage_prod = α·wip + β·wip·cong/(1-cong)` | α, β |
| ④ 비생산FOUP | `storage_npw = γ + δ·move_qty` | γ, δ |

**중요 설계 제약 (수정 시 지켜야 할 것):**
- 혼잡도(cong) 계산에 `move_time`을 포함하면 **순환 참조** 발생 → 금지
- `move_time` 회귀는 반드시 **표준화 후 OLS → 역변환** 순서 유지  
  (load_dist의 mm 단위 절대값이 커서 표준화 없으면 수치 불안정)

---

### `predictor.py`

**공개 함수 1개:**

```python
predict(plan: pd.DataFrame, p: ModelParams) -> pd.DataFrame
    # plan의 각 행에 대해 예측값 계산 → 결과 DataFrame 반환
```

**예측 순서 (Step 1~5, 반드시 이 순서):**
```
Step 1: move_qty  = k·(prod_plan/lot_size_plan)
Step 2: cong      = move_qty·T0_ref/(OHT_FIXED·3600)
        move_time = t0 + v_load·load_const + b·cong/(1-cong)
        util      = move_qty·move_time/3600/OHT_FIXED
Step 3: storage_prod, storage_npw, storage_total, occupancy 계산
Step 4: 불확실성 밴드 (move_time_lo/hi, util_lo/hi)
Step 5: 경보 플래그 (포화경보, 부하율경보, 외삽여부, 점유경보)
```

**반환 DataFrame 컬럼:**
```
month, move_qty, move_time, move_time_lo, move_time_hi,
util, util_lo, util_hi, cong,
storage_prod, storage_npw, storage_total, occupancy,
포화경보(bool), 부하율경보(bool), 외삽여부(bool), 점유경보(bool)
```

---

### `reporter.py`

**공개 함수 1개:**

```python
save_all(actuals, forecast, params, metrics) -> None
    # output/ 디렉터리에 산출물 전체 저장
```

**생성 산출물:**
```
output/
├── param_report.txt     ← 파라미터 및 R²/MAPE 리포트
├── forecast.csv         ← 월별 예측 테이블 (UTF-8 BOM)
├── warnings.txt         ← 경보 발생 월 요약
├── plot_move_qty.png    ← 반송량 시계열
├── plot_move_time.png   ← 반송시간 + 불확실성 밴드
├── plot_scatter.png     ← 실측 vs 예측 산점도
├── plot_util.png        ← 부하율 + 경보선
└── plot_occupancy.png   ← Storage 점유율 + 경보선
```

---

### `main.py`

**CLI 인터페이스:**
```bash
python main.py                              # 기본 (sample_data/ 사용)
python main.py --actuals <경로>             # 실적 파일 지정
python main.py --actuals <경로> --plan <경로>  # 둘 다 지정
```

**내부 호출 순서:**
```
load_actuals() → load_plan()
  → fit(actuals)
  → predict(plan, params)
  → save_all(actuals, forecast, params, metrics)
```

---

## 에이전트가 자주 받을 수 있는 요청 유형

### 요청: "실적 데이터를 바꿔줘"
→ `sample_data/actuals.csv`를 교체하거나 `data_loader.py`의 `load_actuals()` 수정

### 요청: "경보 기준을 80%로 낮춰줘"
→ `constants.py`에서 `UTIL_WARN = 0.80`, `OCC_WARN = 0.80` 변경

### 요청: "불확실성 밴드를 2σ로 늘려줘"
→ `constants.py`에서 `SENS_Z = 2.0` 변경

### 요청: "Storage 슬롯이 40000으로 늘어났어"
→ `constants.py`에서 `TOTAL_SLOT = 40000` 변경

### 요청: "OHT를 65대로 늘렸을 때 시나리오 보고 싶어"
→ `predictor.py`의 `_predict_row()` 에서 `p.OHT_FIXED` 사용 부분을 시나리오 값으로 대체하거나,  
   `ModelParams.OHT_FIXED`를 덮어써서 `predict()` 재호출

### 요청: "그래프를 영어로 바꿔줘"
→ `reporter.py`에서 `set_title()`, `set_ylabel()`, `label=` 인자 문자열 수정

### 요청: "plan.csv에 OHT 대수 컬럼을 추가해서 시나리오별로 계산하고 싶어"
→ `data_loader.py`에서 `PLAN_COLS`에 `"oht_count_plan"` 추가  
→ `predictor.py`에서 `p.OHT_FIXED` 대신 `row["oht_count_plan"]` 사용

---

## 데이터 흐름 다이어그램

```
actuals.csv ──┐
              ├─→ data_loader.py ─→ actuals DataFrame ──→ model.py (fit) ──→ ModelParams
plan.csv ─────┘                 ─→ plan DataFrame ────┐
                                                       ├─→ predictor.py (predict) ──→ forecast DataFrame
                                                       └─ ModelParams ───────────────┘
                                                                                       │
                                                                          reporter.py (save_all)
                                                                                       │
                                                          ┌──────────────────────────────────────┐
                                                          │ param_report.txt  forecast.csv        │
                                                          │ warnings.txt      plot_*.png (5종)    │
                                                          └──────────────────────────────────────┘
```

---

## 주의사항 (수정 시 반드시 확인)

1. **혼잡도(cong) 순환 금지**: cong 계산에 move_time 포함하지 말 것
2. **표준화 순서**: move_time 회귀는 표준화→OLS→역변환 순서 유지
3. **β 유의성 판단**: storage_prod 2항 모델은 R² 2% 기준으로 자동 축소됨 (model.py 참고)
4. **단위 통일**: prod와 prod_plan은 반드시 같은 단위 사용
5. **LOOCV**: 표본이 36행 미만이면 LOOCV 결과가 불안정할 수 있음
