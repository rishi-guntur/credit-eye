import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from datetime import datetime

# 1. SECRETS CONFIGURATION
# This pulls the key from the Streamlit Cloud settings instead of the code
try:
    api_key = st.secrets["FRED_API_KEY"]
    fred = Fred(api_key=api_key)
except Exception as e:
    st.error("Secrets not found. Please add your FRED_API_KEY to the Streamlit Settings.")
    st.stop()

st.set_page_config(page_title="Credit Eyes", layout="wide")

@st.cache_data(ttl=3600)
def fetch_all_data():
    data = {
        "FFR": fred.get_series('FEDFUNDS'),
        "M2": fred.get_series('WM2NS'),
        "HY_Spread": fred.get_series('BAMLH0A0HYM2'),
        "IG_Spread": fred.get_series('BAMLC0A0CM'),
        "Yield_10Y": fred.get_series('DGS10'),
        "Yield_2Y": fred.get_series('DGS2'),
        "Spread_10Y2Y": fred.get_series('T10Y2Y'),
        "Consumer_Total": fred.get_series('TOTALSL'),
        "Revolving": fred.get_series('REVOLSL'),
        "BAA_Yield": fred.get_series('BAA')
    }
    return data

try:
    d = fetch_all_data()

    # --- DATE RANGE CONTROLS ---
    st.sidebar.header("Date Range")
    min_date = datetime(1990, 1, 1)
    max_date = datetime.today()

    start_date = st.sidebar.date_input("Start Date", value=datetime(2000, 1, 1), min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

    def clip(series):
        return series.loc[str(start_date):str(end_date)]

    # --- SECTION 1: MACRO REGIME ---
    st.header("1. Macro Regime: Liquidity vs. Rates")
    m2_growth = d['M2'].pct_change(periods=52).iloc[-1] * 100
    st.metric("M2 YoY Growth", f"{m2_growth:.2f}%")

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=clip(d['FFR']).index, y=clip(d['FFR']), name="Fed Funds Rate", line=dict(color='#ff4b4b')))
    fig1.add_trace(go.Scatter(x=clip(d['M2']).index, y=clip(d['M2']), name="M2 Supply", yaxis="y2", line=dict(color='#00d4ff')))
    fig1.update_layout(template="plotly_dark", height=300, yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig1, use_container_width=True)

    # --- SECTION 2: CREDIT SPREADS ---
    st.header("2. Credit Spreads: HY vs IG")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=clip(d['HY_Spread']).index, y=clip(d['HY_Spread']), name="High Yield Spread"))
    fig2.add_trace(go.Scatter(x=clip(d['IG_Spread']).index, y=clip(d['IG_Spread']), name="Investment Grade Spread"))
    fig2.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig2, use_container_width=True)

    # --- SECTION 3: YIELD CURVE ---
    st.header("3. Treasury Yield Curve (10Y-2Y Spread)")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=clip(d['Spread_10Y2Y']).index, y=clip(d['Spread_10Y2Y']), name="10Y-2Y Spread", line=dict(color='#4dd9ac')))
    fig3.add_hline(y=0, line_dash="dash")
    fig3.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig3, use_container_width=True)

    # --- SECTION 4: CONSUMER STRESS ---
    st.header("4. Consumer Credit Stress")
    revolving_clipped = clip(d['Revolving'])
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=revolving_clipped.index, y=revolving_clipped, name="Credit Card Debt ($B)"))
    fig4.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig4, use_container_width=True)

except Exception as e:
    st.error(f"Stream Error: {e}")
