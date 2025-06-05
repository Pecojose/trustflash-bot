import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import datetime as dt
from urllib.error import URLError

# --------------------------------------------------
# PAGE CONFIG & BASIC STYLE
# --------------------------------------------------
st.set_page_config(
    page_title="TrustFlash Bot – Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit default menu & footer
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image(
        "https://trustflashtrade.com/_next/image?url=%2Flogo_nav.png&w=256&q=75",
        width=90,
    )
with col_title:
    st.markdown("## ⚡ **TrustFlash Bot** – Real‑time Market Dashboard")
    st.caption("Gamma Exposure • Volatility • Price Levels – refreshed every 15 min")

st.markdown("---")

# --------------------------------------------------
# DATA HELPERS (cached 15 min)
# --------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)

def get_vix():
    end = dt.date.today()
    start = end - dt.timedelta(days=150)
    data = yf.download("^VIX", start=start, end=end, progress=False)
    if data.empty:
        raise ValueError("Empty VIX frame")
    data["MA20"] = data["Close"].rolling(20).mean()
    return data.tail(90)


@st.cache_data(ttl=900, show_spinner=False)

def get_gex():
    url = "https://raw.githubusercontent.com/SqueezeMetrics/legacy-data/master/spy_gex.csv"
    gex = pd.read_csv(url, parse_dates=["date"])
    if gex.empty:
        raise ValueError("Empty GEX frame")
    return gex.tail(60)


# --------------------------------------------------
# VIX SECTION
# --------------------------------------------------
try:
    vix_df = get_vix()

    # Metrics row
    col1, col2 = st.columns(2)
    latest_vix = vix_df["Close"].iloc[-1]
    latest_ma = vix_df["MA20"].iloc[-1]
    col1.metric("Current VIX", f"{latest_vix:.2f}")
    col2.metric("20‑Day Avg", f"{latest_ma:.2f}")

    # Chart
    st.subheader("VIX Trend vs 20‑Day Moving Average")
    fig_vix = go.Figure()
    fig_vix.add_trace(go.Scatter(x=vix_df.index, y=vix_df["Close"], name="VIX",
                                 line=dict(width=2, color="#3B82F6")))
    fig_vix.add_trace(go.Scatter(x=vix_df.index, y=vix_df["MA20"], name="20‑Day MA",
                                 line=dict(width=1.5, dash="dash", color="#FBBF24")))
    fig_vix.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig_vix, use_container_width=True)
except (URLError, ValueError) as e:
    st.error("Unable to load VIX data right now 🤔")

# --------------------------------------------------
# GEX SECTION
# --------------------------------------------------
try:
    gex_df = get_gex()

    st.subheader("SPX Gamma Exposure (GEX)")
    fig_gex = go.Figure()
    fig_gex.add_trace(go.Bar(x=gex_df["date"], y=gex_df["GEX"], name="GEX",
                              marker_color="#10B981"))
    fig_gex.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          xaxis_title="Date", yaxis_title="Gamma ($)")
    st.plotly_chart(fig_gex, use_container_width=True)
except (URLError, ValueError):
    st.warning("GEX data temporarily unavailable.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("<hr style='margin-top:30px;margin-bottom:10px'>", unsafe_allow_html=True)
left, right = st.columns([3, 1])
left.caption("Data refreshed every 15 min • Prototype v0.2")
right.caption("© 2025 TrustFlashTrade")
