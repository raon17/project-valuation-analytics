import streamlit as st
from db.connection import init_db

st.set_page_config(
    page_title="VMI Dashboard",
    layout="wide"
)

init_db()

st.title("Adam Khoo VMI Dashboard")
st.markdown("""
**Value Momentum Investing (VMI)**

""")