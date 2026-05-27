"""
계획/실적 Excel 업로드 + 모델 학습 페이지
"""
import streamlit as st
import requests
import pandas as pd

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("📂 데이터 업로드")

tab1, tab2, tab3 = st.tabs(["실적 업로드", "계획 업로드", "모델 학습"])

# ── 실적 업로드 ──────────────────────────────────────────
with tab1:
    st.subheader("월별 실적 업로드")
    st.markdown("""
    **필수 컬럼**: 사이트, 라인, 층, DR타입, 실적월
    **선택 컬럼**: 생산실적, 반송량실적, 반송시간실적, 저장량실적(product), 저장량실적(total), 투입계획
    ※ 투입계획은 이력 보관 용도로만 저장됩니다.
    """)

    col1, col2 = st.columns([3, 1])
    uploaded = col1.file_uploader("실적 Excel (.xlsx)", type=["xlsx"], key="actual_upload")

    with col2:
        st.write("")
        st.write("")
        try:
            res = requests.get(f"{API}/actuals/sample")
            st.download_button("샘플 양식 다운로드", res.content,
                               file_name="sample_actuals.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            st.caption("서버 연결 필요")

    if uploaded:
        res = requests.post(f"{API}/actuals/upload", files={"file": uploaded.getvalue()})
        if res.ok:
            st.success(f"업로드 완료: {res.json()['inserted']}건 저장")
        else:
            st.error(res.text)

    st.divider()
    st.subheader("저장된 실적 목록")
    try:
        data = requests.get(f"{API}/actuals/list").json()
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("실적 데이터 없음")
    except Exception:
        st.warning("API 서버에 연결할 수 없습니다.")

# ── 계획 업로드 ──────────────────────────────────────────
with tab2:
    st.subheader("월별 생산계획 업로드")
    st.markdown("""
    **필수 컬럼**: 사이트, 라인, 층, DR타입, 계획월, 생산계획
    **선택 컬럼**: 재공계획, LOT크기, NPW계획, 투입계획(이력)
    """)

    col1, col2 = st.columns([3, 1])
    plan_uploaded = col1.file_uploader("계획 Excel (.xlsx)", type=["xlsx"], key="plan_upload")

    with col2:
        st.write("")
        st.write("")
        try:
            res = requests.get(f"{API}/planning/sample")
            st.download_button("샘플 양식 다운로드", res.content,
                               file_name="sample_planning.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            st.caption("서버 연결 필요")

    if plan_uploaded:
        res = requests.post(f"{API}/planning/upload", files={"file": plan_uploaded.getvalue()})
        if res.ok:
            st.success(f"업로드 완료: {res.json()['inserted']}건 저장")
        else:
            st.error(res.text)

    st.divider()
    st.subheader("저장된 계획 목록")
    try:
        data = requests.get(f"{API}/planning/list").json()
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("계획 데이터 없음")
    except Exception:
        st.warning("API 서버에 연결할 수 없습니다.")

# ── 모델 학습 ────────────────────────────────────────────
with tab3:
    st.subheader("예측 모델 학습")
    st.markdown("""
    실적 데이터가 충분히 업로드된 후 학습을 실행하세요.
    - **Step 1 (생산량→movement)**: EWMA 가중 OLS
    - **Step 2 (movement→반송량)**: DR×라인별 EWMA OLS
    - **Step 3 (반송량→반송시간)**: 대기행렬 비선형 curve fitting
    - **Storage**: LightGBM (product FOUP)
    """)

    col1, col2 = st.columns(2)

    if col1.button("전체 모델 일괄 학습", type="primary", use_container_width=True):
        with st.spinner("학습 중..."):
            try:
                res = requests.post(f"{API}/models/train/all", timeout=120)
                if res.ok:
                    result = res.json()
                    st.success("학습 완료!")
                    st.json(result)
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(f"오류: {e}")

    if col2.button("Step 3 (반송시간) 개별 학습", use_container_width=True):
        with st.spinner("curve fitting 실행 중 (시간 소요)..."):
            try:
                res = requests.post(f"{API}/models/train/transport-time", timeout=300)
                if res.ok:
                    st.success("학습 완료!")
                    st.json(res.json())
                else:
                    st.error(res.text)
            except Exception as e:
                st.error(f"오류: {e}")

    st.divider()
    st.subheader("학습된 계수 확인")

    if st.button("반송시간 모델 계수 보기"):
        try:
            res = requests.get(f"{API}/models/coefficients/transport-time")
            if res.ok:
                data = res.json()
                rows = []
                for key, val in data.items():
                    row = {"key": key}
                    row.update(val)
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.error(res.text)
        except Exception as e:
            st.error(f"오류: {e}")
