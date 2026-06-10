import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Valuation")

def valuation(eps, growth, pe, years, discount=0.15, mos=0.5):
    future_eps = eps *(1+growth) ** years
    future_price = future_eps * pe
    intrinsic = future_price/(1 + discount) ** years
    fair_value = intrinsic*(1 - mos)
    return intrinsic, fair_value

ticker = st.text_input("Ticker", "NVDA").upper()

years = st.slider("Projection Years", 5, 15, 10)

if ticker:

    stock = yf.Ticker(ticker)
    info = stock.info

    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )

    eps = info.get("trailingEps") or info.get("forwardEps") or 1

    growth = info.get("earningsGrowth")
    growth = growth if growth else 0.15

    pe = info.get("trailingPE") or info.get("forwardPE") or 20

    intrinsic, fair_value = valuation(
        eps=eps,
        growth=growth,
        pe=pe,
        years=years
    )