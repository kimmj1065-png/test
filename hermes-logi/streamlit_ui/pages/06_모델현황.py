"""
모델 현황 페이지
- 학습된 계수 시각화
- MAPE, R² 정확도 지표
- 변곡점 감지 경고
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API = st.secrets.get("API_URL", "http://localhost:8000")

st.title("📊 모델 현황")

tab1, tab2 = st.tabs(["반송시간 모델 (대기행렬)", "반송량 모델 계수"])

with tab1:
    st.subheader("Step 3: 반송시간 모델 파라미터 (base_time, a_line)")
    st.markdown("""
    - **base_time**: 혼잡 없는 이상적 반송시간 (초). 값이 낮을수록 OHT 이동 효율 높음.
    - **a_line**: 혼잡 민감도 계수. 값이 클수록 부하율 상승 시 반송시간 급증.
    - **R²**: 모델 적합도 (1에 가까울수록 정확).
    """)

    try:
        res = requests.get(f"{API}/models/coefficients/transport-time")
        if res.ok:
            data = res.json()
            rows = []
            for key_str, val in data.items():
                row = {"모델 키": key_str}
                row["base_time (초)"] = val.get("base_time")
                row["a_line"] = val.get("a_line")
                row["R²"] = val.get("r2")
                row["데이터 수"] = val.get("n")
                row["Fallback여부"] = val.get("fallback", False)
                rows.append(row)
            df = pd.DataFrame(rows)

            # 경고: a_line이 크거나 fallback인 경우
            warns = df[df["Fallback여부"] == True]
            if not warns.empty:
                st.warning(f"⚠️ Fallback(선형) 사용 중인 모델: {warns['모델 키'].tolist()}")

            high_a = df[df["a_line"].notna() & (df["a_line"] > 2.0)]
            if not high_a.empty:
                st.warning(f"⚠️ 혼잡 민감도(a_line) 높음 — 부하율 증가 시 반송시간 급증 위험: {high_a['모델 키'].tolist()}")

            st.dataframe(
                df.style.format({
                    "base_time (초)": "{:.1f}",
                    "a_line": "{:.3f}",
                    "R²": "{:.4f}",
                }),
                use_container_width=True,
            )

            # base_time 바차트
            valid = df[df["base_time (초)"].notna()]
            if not valid.empty:
                fig = go.Figure(go.Bar(
                    x=valid["모델 키"], y=valid["base_time (초)"],
                    marker_color="#3b82f6",
                ))
                fig.update_layout(title="라인별 base_time 비교", height=300)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("모델이 아직 학습되지 않았습니다. '데이터 업로드' 페이지에서 학습을 실행하세요.")
    except Exception as e:
        st.error(f"오류: {e}")

with tab2:
    st.subheader("Step 1: 생산량→movement 모델 계수")

    try:
        res = requests.get(f"{API}/models/coefficients/movement")
        if res.ok:
            data = res.json()
            rows = [{"모델 키": k, "계수(coef)": v.get("coef"), "절편": v.get("intercept"),
                     "R²": v.get("r2"), "변곡점 감지": v.get("breakpoint_detected")} for k, v in data.items()]
            df = pd.DataFrame(rows)

            bp_rows = df[df["변곡점 감지"] == True]
            if not bp_rows.empty:
                st.warning(
                    f"⚠️ 변곡점 감지됨 (증산/감산 이력): {bp_rows['모델 키'].tolist()}\n"
                    "→ 최근 데이터만 사용하여 계수를 재추정했습니다."
                )

            st.dataframe(
                df.style.format({"계수(coef)": "{:.4f}", "절편": "{:.1f}", "R²": "{:.4f}"}),
                use_container_width=True,
            )
        else:
            st.info("모델이 아직 학습되지 않았습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
