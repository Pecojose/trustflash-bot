import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import datetime as dt
from urllib.error import URLError
import io, requests, importlib.resources as pkg_resources

# --------------------------------------------------
# PAGE CONFIG & GLOBAL STYLE
# --------------------------------------------------
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

# --------------------------------------------------
# UTILS  ----------------------------------------------------------------------
# --------------------------------------------------

def safe_float(val):
    """Return float or None if value is not finite."""
    try:
        if isinstance(val, pd.Series):
            val = val.iloc[0]
        num = float(val)
        if pd.isna(num):
            return None
        return num
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)

def get_gex() -> pd.DataFrame:
    """Return last 60 d of SPX Gamma Exposure (GEX) with multiple fallbacks.

    1. Raw GitHub CSV  
    2. jsDelivr CDN mirror  
    3. Local `sample_gex.csv` shipped with the repo (ensures UI never breaks).
    """
    import pathlib

    urls = [
        "https://raw.githubusercontent.com/SqueezeMetrics/legacy-data/master/spy_gex.csv",
        "https://cdn.jsdelivr.net/gh/SqueezeMetrics/legacy-data@master/spy_gex.csv",
    ]

    for src in urls:
        try:
            df = pd.read_csv(src, parse_dates=["date"], dtype={"GEX": "float"})
            if not df.empty and "GEX" in df.columns:
                df["_source"] = src
                return df.tail(60)
        except Exception:
            continue

    # ---- local fallback ----
    local_path = pathlib.Path(__file__).with_name("sample_gex.csv")
    if local_path.exists():
        df_local = pd.read_csv(local_path, parse_dates=["date"], dtype={"GEX": "float"})
        df_local["_source"] = "local_sample"
        return df_local.tail(60)

    raise ValueError("All GEX sources failed and no local sample_gex.csv found"))

# --------------------------------------------------
# HEADER LAYOUT
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
# VIX SECTION
# --------------------------------------------------
try:
    vix_df = get_vix()
    latest_vix = safe_float(vix_df["Close"].iloc[-1])
    latest_ma = safe_float(vix_df["MA20"].iloc[-1])

    m1, m2 = st.columns(2)
    m1.metric("Current VIX", f"{latest_vix:.2f}" if latest_vix else "–")
    m2.metric("20‑Day Avg", f"{latest_ma:.2f}" if latest_ma else "–")

    st.subheader("VIX Trend vs 20‑Day Moving Average")
    fig_vix = go.Figure([
        go.Scatter(x=vix_df.index, y=vix_df["Close"], name="VIX", line=dict(width=2, color="#3B82F6")),
        go.Scatter(x=vix_df.index, y=vix_df["MA20"], name="20‑Day MA", line=dict(width=1.3, dash="dash", color="#FBBF24")),
    ])
    fig_vix.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig_vix, use_container_width=True)
except (URLError, ValueError):
    st.error("VIX data currently unavailable (market closed or API down).")

# --------------------------------------------------
# GEX SECTION
# --------------------------------------------------
try:
    gex_df = get_gex()
    st.subheader("SPX Gamma Exposure (GEX)")
    fig_gex = go.Figure([
        go.Bar(x=gex_df["date"], y=gex_df["GEX"], marker_color="#10B981"),
    ])
    src_note = "(sample)" if gex_df["_source"].iloc[0] == "local_sample" else ""
    fig_gex.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          xaxis_title="Date", yaxis_title="Gamma ($)", title=src_note)
    st.plotly_chart(fig_gex, use_container_width=True)
except (URLError, ValueError):
    st.warning("GEX data temporarily unavailable. Source unreachable.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("<hr style='margin-top:30px;margin-bottom:10px'>", unsafe_allow_html=True)
left, right = st.columns([3, 1])
left.caption("Data refreshed every 15 min • Prototype v0.6")
right.caption("© 2025 TrustFlashTrade")
