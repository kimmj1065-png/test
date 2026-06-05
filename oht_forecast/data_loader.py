"""
CSV 데이터 로드 및 검증 모듈

책임:
  - actuals.csv, plan.csv를 읽어 정제된 DataFrame 반환
  - 컬럼 존재 여부, 자료형, 결측치, 중복 month 등 입력 품질 보장
  - 이 모듈 이후에는 NaN/Inf/음수/0-division 위험이 없다고 가정할 수 있어야 한다
"""

import pandas as pd
import logging
from oht_forecast.constants import ACTUALS_COLS, PLAN_COLS, COL_MONTH

logger = logging.getLogger(__name__)


class DataLoadError(ValueError):
    """입력 데이터 품질 문제"""


def load_actuals(path: str) -> pd.DataFrame:
    """
    actuals.csv를 읽어 정제된 DataFrame을 반환한다.

    반환 DataFrame 규격:
      - index: RangeIndex(0..N-1), month 기준 오름차순 정렬
      - 'month' 컬럼: pd.Period(freq='M') dtype
      - 나머지 컬럼: float64
      - 결측치 없음, 중복 month 없음
      - lot_size > 0, oht_count > 0 (0-division 방지)

    Args:
        path: actuals.csv 파일 경로

    Returns:
        pd.DataFrame with columns ACTUALS_COLS

    Raises:
        DataLoadError: 필수 컬럼 누락, 중복 month, 결측치, 또는 0-division 위험 시
        FileNotFoundError: 파일이 없을 때
    """
    # TODO: 구현
    # Step 1: pd.read_csv(path) 로 로드
    # Step 2: 필수 컬럼 검증 → set(ACTUALS_COLS) - set(df.columns) 비어있는지 확인
    # Step 3: month 파싱 → pd.to_datetime(df['month']).dt.to_period('M')
    #         - '2022-01', '2022/01', Excel integer 등 다양한 포맷 지원
    #         - pd.to_datetime 실패 시 DataLoadError
    # Step 4: month 중복 검사 → df['month'].duplicated().any() → DataLoadError
    # Step 5: month 기준 오름차순 정렬, index reset
    # Step 6: 숫자 컬럼 float64 캐스팅
    # Step 7: NaN/Inf 검사 → any row with non-finite values → DataLoadError
    # Step 8: lot_size > 0, oht_count > 0 검사 → DataLoadError
    # Step 9: 경고 로그: 52행이 아닐 때 (모델은 계속 실행)
    raise NotImplementedError


def load_plan(path: str) -> pd.DataFrame:
    """
    plan.csv를 읽어 정제된 DataFrame을 반환한다.

    반환 DataFrame 규격:
      - index: RangeIndex(0..N-1), month 기준 오름차순 정렬
      - 'month' 컬럼: pd.Period(freq='M') dtype
      - 나머지 컬럼: float64
      - lot_size_plan > 0
      - actuals의 가장 마지막 month 이후여야 함 (검사는 main.py 에서)

    Args:
        path: plan.csv 파일 경로

    Returns:
        pd.DataFrame with columns PLAN_COLS

    Raises:
        DataLoadError: 필수 컬럼 누락, lot_size_plan=0, 결측치 시
    """
    # TODO: load_actuals와 동일한 패턴, PLAN_COLS 기준으로 검증
    # lot_size_plan > 0, prod_plan > 0, wip_plan > 0 검사 추가
    raise NotImplementedError
