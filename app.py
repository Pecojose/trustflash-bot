"""app.py – TrustFlash Bot dashboard (v0.8)
-----------------------------------------------------------------------------
Adds bilingual **News Flash** module (top‑5 market‑moving headlines).
• Sources: snscrape (Twitter/X) + NewsAPI RSS mirror (free) + fallback sample
• Update every 15 min (manual refresh) and 30 min pre‑market
• Headlines returned in English & Spanish (OpenAI GPT‑3.5) – insert your API key
"""

from pathlib import Path
import datetime as dt
import io
from urllib.error import URLError

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
import feedparser  # pip install feedparser
try:
    import snscrape.modules.twitter as sntwitter  # Twitter scraping
    TWITTER_OK = True
except AttributeError:  # Incompatible snscrape on Python 3.13
    TWITTER_OK = False
import openai  # pip install openai

###############################################################################
# CONFIG
###############################################################################
openai.api_key = st.secrets.get("OPENAI_API_KEY", "")  # add in Streamlit secrets
TWITTER_ACCOUNTS = [
    "KobeissiLetter",
    "JesseCohenInv",
    "Investingcom",
    "WatcherGuru",
    "realDonaldTrump",
]
NEWSAPI_RSS = [
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
]

st.set_page_config(
    page_title="TrustFlash Bot – Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      #MainMenu {visibility: hidden;} header, footer {visibility: hidden;}
      .block-container {padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

###############################################################################
# HELPERS
###############################################################################

def safe_float(v):
    try:
        if isinstance(v, pd.Series):
            v = v.iloc[0]
        f = float(v)
        return None if pd.isna(f) else f
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)

def get_vix():
    df = yf.Ticker("^VIX").history(period="6mo", interval="1d")
    if df.empty or len(df) < 30:
        raise ValueError("Insufficient VIX data")
    df["MA20"] = df["Close"].rolling(20).mean()
    return df.tail(90)


@st.cache_data(ttl=900, show_spinner=False)

def get_gex():
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
    local = Path(__file__).with_name("sample_gex.csv")
    if local.exists():
        df = pd.read_csv(local, parse_dates=["date"], dtype={"GEX": "float"})
        df["_src"] = "local_sample"
        return df.tail(60)
    raise ValueError("No GEX data available")


###############################################################################
# NEWS MODULE
###############################################################################

NEWS_CACHE_TTL = 900  # 15 min

@st.cache_data(ttl=NEWS_CACHE_TTL, show_spinner=False)

def get_raw_tweets(limit: int = 40):
    tweets = []
    for user in TWITTER_ACCOUNTS:
        for i, tweet in enumerate(sntwitter.TwitterUserScraper(user).get_items()):
            if i >= 10:
                break
            tweets.append(tweet.content)
    return tweets[:limit]


@st.cache_data(ttl=NEWS_CACHE_TTL, show_spinner=False)

def get_raw_rss(limit: int = 30):
    headlines = []
    for feed in NEWSAPI_RSS:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries[:10]:
            headlines.append(entry.title)
    return headlines[:limit]


def summarise_headlines(texts: list[str], lang: str = "bilingual", k: int = 5) -> list[str]:
    joined = "\n".join([f"- {t}" for t in texts])
    sys = "Eres un analista financiero profesional."
    if lang == "bilingual":
        user = (
            "He recopilado titulares que impactan al mercado. "
            "Resume EXACTAMENTE en 5 bullets de ≤25 palabras cada uno, español primero y traducción inglesa entre paréntesis."
        )
    else:
        user = (
            f"Resume EXACTAMENTE {k} bullets en {lang}, ≤25 palabras cada uno, conservando tickers en mayúsculas."
        )
    if not openai.api_key:
        return ["(No OpenAI key configured – showing raw headline)"] + texts[:5]
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user + "\n\n" + joined},
        ],
        max_tokens=300,
        temperature=0.5,
    )
    bullets = resp.choices[0].message.content.strip().split("\n")
    bullets = [b.lstrip("- •") for b in bullets if b]
    return bullets[:k]


###############################################################################
# LAYOUT – HEADER
###############################################################################
logo_c, title_c = st.columns([1, 5])
with logo_c:
    st.image("https://trustflashtrade.com/_next/image?url=%2Flogo_nav.png&w=256&q=75", width=90)
with title_c:
    st.markdown("## ⚡ **TrustFlash Bot** – Real-time Market Dashboard")
    st.caption("Gamma Exposure • Volatility • Price Levels – refreshed every 15 min")

st.divider()

###############################################################################
# VIX SECTION
###############################################################################
try:
    vix_df = get_vix()
    v_cur = safe_float(vix_df["Close"].iloc[-1])
    v_ma = safe_float(vix_df["MA20"].iloc[-1])
    m1, m2 = st.columns(2)
    m1.metric("Current VIX", f"{v_cur:.2f}" if v_cur else "–")
    m2.metric("20-Day Avg", f"{v_ma:.2f}" if v_ma else "–")

    st.subheader("VIX Trend vs 20-Day Moving Average")
    fig_vix = go.Figure([
        go.Scatter(x=vix_df.index, y=vix_df["Close"], name="VIX", line=dict(width=2, color="#3B82F6")),
        go.Scatter(x=vix_df.index, y=vix_df["MA20"], name="20-Day MA", line=dict(width=1.3, dash="dash", color="#FBBF24")),
    ])
    fig_vix.update_layout(height=350, margin=dict(l=20, r=20, t=10, b=30))
    st.plotly_chart(fig_vix, use_container_width=True)
except Exception as err:
    st.error(f"VIX unavailable: {err}")

###############################################################################
# GEX SECTION
###############################################################################
try:
    gex_df = get_gex()
    st.subheader("SPX Gamma Exposure (GEX)")
    tag = "(sample)" if gex_df["_src"].iloc[0] == "local_sample" else ""
    fig_gex = go.Figure([
        go.Bar(x=gex_df["date"], y=gex_df["GEX"], marker_color="#10B981"),
    ])
    fig_gex.update_layout(height=350, title=tag, margin=dict(l=20, r=20, t=10, b=30))
    st.plotly_chart(fig_gex, use_container_width=True)
except Exception as e:
    st.warning(f"GEX unavailable: {e}")

###############################################################################
# NEWS FLASH SECTION
###############################################################################
with st.expander("📰 News Flash – last 15 min", expanded=False):
    raw = get_raw_tweets() + get_raw_rss()
    bullets = summarise_headlines(raw, lang="bilingual", k=5)
    for b in bullets:
        st.write("• ", b)

###############################################################################
# FOOTER
###############################################################################

st.divider()
left, right = st.columns([3, 1])
left.caption("Data refreshed every 15 min • Prototype v0.8 (News beta)")
right.caption("© 2025 TrustFlashTrade")
