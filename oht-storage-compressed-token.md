# OHT / Storage Capa 예측 모델 — 구현 플랜

## Context

반도체 팹 단일 라인(단일 DR)의 OHT 반송 및 Storage 점유를 월 단위로 예측하는
물리식 기반 모델을 구현한다. 학습 데이터가 52행(월 단위, 2022-01~2026-04)으로
매우 적고, 예측 구간이 학습 범위를 벗어나는 외삽이므로 ML 대신 **단계별 물리식
+ 소수 파라미터 회귀** 방식을 택한다. 목표 부하율 85%를 역산해 월별 필요 OHT
대수와 Storage 점유율을 불확실성 범위와 함께 산출한다.

---

## 디렉토리 구조 (완성 시)

```
/home/user/test/
├── oht_forecast/
│   ├── __init__.py         ← 완성
│   ├── constants.py        ← 완성 (모든 상수 정의)
│   ├── data_loader.py      ← 스켈레톤 작성됨, TODO 구현 필요
│   ├── fitting.py          ← 스켈레톤 작성됨, TODO 구현 필요
│   ├── prediction.py       ← 스켈레톤 작성됨, TODO 구현 필요
│   ├── validation.py       ← 스켈레톤 작성됨, TODO 구현 필요
│   ├── plotting.py         ← 스켈레톤 작성됨, TODO 구현 필요
│   ├── reporting.py        ← 스켈레톤 작성됨, TODO 구현 필요
│   └── main.py             ← 스켈레톤 작성됨, TODO 구현 필요
├── data/
│   ├── generate_sample_data.py  ← 완성 (합성 데이터 생성기)
│   ├── actuals.csv         ← generate_sample_data.py 실행 후 생성
│   └── plan.csv            ← generate_sample_data.py 실행 후 생성
├── output/                 ← 실행 후 자동 생성
│   ├── parameters.txt
│   ├── predictions.csv
│   ├── warnings.log
│   └── plots/
│       ├── move_qty_timeseries.png
│       ├── move_time_fit.png
│       ├── oht_required.png
│       ├── storage_occupancy.png
│       └── combined.png
└── requirements_oht.txt    ← 완성
```

---

## 구현 순서 (하위 에이전트용 우선순위)

### 1단계: 데이터 준비
```bash
pip install -r requirements_oht.txt
python data/generate_sample_data.py   # actuals.csv, plan.csv 생성
```

### 2단계: `data_loader.py` — `DataLoadError`, `load_actuals()`, `load_plan()`
```
입력: CSV 파일 경로
출력: month=Period(M), 숫자 컬럼=float64 DataFrame
검증: 컬럼 존재, 중복 month, NaN/Inf, lot_size/oht_count > 0
라이브러리: pandas
```

### 3단계: `fitting.py` (순서 중요 — 의존성 있음)

#### 3-1: `compute_congestion(move_qty, oht_count, T0) → np.ndarray`
```
cong = move_qty * T0 / (oht_count * 3600)
⚠ move_time 절대 포함하지 말 것 (순환 의존 방지)
```

#### 3-2: `fit_move_qty(df) → MoveQtyParams`
```
x = prod/lot_size, y = move_qty
원점 통과 OLS: k = (x·y)/(x·x)
절편 포함 OLS: sklearn LinearRegression
R² 차이 < 0.005 → 원점 선택
⚠ wip 변수 사용 금지
```

#### 3-3: `estimate_T0(df) → float`
```
util = move_qty * move_time / 3600 / oht_count
하위 LOWLOAD_N(=6)개월의 move_time 평균
⚠ LOOCV 각 fold에서 반드시 재계산 (train_df 기준)
```

#### 3-4: `fit_move_time(df) → MoveTimeParams`
```
T0 = estimate_T0(df)
cong = compute_congestion(...)
T_wait_obs = move_time - T0
curve_fit(lambda c,b: b*c/(1-c), cong[cong<1], T_wait_obs, bounds=(0,inf))
se_b = sqrt(pcov[0,0])
⚠ cong>=1 행 제외 후 fit (경고 로그)
```

