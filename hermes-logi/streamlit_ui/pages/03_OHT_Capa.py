"""
OHT Capa 과부족 시각화 페이지
- Floor 단위 집계 (같은 floor의 여러 라인 합산)
- 월별 바차트 + 부하율 라인
- Floor 내 라인별 기여 파이차트
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("🚛 OHT Capa 과부족 분석")

# ── 필터 ─────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
site_filter = col1.text_input("Site 필터 (비워두면 전체)", placeholder="Fab1")
from_month = col2.text_input("시작월 (YYYY-MM)", placeholder="2026-01")
to_month = col3.text_input("종료월 (YYYY-MM)", placeholder="2026-12")

if st.button("조회", type="primary"):
    params = {}
    if site_filter:
        params["site"] = site_filter
    if from_month:
        params["from_month"] = from_month
    if to_month:
        params["to_month"] = to_month

    try:
        res = requests.get(f"{API}/capacity/oht", params=params, timeout=60)
    except Exception as e:
        st.error(f"API 연결 오류: {e}")
        st.stop()

    if not res.ok:
        st.error(res.text)
        st.stop()

    data = res.json()
    floor_df = pd.DataFrame(data["floor_summary"])
    line_df = pd.DataFrame(data["line_detail"])

    if floor_df.empty:
        st.warning("조회된 데이터가 없습니다.")
        st.stop()

    # ── 월별 과부족 바차트 ──────────────────────────────
    st.subheader("Floor별 OHT 과부족 (월별)")

    floors = floor_df["floor"].unique().tolist()
    selected_floor = st.selectbox("Floor 선택", ["전체"] + floors)

    plot_df = floor_df if selected_floor == "전체" else floor_df[floor_df["floor"] == selected_floor]

    fig = go.Figure()

    for floor_name, grp in plot_df.groupby("floor"):
        grp = grp.sort_values("plan_month")
        color = ["#ef4444" if v < 0 else "#22c55e" for v in grp["oht_surplus_units"]]

        fig.add_trace(go.Bar(
            name=f"{floor_name} 과부족(대)",
            x=grp["plan_month"],
            y=grp["oht_surplus_units"],
            marker_color=color,
            text=[f"{v:+.1f}대" for v in grp["oht_surplus_units"]],
            textposition="outside",
        ))

        fig.add_trace(go.Scatter(
            name=f"{floor_name} 부하율",
            x=grp["plan_month"],
            y=grp["utilization_rate"] * 100,
            yaxis="y2",
            mode="lines+markers",
            line=dict(dash="dot"),
        ))

    fig.update_layout(
        title="OHT 과부족(대) 및 부하율(%)",
        yaxis=dict(title="과부족 대수"),
        yaxis2=dict(title="부하율 (%)", overlaying="y", side="right", range=[0, 120]),
        barmode="group",
        height=450,
        legend=dict(orientation="h", y=-0.2),
        shapes=[dict(
            type="line", xref="paper", x0=0, x1=1,
            yref="y2", y0=85, y1=85,
            line=dict(color="orange", dash="dash", width=2),
        )],
        annotations=[dict(
            x=1, y=85, xref="paper", yref="y2",
            text="부하율 85% 경계", showarrow=False, font=dict(color="orange"),
        )],
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 라인별 기여 파이차트 ─────────────────────────────
    st.subheader("Floor 내 라인별 OHT 수요 기여")

    months = line_df["plan_month"].unique().tolist()
    sel_month = st.selectbox("월 선택", sorted(months))
    sel_floor2 = st.selectbox("Floor 선택 (파이차트)", floors, key="pie_floor")

    pie_df = line_df[
        (line_df["plan_month"] == sel_month) & (line_df["floor"] == sel_floor2)
    ]
    if not pie_df.empty:
        agg = pie_df.groupby("line")["required_oht_hours"].sum().reset_index()
        fig2 = px.pie(agg, names="line", values="required_oht_hours",
                      title=f"{sel_floor2} / {sel_month} 라인별 OHT 수요 기여")
        st.plotly_chart(fig2, use_container_width=True)

    # ── 수치 테이블 ──────────────────────────────────────
    with st.expander("상세 수치 보기"):
        cols_to_show = [
            "site", "floor", "plan_month", "oht_count", "available_oht_hours",
            "required_oht_hours", "oht_surplus_hours", "oht_surplus_units", "utilization_rate",
        ]
        show_cols = [c for c in cols_to_show if c in floor_df.columns]
        st.dataframe(
            floor_df[show_cols].style.format({
                "available_oht_hours": "{:.0f}h",
                "required_oht_hours": "{:.0f}h",
                "oht_surplus_hours": "{:+.0f}h",
                "oht_surplus_units": "{:+.1f}대",
                "utilization_rate": "{:.1%}",
            }),
            use_container_width=True,
        )
