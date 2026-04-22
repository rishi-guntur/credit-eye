import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from datetime import datetime

# Initialize FRED (Replace with your actual key)
fred = Fred(api_key='bb77484198247930e72b4d6f3dbeb7aa')

st.set_page_config(page_title="Credit Eye", layout="wide")
st.title("Macro")
st.markdown(f"*Live*")

@st.cache_data(ttl=3600)
def fetch_all_data():
    # Fetching specific series IDs from FRED
    data = {
        "FFR": fred.get_series('FEDFUNDS'),
        "M2": fred.get_series('WM2NS'),
        "HY_Spread": fred.get_series('BAMLH0A0HYM2'), # ICE BofA High Yield Spread
        "IG_Spread": fred.get_series('BAMLC0A0CM'),   # ICE BofA IG Spread
        "Yield_10Y": fred.get_series('DGS10'),
        "Yield_2Y": fred.get_series('DGS2Y'),
        "Spread_10Y2Y": fred.get_series('T10Y2Y'),
        "Consumer_Total": fred.get_series('TOTALSL'),
        "Revolving": fred.get_series('REVOLSL'),
        "BAA_Yield": fred.get_series('BAA')
    }
    return data

try:
    d = fetch_all_data()

    # --- SECTION 1: MACRO REGIME (M2 vs FFR) ---
    st.header("1. Macro Regime: Liquidity vs. Rates")
    col1, col2 = st.columns([1, 3])
    with col1:
        m2_growth = d['M2'].pct_change(periods=52).iloc[-1] * 100
        st.metric("M2 YoY Growth", f"{m2_growth:.2f}%", delta_color="inverse")
        st.write("Tracks the 'Liquidity Tide'. Negative growth signals tightening.")
    
    with col2:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=d['FFR'].index, y=d['FFR'], name="Fed Funds Rate", line=dict(color='#ff4b4b')))
        fig1.add_trace(go.Scatter(x=d['M2'].index, y=d['M2'], name="M2 Supply", yaxis="y2", line=dict(color='#00d4ff')))
        fig1.update_layout(template="plotly_dark", height=300, yaxis2=dict(overlaying="y", side="right"), margin=dict(t=20, b=20))
        st.plotly_chart(fig1, use_container_width=True)

    # --- SECTION 2: CREDIT SPREADS (HY vs IG) ---
    st.header("2. Credit Spreads: Risk Appetite")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("High Yield Spread", f"{d['HY_Spread'].iloc[-1]:.2f}%")
    with c2:
        st.metric("IG Spread", f"{d['IG_Spread'].iloc[-1]:.2f}%")
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=d['HY_Spread'].index, y=d['HY_Spread'], name="High Yield Spread", fill='tozeroy'))
    fig2.add_trace(go.Scatter(x=d['IG_Spread'].index, y=d['IG_Spread'], name="Investment Grade Spread"))
    fig2.update_layout(template="plotly_dark", height=300, title="Credit Spread Compression/Expansion")
    st.plotly_chart(fig2, use_container_width=True)

    # --- SECTION 3: YIELD CURVE (10Y-2Y) ---
    st.header("3. Treasury Yield Curve & 10Y-2Y Spread")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=d['Spread_10Y2Y'].index, y=d['Spread_10Y2Y'], name="10Y-2Y Spread", line=dict(color='yellow')))
    fig3.add_hline(y=0, line_dash="dash", line_color="white")
    fig3.update_layout(template="plotly_dark", height=300, title="Inversion Watch (Yellow < 0 = Inverted)")
    st.plotly_chart(fig3, use_container_width=True)

    # --- SECTION 4: CONSUMER STRESS & BAA ---
    st.header("4. Consumer & Corporate Credit Stress")
    col3, col4 = st.columns(2)
    with col3:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=d['Revolving'].index[-60:], y=d['Revolving'][-60:], name="Revolving (Credit Cards)"))
        fig4.update_layout(template="plotly_dark", height=300, title="Total Consumer Credit ($B)")
        st.plotly_chart(fig4, use_container_width=True)
    with col4:
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=d['BAA_Yield'].index, y=d['BAA_Yield'], name="Moody's BAA Yield", line=dict(color='orange')))
        fig5.update_layout(template="plotly_dark", height=300, title="Moody's BAA Corp Bond Yield")
        st.plotly_chart(fig5, use_container_width=True)

except Exception as e:
    st.error(f"Error fetching live stream: {e}. Check if your API key is correct in app.py.")
