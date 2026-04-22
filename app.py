import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from datetime import datetime

# Initialize FRED (Using a common public key for demo; get your own at fred.stlouisfed.org)
fred = Fred(api_key='180513e2616ca9103f8d0a33154057c0')

st.set_page_config(page_title="Macro Regime Dashboard", layout="wide")
st.title("🏛️ Macro Regime Metadata (Live)")

# 1. Fetch Data (FFR and M2 Money Supply)
@st.cache_data(ttl=86400) # Updates once a day
def get_macro_data():
    # 'FEDFUNDS' is FFR, 'WM2NS' is M2 Money Supply
    ffr = fred.get_series('FEDFUNDS', observation_start='2010-01-01')
    m2 = fred.get_series('WM2NS', observation_start='2010-01-01')
    return ffr, m2

try:
    ffr_series, m2_series = get_macro_data()
    
    # 2. Logic for Regimes
    latest_ffr = ffr_series.iloc[-1]
    zirp_status = "ACTIVE" if latest_ffr < 0.25 else "INACTIVE"
    
    # Calculate M2 Growth (Expansion vs Tightening)
    m2_growth = m2_series.pct_change(periods=52) * 100 # Year-over-year growth
    current_growth = m2_growth.iloc[-1]
    regime = "Expansion" if current_growth > 0 else "Contraction/Tightening"

    # 3. Display Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Fed Funds Rate", f"{latest_ffr}%")
    c2.metric("ZIRP Status", zirp_status)
    c3.metric("M2 Money Supply Regime", regime, f"{current_growth:.2f}% YoY")

    # 4. Visualization
    st.subheader("Federal Funds Rate vs Money Supply Velocity")
    fig = go.Figure()
    
    # Add FFR Trace
    fig.add_trace(go.Scatter(x=ffr_series.index, y=ffr_series.values, name="Fed Funds Rate", line=dict(color='#ff4b4b')))
    
    # Add M2 Growth on Secondary Axis
    fig.add_trace(go.Scatter(x=m2_growth.index, y=m2_growth.values, name="M2 YoY Growth %", line=dict(color='#00d4ff'), yaxis="y2"))

    fig.update_layout(
        template="plotly_dark",
        yaxis=dict(title="Fed Funds Rate (%)"),
        yaxis2=dict(title="M2 Growth (%)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"Data automatically updated through {datetime.now().strftime('%B %Y')}")

except Exception as e:
    st.error(f"Waiting for data stream: {e}")
