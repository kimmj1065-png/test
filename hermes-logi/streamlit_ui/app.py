"""
Hermes-Logi Streamlit 메인
실행: streamlit run streamlit_ui/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Hermes-Logi | OHT·Storage Capa 분석",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Hermes-Logi — 물류 중장기 Capa 분석 시스템")
st.markdown("""
### 사용 순서
1. **사이드바 → 기준 데이터 설정** : OHT 대수, Storage 용량, DR별 Step 수 입력
2. **실적 업로드** : 2년치 월별 실적 Excel 업로드 → 모델 학습
3. **계획 업로드** : 예측 대상 월별 생산계획 Excel 업로드
4. **OHT Capa** / **Storage Capa** 탭에서 과부족 시각화
5. **시나리오 분석** 탭에서 생산계획 변동 시뮬레이션

---
""")

st.info("왼쪽 사이드바의 페이지를 선택하세요.")
