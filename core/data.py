import yfinance as yf
import streamlit as st

@st.cache_data(ttl=3600)
def get_ticker_data(ticker: str):
    t = yf.Ticker(ticker)

    info = t.info
    financials = t.financials 
    balance = t.balance_sheet
    cashflow = t.cashflow
    history = t.history(period="2y")
    history_5y = t.history(period="5y")

    return {
        "info": info,
        "financials": financials,
        "balance": balance,
        "cashflow": cashflow,
        "history": history,
        "history_5y": history_5y,
    }