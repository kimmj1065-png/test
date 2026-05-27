"""
시나리오 분석 페이지
- 생산계획 ±% 변동 시 OHT/Storage 과부족 변화 시뮬레이션
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("🔮 시나리오 분석")
st.caption("생산계획 변동 시 OHT·Storage 과부족이 어떻게 달라지는지 시뮬레이션합니다.")

col1, col2 = st.columns(2)
site_filter = col1.text_input("Site", placeholder="Fab1")
plan_month = col2.text_input("기준 월 (YYYY-MM)", placeholder="2026-06")

delta_options = [-30, -20, -10, 0, 10, 20, 30]
selected_deltas = st.multiselect(
    "생산계획 변동 범위 (%)", delta_options, default=[-20, -10, 0, 10, 20]
)

if st.button("시뮬레이션 실행", type="primary"):
    if not plan_month:
        st.error("기준 월을 입력하세요.")
        st.stop()

    oht_rows = []
    stor_rows = []

    progress = st.progress(0)
    for i, delta in enumerate(selected_deltas):
        params = {
            "from_month": plan_month, "to_month": plan_month,
            "movement_delta": delta / 100,
        }
        if site_filter:
            params["site"] = site_filter

        try:
            oht_res = requests.get(f"{API}/capacity/oht", params=params, timeout=60)
            if oht_res.ok:
                for row in oht_res.json().get("floor_summary", []):
                    row["delta_pct"] = delta
                    oht_rows.append(row)

            stor_res = requests.get(f"{API}/capacity/storage", params=params, timeout=60)
            if stor_res.ok:
                for row in stor_res.json():
                    row["delta_pct"] = delta
                    stor_rows.append(row)
        except Exception as e:
            st.warning(f"delta={delta}% 오류: {e}")

        progress.progress((i + 1) / len(selected_deltas))

    if oht_rows:
        oht_df = pd.DataFrame(oht_rows)
        st.subheader("OHT 과부족 vs 생산계획 변동")

        floors = oht_df["floor"].unique().tolist()
        for fl in floors:
            grp = oht_df[oht_df["floor"] == fl].sort_values("delta_pct")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=grp["delta_pct"].astype(str) + "%",
                y=grp["oht_surplus_units"],
                marker_color=["#ef4444" if v < 0 else "#22c55e" for v in grp["oht_surplus_units"]],
                text=[f"{v:+.1f}대" for v in grp["oht_surplus_units"]],
                textposition="outside",
            ))
            fig.update_layout(
                title=f"Floor {fl} — 생산계획 변동별 OHT 과부족",
                xaxis_title="생산계획 변동(%)",
                yaxis_title="OHT 과부족(대)",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    if stor_rows:
        stor_df = pd.DataFrame(stor_rows)
        st.subheader("Storage 과부족 vs 생산계획 변동")

        for (line_v, floor_v), grp in stor_df.groupby(["line", "floor"]):
            grp = grp.sort_values("delta_pct")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=grp["delta_pct"].astype(str) + "%",
                y=grp["storage_surplus"],
                marker_color=["#ef4444" if v < 0 else "#22c55e" for v in grp["storage_surplus"]],
                text=[f"{v:+.0f}" for v in grp["storage_surplus"]],
                textposition="outside",
            ))
            fig.update_layout(
                title=f"Line {line_v} / Floor {floor_v} — Storage 과부족",
                xaxis_title="생산계획 변동(%)",
                yaxis_title="Storage 과부족(포트 수)",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
