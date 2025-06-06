import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import datetime as dt
from urllib.error import URLError

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="TrustFlash Bot – Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------
# BASIC STYLE (hide Streamlit chrome)
# --------------------------------------------------
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
# HELPERS
# --------------------------------------------------

def safe_float(val):
    """Return Python float or None if NaN / not convertible."""
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

def get_vix() -> pd.DataFrame:
    """Fetch 6 m of daily VIX data and compute 20‑day MA."""
    df = yf.Ticker("^VIX").history(period="6mo", interval="1d", auto_adjust=False)
    if df.empty or len(df) < 30:
        raise ValueError("Insufficient VIX data")
    df["MA20"] = df["Close"].rolling(20).mean()
    return df.tail(90)


@st.cache_data(ttl=900, show_spinner=False)

def get_gex() -> pd.DataFrame:
    """Fetch last 60 d of SPX Gamma Exposure (GEX) with fallback download."""
    import io, requests

    url = "https://raw.githubusercontent.com/SqueezeMetrics/legacy-data/master/spy_gex.csv"
    try:
        df = pd.read_csv(url, parse_dates=["date"], dtype={"GEX": "float"})
    except Exception:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "trustflash-bot"})
        if resp.status_code != 200:
            raise ValueError("GEX source unreachable (status != 200)")
        df = pd.read_csv(io.StringIO(resp.text), parse_dates=["date"], dtype={"GEX": "float"})

    if df.empty or "GEX" not in df.columns:
        raise ValueError("GEX data missing or schema changed")
    return df.tail(60)

# --------------------------------------------------
# VIX SECTION
# --------------------------------------------------
try:
    vix_df = get_vix()
    latest_vix = safe_float(vix_df["Close"].iloc[-1])
    latest_ma = safe_float(vix_df["MA20"].iloc[-1])

    col1, col2 = st.columns(2)
    col1.metric("Current VIX", f"{latest_vix:.2f}" if latest_vix else "–")
    col2.metric("20‑Day Avg", f"{latest_ma:.2f}" if latest_ma else "–")

    st.subheader("VIX Trend vs 20‑Day Moving Average")
    fig_vix = go.Figure([
        go.Scatter(x=vix_df.index, y=vix_df["Close"], name="VIX", line=dict(width=2, color="#3B82F6")),
        go.Scatter(x=vix_df.index, y=vix_df["MA20"], name="20‑Day MA", line=dict(width=1.5, dash="dash", color="#FBBF24")),
    ])
    fig_vix.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig_vix, use_container_width=True)
except (URLError, ValueError):
    st.error("VIX data currently unavailable. Market may be closed or API down.")

# --------------------------------------------------
# GEX SECTION
# --------------------------------------------------
try:
    gex_df = get_gex()
    st.subheader("SPX Gamma Exposure (GEX)")
    fig_gex = go.Figure([
        go.Bar(x=gex_df["date"], y=gex_df["GEX"], name="GEX", marker_color="#10B981"),
    ])
    fig_gex.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30),
                          xaxis_title="Date", yaxis_title="Gamma ($)")
    st.plotly_chart(fig_gex, use_container_width=True)
except (URLError, ValueError):
    st.warning("GEX data temporarily unavailable. Source CSV unreachable.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("<hr style='margin-top:30px;margin-bottom:10px'>", unsafe_allow_html=True)
left, right = st.columns([3, 1])
left.caption("Data refreshed every 15 min • Prototype v0.5")
right.caption("© 2025 TrustFlashTrade")
