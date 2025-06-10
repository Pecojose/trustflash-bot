"""app.py – TrustFlash Bot dashboard (stable)
-------------------------------------------------
* Shows VIX + 20‑day MA (yfinance)
* Shows SPX Gamma Exposure (GEX) with mirrors and local fallback
* No external CSS/JS – pure Streamlit + Plotly
"""

from pathlib import Path
from urllib.error import URLError
import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

###############################################################################
# PAGE CONFIG & STYLE
###############################################################################
st.set_page_config(
    page_title="TrustFlash Bot – Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        header, footer {visibility: hidden;}
        .block-container {padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

###############################################################################
# HELPERS
###############################################################################

def safe_float(value) -> float | None:
    """Return a python float or None if the value is not finite."""
    try:
        if isinstance(value, pd.Series):
            value = value.iloc[0]
        out = float(value)
        return None if pd.isna(out) else out
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)

def get_vix() -> pd.DataFrame:
    """Return last 6 m of daily VIX with 20‑day MA; raise ValueError if <30 rows."""
    df = yf.Ticker("^VIX").history(period="6mo", interval="1d", auto_adjust=False)
    if df.empty or len(df) < 30:
        raise ValueError("Insufficient VIX data")
    df["MA20"] = df["Close"].rolling(20).mean()
    return df.tail(90)


@st.cache_data(ttl=900, show_spinner=False)

def get_gex() -> pd.DataFrame:
    """Return last 60 d of SPX Gamma Exposure.

    Order of attempts:
    1. GitHub raw
    2. jsDelivr mirror
    3. Local fallback `sample_gex.csv`
    """
    urls = [
        "https://raw.githubusercontent.com/SqueezeMetrics/legacy-data/master/spy_gex.csv",
        "https://cdn.jsdelivr.net/gh/SqueezeMetrics/legacy-data@master/spy_gex.csv",
    ]
    for url in urls:
        try:
            df = pd.read_csv(url, parse_dates=["date"], dtype={"GEX": "float"})
            if not df.empty and "GEX" in df.columns:
                df["_src"] = url
                return df.tail(60)
        except Exception:
            continue

    # LOCAL FALLBACK
    local_csv = Path(__file__).with_name("sample_gex.csv")
    if local_csv.exists():
        df_local = pd.read_csv(local_csv, parse_dates=["date"], dtype={"GEX": "float"})
        df_local["_src"] = "local_sample"
        return df_local.tail(60)

    raise ValueError("GEX fetch failed and no local sample_gex.csv present")

###############################################################################
# HEADER
###############################################################################
logo_col, title_col = st.columns([1, 5])
with logo_col:
    st.image(
        "https://trustflashtrade.com/_next/image?url=%2Flogo_nav.png&w=256&q=75",
        width=90,
    )
with title_col:
    st.markdown("## ⚡ **TrustFlash Bot** – Real‑time Market Dashboard")
    st.caption("Gamma Exposure • Volatility • Price Levels – refreshed every 15 min")

st.divider()

###############################################################################
# VIX SECTION
###############################################################################
try:
    vix_df = get_vix()
    vix_cur = safe_float(vix_df["Close"].iloc[-1])
    vix_ma = safe_float(vix_df["MA20"].iloc[-1])

    m1, m2 = st.columns(2)
    m1.metric("Current VIX", f"{vix_cur:.2f}" if vix_cur else "–")
    m2.metric("20‑Day Avg", f"{vix_ma:.2f}" if vix_ma else "–")

    st.subheader("VIX Trend vs 20‑Day Moving Average")
    fig_vix = go.Figure([
        go.Scatter(x=vix_df.index, y=vix_df["Close"], name="VIX", line=dict(width=2, color="#3B82F6")),
        go.Scatter(x=vix_df.index, y=vix_df["MA20"], name="20‑Day MA", line=dict(width=1.3, dash="dash", color="#FBBF24")),
    ])
    fig_vix.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig_vix, use_container_width=True)
except (URLError, ValueError):
    st.error("VIX data unavailable – market closed or API down.")

###############################################################################
# GEX SECTION
###############################################################################
try:
    gex_df = get_gex()
    st.subheader("SPX Gamma Exposure (GEX)")
    fig_gex = go.Figure([
        go.Bar(x=gex_df["date"], y=gex_df["GEX"], marker_color="#10B981"),
    ])
    tag = "(sample)" if gex_df["_src"].iloc[0] == "local_sample" else ""
    fig_gex.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          xaxis_title="Date", yaxis_title="Gamma ($)", title=tag)
    st.plotly_chart(fig_gex, use_container_width=True)
except (URLError, ValueError):
    st.warning("GEX data temporarily unavailable. All sources unreachable.")

###############################################################################
# FOOTER
###############################################################################

st.divider()
left, right = st.columns([3, 1])
left.caption("Data refreshed every 15 min • Prototype v0.7")
right.caption("© 2025 TrustFlashTrade")
