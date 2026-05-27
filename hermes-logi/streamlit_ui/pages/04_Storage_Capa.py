"""
Storage Capa 과부족 시각화 페이지
- (site, line, floor) 단위
- Product / Non-product 스택 바 차트
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("📦 Storage Capa 과부족 분석")

col1, col2, col3 = st.columns(3)
site_filter = col1.text_input("Site 필터", placeholder="Fab1")
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
        res = requests.get(f"{API}/capacity/storage", params=params, timeout=60)
    except Exception as e:
        st.error(f"API 연결 오류: {e}")
        st.stop()

    if not res.ok:
        st.error(res.text)
        st.stop()

    df = pd.DataFrame(res.json())
    if df.empty:
        st.warning("조회된 데이터가 없습니다.")
        st.stop()

    lines = df["line"].unique().tolist()
    selected_line = st.selectbox("라인 선택", ["전체"] + lines)

    plot_df = df if selected_line == "전체" else df[df["line"] == selected_line]

    # ── 스택 바 차트: product + non_product vs capacity ──
    st.subheader("월별 Storage 사용 예측 (Product / Non-Product 구분)")

    for (site_v, line_v, floor_v), grp in plot_df.groupby(["site", "line", "floor"]):
        grp = grp.sort_values("plan_month")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Product FOUP",
            x=grp["plan_month"],
            y=grp["product_storage_pred"],
            marker_color="#3b82f6",
        ))
        fig.add_trace(go.Bar(
            name="Non-product (NPW+Empty)",
            x=grp["plan_month"],
            y=grp["non_product_storage_pred"],
            marker_color="#93c5fd",
        ))

        if "storage_capacity" in grp.columns:
            fig.add_trace(go.Scatter(
                name="Storage 용량",
                x=grp["plan_month"],
                y=grp["storage_capacity"],
                mode="lines",
                line=dict(color="red", dash="dash", width=2),
            ))

        fig.update_layout(
            title=f"{site_v} / {line_v} / {floor_v}",
            barmode="stack",
            yaxis_title="FOUP 포트 수",
            height=400,
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 과부족 바
        fig2 = go.Figure()
        colors = ["#ef4444" if v < 0 else "#22c55e" for v in grp["storage_surplus"]]
        fig2.add_trace(go.Bar(
            name="Storage 과부족",
            x=grp["plan_month"],
            y=grp["storage_surplus"],
            marker_color=colors,
            text=[f"{v:+.0f}" for v in grp["storage_surplus"]],
            textposition="outside",
        ))
        fig2.update_layout(
            title=f"{site_v} / {line_v} 과부족 (양수=여유, 음수=부족)",
            yaxis_title="포트 수",
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("상세 수치 보기"):
        show_cols = [
            "site", "line", "floor", "plan_month",
            "product_storage_pred", "non_product_storage_pred", "total_storage_pred",
            "storage_capacity", "storage_surplus", "storage_utilization",
        ]
        show_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(
            df[show_cols].style.format({
                "product_storage_pred": "{:.0f}",
                "non_product_storage_pred": "{:.0f}",
                "total_storage_pred": "{:.0f}",
                "storage_capacity": "{:.0f}",
                "storage_surplus": "{:+.0f}",
                "storage_utilization": "{:.1%}",
            }),
            use_container_width=True,
        )