#### 3-5: `fit_storage_prod(df, mt) → StorageProdParams`
```
cong = compute_congestion(..., T0=mt.T0)
X = [wip, wip*(cong/(1-cong))]  (N×2 설계행렬)
lstsq → α, β
β t-검정: p > 0.05 → β=0으로 축소, 경고 출력
⚠ wip은 이 함수에서만 사용
```

#### 3-6: `fit_storage_npw(df) → StorageNPWParams`
```
polyfit(move_qty, storage_npw, 1) → γ, δ
```

#### 3-7: `fit_all(df) → dict`
```
{'mq': MoveQtyParams, 'mt': MoveTimeParams,
 'sp': StorageProdParams, 'snpw': StorageNPWParams}
```

### 4단계: `prediction.py`

#### 4-1: `solve_oht(move_qty, T0, b, target_util) → dict`
```
초기값: oht = move_qty * T0 / 3600 / target_util
반복:
  cong = move_qty * T0 / (oht * 3600)
  if cong >= 1: oht *= 1.1, warn_saturation=True, continue
  mt = T0 + b * cong/(1-cong)
  oht_new = move_qty * mt / 3600 / target_util
  if |oht_new - oht| < CONVERGE_TOL: break
  oht = oht_new
반환: {oht_float, cong, move_time, converged, iterations, warn_saturation}
```

#### 4-2: `predict_month(row, mq, mt, sp, snpw) → (MonthForecast, OHTBand)`
```
move_qty = mq.k0 + mq.k * (prod_plan/lot_size_plan)  [wip_plan 사용 금지]
solve_oht 5회 호출: b, b±se_b, b±2*se_b → OHTBand
storage_prod = alpha*wip_plan + beta*wip_plan*(cong/(1-cong))
storage_npw  = gamma + delta*move_qty
occupancy = (storage_prod + storage_npw) / TOTAL_SLOT
경보 플래그: warn_saturation, warn_occupancy, extrapolation(cong>0.85)
```

#### 4-3: `predict(plan_df, ...) → (List[MonthForecast], List[OHTBand])`
```
plan_df 각 행에 predict_month 적용, 결과 리스트 반환
```

### 5단계: `validation.py`

#### 5-1: `loocv_report(df) → dict`
```
N=52 LOOCV (데이터 누수 방지 필수):
for i in range(N):
  train = df.drop(i)
  params = fit_all(train)          ← T0도 train 기준으로 재계산됨
  test = df.iloc[i]
  pred_mq = k0 + k*(prod/lot_size)  [wip 사용 금지]
  cong_test = pred_mq * T0 / (test.oht_count * 3600)  [실제 oht_count 사용]
  pred_mt = T0 + b*cong_test/(1-cong_test)
  pred_sp = alpha*test.wip + beta*test.wip*(cong_test/(1-cong_test))
  pred_snpw = gamma + delta*pred_mq
반환: {'move_qty': {'mape':%, 'rmse':}, 'move_time': {...}, ...}
```

#### 5-2: `sensitivity_analysis(df, mt, sp, mq_loocv_mape)` — 최근 12개월 대상
```
시나리오: b±1σ, b±2σ, move_qty×(1±MAPE%), T0×(1±5%), beta=0
각 시나리오별 oht_required 최대 변동폭(%) 반환
```

#### 5-3: `check_littles_law(plan_df)` — 경고 전용
```
|wip_plan - prod_plan*3| / (prod_plan*3) > 0.30 이면 경고 문자열 반환
```

### 6단계: `plotting.py` — 4개 함수 + `make_plots()`

| 함수 | 그래프 내용 |
|------|------------|
| `plot_move_qty` | 실적+예측 시계열, ±MAPE 밴드 |
| `plot_move_time_fit` | cong vs T_wait scatter + 적합곡선, cong>0.85 음영 |
| `plot_oht_required` | 막대그래프 + ±1σ/±2σ error bar |
| `plot_storage_occupancy` | 점유율 선그래프 + OCC_WARN 경보선 |

`make_plots()`: 개별 PNG + 2×2 combined.png 저장

### 7단계: `reporting.py` — 3개 함수 + `save_outputs()`
```
parameter_report() → parameters.txt 형식 문자열
save_predictions_csv() → predictions.csv
save_warnings_log() → warnings.log
save_outputs() → 위 3개 일괄 저장
```

