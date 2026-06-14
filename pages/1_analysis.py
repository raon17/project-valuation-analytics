import streamlit as st
import numpy as np
from core.data import get_ticker_data
from core.quality import run_quality, score_quality

st.set_page_config(page_title="VMI Analysis", layout="wide")
st.title("VMI Analysis")

# ── Input ─────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    ticker = st.text_input("Ticker", placeholder="AAPL").upper().strip()
with col2:
    proj_years = st.selectbox("Projection Years", [5, 7, 10], index=0)
with col3:
    discount_rate = st.slider("Discount Rate (%)", 8, 15, 10) / 100

run = st.button("Run Analysis", type="primary")

if not ticker or not run:
    st.stop()

# ── Fetch ─────────────────────────────────────────────────────────────────────
with st.spinner(f"Fetching {ticker}..."):
    try:
        data = get_ticker_data(ticker)
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

current_price = data["info"].get("currentPrice") or data["info"].get("regularMarketPrice")
company_name  = data["info"].get("longName", ticker)

st.subheader(f"{company_name} ({ticker})")
if current_price:
    st.metric("Current Price", f"${current_price:,.2f}")

st.divider()

# ── Section 1: Business Quality ───────────────────────────────────────────────
st.header("① Business Quality Test")

with st.expander("📖 Business Quality란?", expanded=False):
    st.markdown("""
    Adam Khoo VMI의 **첫 번째 필터**. 이 테스트를 통과하지 못하면 아무리 싸도 투자 대상에서 제외.

    핵심 질문: *"이 기업은 경쟁 해자가 있고, 꾸준히 성장하며, 재무적으로 건강한가?"*

    - **성장성**: 매출·이익·FCF가 최소 10%/년으로 증가하고 있는가
    - **수익성**: 마진이 업종 내에서 높은 편인가 (Gross 40%, Net 10%)
    - **효율성**: ROE 15%, ROIC 12% — 자본을 얼마나 효율적으로 쓰는가
    - **안전성**: 부채가 과도하지 않고 이자를 감당할 수 있는가
    """)

metrics = run_quality(data)
score, details = score_quality(metrics)

# 점수 요약
total = len(details)
pct   = score / total
color = "green" if pct >= 0.7 else "orange" if pct >= 0.5 else "red"
verdict = "✅ PASS" if pct >= 0.7 else "⚠️ BORDERLINE" if pct >= 0.5 else "❌ FAIL"

m1, m2, m3 = st.columns(3)
m1.metric("Quality Score", f"{score} / {total}")
m2.metric("Pass Rate", f"{pct*100:.0f}%")
m3.metric("Verdict", verdict)

st.divider()

# 항목별 테이블
for item in details:
    col_label, col_val, col_thresh, col_status, col_exp = st.columns([2, 1.2, 1.2, 1, 3])

    status_icon = {"PASS": "✅", "FAIL": "❌", "N/A": "➖"}[item["status"]]

    col_label.markdown(f"**{item['label']}**")
    col_val.markdown(item["value"])
    col_thresh.markdown(f"`{item['threshold']}`")
    col_status.markdown(status_icon)
    col_exp.caption(item["explanation"])

# session_state에 저장 (Part 3, 4에서 재사용)
st.session_state["metrics"]       = metrics
st.session_state["quality_score"] = score
st.session_state["data"]          = data
st.session_state["ticker"]        = ticker
st.session_state["proj_years"]    = proj_years
st.session_state["discount_rate"] = discount_rate
st.session_state["current_price"] = current_price