"""
전역 상수 정의 — 모든 파일은 이 모듈에서만 상수를 가져온다.
숫자 리터럴을 다른 파일에 직접 쓰지 않는다.
"""

# ── 시스템 구조 ─────────────────────────────────────────────────────────────
TOTAL_SLOT: int = 37_938          # Storage 총 슬롯 수 (고정, 변경 불가)

# ── 운용 목표 ─────────────────────────────────────────────────────────────
TARGET_UTIL: float = 0.85         # OHT 역산 기준 목표 부하율
OCC_WARN: float    = 0.85         # Storage 점유율 경보 임계값 (조정 가능: 0.85~0.90)

# ── T0 추정 ───────────────────────────────────────────────────────────────
LOWLOAD_N: int = 6                # T0 추정에 사용할 저부하 월 수

# ── 반복 수렴 ─────────────────────────────────────────────────────────────
CONVERGE_TOL: float  = 1e-3       # OHT 역산 수렴 허용오차 |oht_new - oht|
CONVERGE_MAXIT: int  = 100        # 역산 최대 반복 횟수

# ── 컬럼명 — 실적 파일(actuals.csv) ──────────────────────────────────────
COL_MONTH        = "month"
COL_PROD         = "prod"
COL_WIP          = "wip"
COL_LOT_SIZE     = "lot_size"
COL_MOVE_QTY     = "move_qty"
COL_MOVE_TIME    = "move_time"
COL_OHT_COUNT    = "oht_count"
COL_STORAGE_PROD = "storage_prod"
COL_STORAGE_NPW  = "storage_npw"

ACTUALS_COLS = [
    COL_MONTH, COL_PROD, COL_WIP, COL_LOT_SIZE,
    COL_MOVE_QTY, COL_MOVE_TIME, COL_OHT_COUNT,
    COL_STORAGE_PROD, COL_STORAGE_NPW,
]

# ── 컬럼명 — 계획 파일(plan.csv) ──────────────────────────────────────────
COL_PROD_PLAN     = "prod_plan"
COL_LOT_SIZE_PLAN = "lot_size_plan"
COL_WIP_PLAN      = "wip_plan"

PLAN_COLS = [COL_MONTH, COL_PROD_PLAN, COL_LOT_SIZE_PLAN, COL_WIP_PLAN]