### 8단계: `main.py` — `_collect_warnings()`, `_print_summary()`, `main()`
```
argparse: --actuals, --plan, --output, --no-plots, --loglevel
플로우: 로드→적합→LOOCV→민감도→예측→검산→경고→저장→그래프→요약
```

---

## 핵심 제약 (절대 위반 금지)

| 제약 | 위반 결과 |
|------|----------|
| `wip`/`wip_plan`을 `fit_move_qty`, `fit_move_time`, `solve_oht`에 사용 금지 | 물리 인과 역전 |
| `cong = move_qty * T0 / (oht * 3600)` — move_time 포함 금지 | 순환 의존 |
| LOOCV 각 fold에서 `estimate_T0(train_df)` 재계산 | 데이터 누수 |
| 모든 숫자 상수는 `constants.py`에서만 정의 | 하드코딩 금지 |

---

## 데이터클래스 인터페이스 요약

```python
# fitting.py
MoveQtyParams:    k, k0, use_intercept, r2_origin, r2_intercept, r2
MoveTimeParams:   T0, b, se_b, r2, n_valid
StorageProdParams: alpha, beta, beta_significant, r2
StorageNPWParams:  gamma, delta, r2

# prediction.py
MonthForecast:    month, move_qty, oht_required, oht_float, move_time, cong,
                  converged, iterations, storage_prod, storage_npw,
                  storage_total, occupancy,
                  warn_saturation, warn_occupancy, warn_convergence, extrapolation
OHTBand:          month, oht_central, oht_lo1, oht_hi1, oht_lo2, oht_hi2
```

---

## 엣지 케이스 처리 목록

| 상황 | 위치 | 처리 방법 |
|------|------|----------|
| `cong >= 1` (역산 중) | `solve_oht` | `oht *= 1.1`, `warn_saturation=True` |
| `CONVERGE_MAXIT` 초과 | `solve_oht` | 최선값 반환, `warn_convergence=True` |
| `b - se_b <= 0` (밴드 계산) | `predict_month` | `max(b-se_b, 1e-9)` 클램프 |
| β 유의하지 않음 | `fit_storage_prod` | β=0, 단변수 재적합, 경고 |
| `lot_size == 0` 또는 `oht_count == 0` | `load_actuals` | `DataLoadError` |
| 훈련 데이터 중복 month | `load_actuals` | `DataLoadError` |
| LOOCV 중 `fit_all` 실패 | `loocv_report` | WARNING 로그, 해당 fold 건너뜀 |
| `cong >= 1` (fit 중) | `fit_move_time` | 해당 행 제외, WARNING |
| `LOWLOAD_N` > 실제 행 수 | `estimate_T0` | 전체 행 사용, WARNING |

---

## 검증 방법 (구현 완료 후)

```bash
# 1. 패키지 설치
pip install -r requirements_oht.txt

# 2. 샘플 데이터 생성
python data/generate_sample_data.py

# 3. 모델 실행
python -m oht_forecast.main --actuals data/actuals.csv --plan data/plan.csv

# 4. 확인 항목
# - output/parameters.txt: k, T0, b(±se), α, β, γ, δ + R²/MAPE
# - output/predictions.csv: 미래 18개월 예측 테이블
# - output/warnings.log: 포화·외삽·점유·β비유의 경보
# - output/plots/combined.png: 4개 그래프

# 5. 품질 기준
# - move_qty LOOCV MAPE < 10%  (핵심 지표)
# - move_time fit R² > 0.80
# - 추정 파라미터가 generate_sample_data.py의 TRUE_* 값에 근접
#   (k≈0.28, T0≈55, b≈120, alpha≈0.55, beta≈0.003, gamma≈500, delta≈1.8)
```

---

## 알려진 한계 (parameters.txt에 포함 필수)

1. cong > 0.85 구간은 실측 없음 — 이론 외삽, 불확실성 범위로만 표현
2. 52행 월집계 — 복잡 모델 부적합, 단순 물리식 유지가 정합성에 유리
3. 단일 라인/단일 DR 가정 — 다중 DR 확장 시 그룹별 재적합 필요
4. 예측 품질은 입력 계획(생산·재공) 품질에 종속
