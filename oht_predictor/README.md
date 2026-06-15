# OHT / Storage 예측 모델 — 사용 설명서 v2

반도체 팹 단일 라인의 **OHT 반송량·반송시간·부하율** 및 **Storage 점유율**을  
월 단위로 예측하는 물리식 기반 회귀 모델입니다.

---

## 목차

1. [빠른 시작](#1-빠른-시작)
2. [파일 구조](#2-파일-구조)
3. [실적 데이터 교체 방법 ★](#3-실적-데이터-교체-방법-)
4. [입력 파일 명세](#4-입력-파일-명세)
5. [모델 수식 설명](#5-모델-수식-설명)
6. [예측 단계 절차](#6-예측-단계-절차)
7. [산출물 설명](#7-산출물-설명)
8. [상수 조정 방법](#8-상수-조정-방법)
9. [명령줄 옵션](#9-명령줄-옵션)
10. [설계 원칙 / 한계](#10-설계-원칙--한계)

---

## 1. 빠른 시작

```bash
# 의존 패키지 설치 (최초 1회)
pip install numpy pandas matplotlib

# 샘플 데이터 생성 (처음 실행 또는 초기화할 때)
python generate_sample_data.py

# 예측 실행
python main.py
```

산출물은 `output/` 디렉터리에 저장됩니다.

---

## 2. 파일 구조

```
oht_predictor/
├── main.py                  ← 진입점 (여기서 실행)
├── constants.py             ← 전역 상수 (임계값 등)
├── data_loader.py           ← 데이터 로드 ★실적 교체 포인트★
├── model.py                 ← 회귀 모델 적합 (학습)
├── predictor.py             ← 월별 예측 실행
├── reporter.py              ← 산출물(CSV·그래프·리포트) 생성
├── generate_sample_data.py  ← 검증용 합성 데이터 생성기
├── sample_data/
│   ├── actuals.csv          ← 실적 데이터 (← 여기를 교체)
│   └── plan.csv             ← 생산 계획 데이터
└── output/                  ← 자동 생성됨
    ├── param_report.txt
    ├── forecast.csv
    ├── warnings.txt
    ├── plot_move_qty.png
    ├── plot_move_time.png
    ├── plot_scatter.png
    ├── plot_util.png
    └── plot_occupancy.png
```

---

## 3. 실적 데이터 교체 방법 ★

실적을 바꿀 때는 **3가지 방법** 중 하나를 선택합니다.

### 방법 A — CSV 파일 덮어쓰기 (가장 간단)

```
sample_data/actuals.csv  →  실제 데이터로 덮어쓰기
```
컬럼 형식은 [4절 입력 파일 명세](#4-입력-파일-명세)를 참고하세요.

### 방법 B — CLI 인자로 경로 지정

```bash
python main.py --actuals /your/path/real_actuals.csv
python main.py --actuals /your/path/real_actuals.csv --plan /your/path/real_plan.csv
```

### 방법 C — `data_loader.py` 내부를 DB·API 조회로 교체 (고급)

`data_loader.py`의 `load_actuals()` 함수만 수정하면 됩니다.  
반환 형식(아래 컬럼 보유 + month 오름차순)만 지키면 나머지 코드는 그대로 동작합니다.

```python
# data_loader.py  예시 — DB 조회로 교체
def load_actuals(path=None) -> pd.DataFrame:
    conn = get_db_connection()        # 사내 DB 연결
    df = pd.read_sql("SELECT ...", conn)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m")
    return df.sort_values("month").reset_index(drop=True)
```

---

## 4. 입력 파일 명세

### 4-1. actuals.csv — 실적 (학습용, 권장 36행 이상)

| 컬럼 | 단위 | 설명 | 예시 |
|------|------|------|------|
| `month` | YYYY-MM | 연월 인덱스 | 2023-01 |
| `prod` | — | 생산량 (웨이퍼·로트 등, plan과 동일 단위) | 138500 |
| `wip` | — | 월말 재공 (prod 와 동일 단위 기준) | 39000 |
| `lot_size` | — | 평균 lot size | 25.0 |
| `move_qty` | 회/hr | OHT 시간당 반송량 | 387.4 |
| `move_time` | 초 | 평균 반송시간 | 192.6 |
| `load_dist` | mm | 평균 load 반송거리 | 19850 |
| `oht_count` | 대 | OHT 투입 대수 | 58 |
| `storage_prod` | 캐리어 | 생산 FOUP 저장량 | 18200 |
| `storage_npw` | 캐리어 | 비생산(NPW/Empty) FOUP 저장량 | 5650 |

> **주의**: `month`는 `YYYY-MM` 형식 문자열, 나머지는 모두 숫자입니다.  
> 결측값(NaN) 행이 있으면 해당 월은 학습에서 자동 제외됩니다.

### 4-2. plan.csv — 생산 계획 (예측용)

| 컬럼 | 단위 | 설명 |
|------|------|------|
| `month` | YYYY-MM | 예측 대상 연월 |
| `prod_plan` | — | 생산 계획 (actuals.prod 와 동일 단위) |
| `lot_size_plan` | — | 계획 lot size |
| `wip_plan` | — | 예상 재공 |

> **참고**: OHT 대수(`oht_count`)와 load 거리(`load_dist`)는 plan에 없어도 됩니다.  
> - `oht_count` → 학습 데이터 마지막 달 실적으로 자동 고정 (`OHT_FIXED`)  
> - `load_dist` → 과거 평균값(`load_const`)으로 자동 대체

---

## 5. 모델 수식 설명

### 수식 ① — 반송량

```
move_qty = k · (prod / lot_size)
```

- **k**: 단위 생산 당 반송 횟수 (절편 없는 최소제곱으로 추정)
- 의미: 생산량을 lot으로 나눈 값(착공 수)에 비례해 반송이 발생

### 수식 ② — 반송시간 (핵심)

```
move_time = t0 + v_load · load_dist + b · cong / (1 − cong)
```

**혼잡도(cong) 정의** — 순환 참조 차단:
```
cong = move_qty · T0_ref / (oht_count · 3600)
```
- `T0_ref`: 저부하 월 상위 `LOWLOAD_N`개의 `move_time` 평균 (기준 이동시간)
- `cong < 1`: 정상 운영 / `cong ≥ 1`: 물리적 포화 (OHT 수용 초과)

**표준화 후 OLS — 역변환 순서**:
1. `X1 = load_dist`, `X2 = cong/(1−cong)`를 각각 표준화 → `X1ⁿ, X2ⁿ`
2. 타깃 `move_time`도 표준화 → `yⁿ`
3. 표준화 공간에서 절편 없는 OLS: `yⁿ = β1·X1ⁿ + β2·X2ⁿ`
4. 원단위 역변환:
   - `v_load = β1 · σ(y) / σ(X1)`
   - `b      = β2 · σ(y) / σ(X2)`
   - `t0     = μ(y) − v_load·μ(X1) − b·μ(X2)`

> `t0`이 음수일 수 있습니다 — 데이터 범위 밖 외삽점이므로 정상입니다.

### 수식 ③ — 생산 FOUP 저장량

```
storage_prod = α · wip + β · wip · cong/(1−cong)
```

- β의 R² 기여가 2% 미만이면 단순 모델(`β=0`)로 자동 축소
- 의미: 재공이 많고 혼잡할수록 대기 FOUP이 증가

### 수식 ④ — 비생산 FOUP 저장량

```
storage_npw = γ + δ · move_qty
```

### 합산

```
storage_total = storage_prod + storage_npw
occupancy     = storage_total / TOTAL_SLOT
util          = move_qty · move_time / 3600 / OHT_FIXED
```

---

## 6. 예측 단계 절차

각 미래 월에 대해 다음 순서로 계산합니다:

```
입력값: prod_plan, lot_size_plan, wip_plan (plan.csv)
고정값: OHT_FIXED (학습 마지막 달 oht_count)
        load_const (과거 load_dist 평균)
        T0_ref, k, t0, v_load, b, α, β, γ, δ (학습 결과)

Step 1  move_qty  = k · (prod_plan / lot_size_plan)

Step 2  cong      = move_qty · T0_ref / (OHT_FIXED · 3600)
        [경보] cong ≥ 1 → 포화 경보 발생
        move_time = t0 + v_load · load_const + b · cong/(1−cong)
        util      = move_qty · move_time / 3600 / OHT_FIXED

Step 3  storage_prod  = α · wip_plan [+ β · wip_plan · cong/(1−cong)]
        storage_npw   = γ + δ · move_qty
        storage_total = storage_prod + storage_npw
        occupancy     = storage_total / TOTAL_SLOT

Step 4  불확실성 밴드 (±SENS_Z·σ):
          move_time_lo/hi → b ± SENS_Z·se_b, load_const ± SENS_Z·σ(load)
          util_lo/hi      → move_time_lo/hi 적용

Step 5  경보 플래그
          포화경보  : cong ≥ 1
          부하율경보: util ≥ UTIL_WARN     (OHT 증설 신호)
          외삽여부  : cong > 0.78          (과거 최대 초과)
          점유경보  : occupancy ≥ OCC_WARN
```

---

## 7. 산출물 설명

### param_report.txt

모델 파라미터 전체와 적합도(R², MAPE LOOCV)를 텍스트로 정리합니다.

```
■ 반송량  move_qty = k · (prod / lot_size)
    k            = 0.070021
    R²           = 0.9232
    MAPE(LOOCV)  = 1.96%
...
```

### forecast.csv

| 컬럼 | 설명 |
|------|------|
| `month` | 예측 연월 |
| `move_qty` | 예측 반송량 (회/hr) |
| `move_time` | 예측 반송시간 (초) |
| `move_time_lo/hi` | 불확실성 하한/상한 |
| `util` | 예측 부하율 |
| `util_lo/hi` | 부하율 불확실성 하한/상한 |
| `cong` | 혼잡도 |
| `storage_prod` | 생산 FOUP 저장량 |
| `storage_npw` | 비생산 FOUP 저장량 |
| `storage_total` | 총 저장량 |
| `occupancy` | Storage 점유율 |
| `포화경보` | True/False |
| `부하율경보` | True/False (OHT 증설 신호) |
| `외삽여부` | True/False (예측 신뢰도 주의) |
| `점유경보` | True/False |

### warnings.txt

경보가 발생한 월을 요약합니다.

```
[경고 로그]

  util ≥ 0.85  [OHT 증설 신호]
    해당 월: 2025-01, 2025-02
```

### 그래프 5종

| 파일 | 내용 |
|------|------|
| `plot_move_qty.png` | 반송량 실적+예측 시계열 |
| `plot_move_time.png` | 반송시간 시계열 + ±1σ 불확실성 밴드 (외삽 구간 음영) |
| `plot_scatter.png` | move_time 실측 vs 예측 산점도 (y=x 직선) |
| `plot_util.png` | 부하율 시계열 + 경보선 (0.85) |
| `plot_occupancy.png` | Storage 점유율 시계열 + 경보선 (85%) |

---

## 8. 상수 조정 방법

`constants.py` 파일을 열어 아래 값을 수정합니다.

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `TOTAL_SLOT` | 37938 | Storage 총 슬롯 수 (설비 변경 시 수정) |
| `OCC_WARN` | 0.85 | Storage 점유율 경보 임계 |
| `UTIL_WARN` | 0.85 | 부하율 경보 임계 (OHT 증설 판단 기준) |
| `LOWLOAD_N` | 6 | T0_ref 산정용 저부하 월 수 |
| `LOAD_CONST_MODE` | `"recent"` | `"all"` = 전체 평균, `"recent"` = 최근 N개월 평균 |
| `LOAD_CONST_WIN` | 12 | `LOAD_CONST_MODE="recent"` 시 참조 월 수 |
| `SENS_Z` | 1.0 | 불확실성 밴드 배수 (2.0으로 바꾸면 ±2σ) |

---

## 9. 명령줄 옵션

```bash
python main.py [--actuals <경로>] [--plan <경로>]

옵션:
  --actuals   실적 CSV 경로 (생략 시 sample_data/actuals.csv)
  --plan      계획 CSV 경로 (생략 시 sample_data/plan.csv)

예시:
  python main.py --actuals /data/fab_actual_2024.csv
  python main.py --actuals /data/fab_actual.csv --plan /data/2025_plan.csv
```

---

## 10. 설계 원칙 / 한계

### 설계 원칙

| 원칙 | 내용 |
|------|------|
| **물리식 기반** | 순수 데이터 ML 대신 물리 모델에 소수 파라미터 회귀 → 소표본(52행)에서도 안정적 |
| **순환 의존 차단** | 혼잡도(cong)를 move_time 없이 정의 → 연립방정식 회피 |
| **표준화 필수** | load_dist(mm 단위)의 절대값이 커 표준화 없으면 회귀 계수가 수치 불안정 |
| **OHT 고정** | 미래 OHT 대수 변경 없다고 가정 → 부하율 상승 추이로 증설 시점 도출 |
| **LOOCV 평가** | 소표본 과적합 방지를 위해 Leave-One-Out Cross-Validation MAPE 사용 |

### 한계 및 주의사항

- **표본 크기**: 권장 36행 이상. 36행 미만이면 LOOCV 결과가 불안정할 수 있습니다.
- **외삽 구간** (`cong > 0.78`): 과거 실측 없는 혼잡도 구간으로, 예측 불확실성이 급증합니다. 이 구간의 결과는 방향성 참고에만 사용하세요.
- **OHT 대수 변경 시나리오**: 미래에 OHT를 증설할 계획이 있다면, `OHT_FIXED`를 수동으로 변경하거나 plan.csv에 `oht_count_plan` 컬럼을 추가해 `predictor.py`를 수정해야 합니다.
- **load_dist 변동**: 공정 레이아웃이 크게 바뀌면 `load_const`가 더 이상 유효하지 않습니다. 이 경우 plan.csv에 `load_dist_plan` 컬럼을 추가하고 predictor.py를 수정하세요.
- **계절성**: 현재 모델은 계절성을 명시적으로 모델링하지 않습니다. 계획 데이터(wip_plan, prod_plan)에 계절 패턴이 반영되어 있다면 자연스럽게 반영됩니다.
