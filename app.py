import streamlit as st, pandas as pd, yfinance as yf, requests, datetime as dt
import plotly.graph_objects as go

st.set_page_config(page_title="TrustFlash Bot", page_icon="⚡", layout="wide")

st.title("⚡ TrustFlash Bot – Free Dashboard")

# ---------- VIX ----------
end = dt.date.today()
vix = yf.download("^VIX", start=end - dt.timedelta(days=90), end=end)
vix["MA20"] = vix["Close"].rolling(20).mean()

fig_vix = go.Figure()
fig_vix.add_trace(go.Scatter(x=vix.index, y=vix["Close"], name="VIX",
                             line=dict(width=2)))
fig_vix.add_trace(go.Scatter(x=vix.index, y=vix["MA20"],
                             name="20-Day Avg", line=dict(dash="dash")))
fig_vix.update_layout(title="VIX Trend with 20-Day Average",
                      xaxis_title="", yaxis_title="VIX Level")
st.plotly_chart(fig_vix, use_container_width=True)

# ---------- GEX (dummy pull) ----------
gex_url = ("https://raw.githubusercontent.com/"
           "SqueezeMetrics/legacy-data/master/spy_gex.csv")
try:
    gex = pd.read_csv(gex_url, parse_dates=["date"])
    gex_last = gex.tail(30)
    st.line_chart(gex_last.set_index("date")["GEX"],
                  height=300,
                  use_container_width=True)
except Exception:
    st.warning("GEX data temporarily unavailable.")

st.write("*Data is refreshed every 15 min • Prototype version*")
