# ── 모델 전역 상수 ────────────────────────────────────────────────────────────
# 이 파일만 바꾸면 임계값/운영 파라미터를 일괄 변경할 수 있습니다.

TOTAL_SLOT       = 37938   # Storage 총 슬롯 수 (설비 고정값)
OCC_WARN         = 0.85    # Storage 점유율 경보 임계
UTIL_WARN        = 0.85    # OHT 부하율 경보 임계 (≥ → 증설 신호)
LOWLOAD_N        = 6       # T0_ref 추정용 저부하 월 개수
LOAD_CONST_MODE  = "recent"  # "all"=전체 평균 / "recent"=최근 N개월 평균
LOAD_CONST_WIN   = 12      # LOAD_CONST_MODE="recent" 시 참조 월 수
SENS_Z           = 1.0     # 불확실성 밴드 배수 (1.0 = ±1σ, 2.0 = ±2σ)
