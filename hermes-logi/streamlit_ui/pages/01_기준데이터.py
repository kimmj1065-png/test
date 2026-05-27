"""
기준 데이터 설정 페이지
- OHT 대수 (site, floor 단위)
- Storage 용량 (site, line, floor 단위)
- DR별 공정 step 수
"""
import streamlit as st
import requests
import pandas as pd

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("⚙️ 기준 데이터 설정")

tab1, tab2, tab3 = st.tabs(["OHT 대수", "Storage 용량", "DR Step 수"])

# ── OHT 대수 ────────────────────────────────────────────
with tab1:
    st.subheader("OHT 대수 (floor 단위)")
    st.caption("하나의 floor에 여러 라인이 있어도 OHT는 floor 단위로 등록합니다.")

    with st.form("oht_form"):
        col1, col2, col3 = st.columns(3)
        site = col1.text_input("Site", placeholder="Fab1")
        floor = col2.text_input("Floor", placeholder="F2")
        line = col3.text_input("Line (해당 floor의 라인 중 하나)", placeholder="L1")
        col4, col5 = st.columns(2)
        oht_count = col4.number_input("OHT 대수", min_value=1, value=30)
        oht_hours = col5.number_input("대당 월 가동시간 (h)", min_value=1.0, value=720.0)
        submitted = st.form_submit_button("저장")

    if submitted and site and floor and line:
        res = requests.post(f"{API}/reference/floor-config", json={
            "site": site, "floor": floor, "line": line,
            "oht_count": oht_count, "oht_monthly_hours": oht_hours,
        })
        if res.ok:
            st.success("저장 완료")
        else:
            st.error(res.text)

    try:
        data = requests.get(f"{API}/reference/floor-config").json()
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
    except Exception:
        st.warning("API 서버에 연결할 수 없습니다.")

# ── Storage 용량 ─────────────────────────────────────────
with tab2:
    st.subheader("Storage 용량 (line 단위)")

    with st.form("storage_form"):
        col1, col2, col3 = st.columns(3)
        s_site = col1.text_input("Site", key="s_site", placeholder="Fab1")
        s_line = col2.text_input("Line", key="s_line", placeholder="L1")
        s_floor = col3.text_input("Floor", key="s_floor", placeholder="F2")
        s_cap = st.number_input("Storage 용량 (FOUP 포트 수)", min_value=1, value=5000)
        s_submitted = st.form_submit_button("저장")

    if s_submitted and s_site and s_line and s_floor:
        res = requests.post(f"{API}/reference/storage-config", json={
            "site": s_site, "line": s_line, "floor": s_floor,
            "storage_capacity": s_cap,
        })
        st.success("저장 완료") if res.ok else st.error(res.text)

    try:
        data = requests.get(f"{API}/reference/storage-config").json()
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
    except Exception:
        st.warning("API 서버에 연결할 수 없습니다.")

# ── DR Step 수 ───────────────────────────────────────────
with tab3:
    st.subheader("DR별 공정 Step 수")
    st.caption("DR 타입마다 공정 step 수가 다를 경우 반송량 예측 정확도에 영향을 줍니다.")

    with st.form("dr_form"):
        dr_type = st.text_input("DR 타입", placeholder="DRAM_1a")
        step_count = st.number_input("Step 수", min_value=1, value=300)
        dr_submitted = st.form_submit_button("저장")

    if dr_submitted and dr_type:
        res = requests.post(f"{API}/reference/dr-steps", json={
            "dr_type": dr_type, "step_count": step_count,
        })
        st.success("저장 완료") if res.ok else st.error(res.text)

    try:
        data = requests.get(f"{API}/reference/dr-steps").json()
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
    except Exception:
        st.warning("API 서버에 연결할 수 없습니다.")
