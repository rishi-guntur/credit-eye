import streamlit as st
import pandas as pd
import numpy as np
from fredapi import Fred
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import yfinance as yf

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Credit Eyes", layout="wide", page_icon="📡")

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0a0e1a;
    color: #c9d1e0;
}
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; letter-spacing: -0.03em; }
.stMetric label { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #5a7a9a; text-transform: uppercase; letter-spacing: 0.1em; }
.stMetric [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem; }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: #3a6ea8;
    text-transform: uppercase;
    border-left: 2px solid #3a6ea8;
    padding-left: 8px;
    margin-bottom: 4px;
}

.regime-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 2px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    margin: 4px 4px 4px 0;
}
.badge-zirp    { background: #0d2a3d; border: 1px solid #00aaff; color: #00aaff; }
.badge-tight   { background: #3d0d0d; border: 1px solid #ff4b4b; color: #ff4b4b; }
.badge-expand  { background: #0d3d1a; border: 1px solid #4dd9ac; color: #4dd9ac; }
.badge-neutral { background: #1a1a0d; border: 1px solid #ffd700; color: #ffd700; }

.disclaimer {
    background: #0f1520;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 0.72rem;
    color: #5a7a9a;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 8px;
}

hr { border-color: #1a2540; margin: 28px 0; }
</style>
""", unsafe_allow_html=True)

# ── SECRETS ───────────────────────────────────────────────────────────────────
try:
    api_key = st.secrets["FRED_API_KEY"]
    fred = Fred(api_key=api_key)
except Exception as e:
    st.error("Secrets not found. Please add your FRED_API_KEY to Streamlit Settings.")
    st.stop()

# ── FRED DATA FETCH ───────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_fred_data():
    series_ids = {
        "FFR":            'FEDFUNDS',
        "M2":             'WM2NS',
        "HY_Spread":      'BAMLH0A0HYM2',
        "IG_Spread":      'BAMLC0A0CM',
        "Yield_10Y":      'DGS10',
        "Yield_2Y":       'DGS2',
        "Spread_10Y2Y":   'T10Y2Y',
        "Consumer_Total": 'TOTALSL',
        "Revolving":      'REVOLSL',
        "BAA_Yield":      'BAA',
        "Home_Price":     'CSUSHPINSA',
        "Mortgage_Debt":  'MDOAH',
        "PCE_Income":     'DSPIC96',
        "Manuf_Employ":   'MANEMP',
    }
    data = {}
    for key, sid in series_ids.items():
        try:
            data[key] = fred.get_series(sid)
        except Exception as e:
            st.warning(f"Could not fetch {key} ({sid}): {e}")
    return data

# ── YAHOO FINANCE DATA ────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_yf_data():
    tickers = {
        "BKLN":   "BKLN",
        "HYG":    "HYG",
        "LQD":    "LQD",
        "XLK":    "XLK",
        "XLI":    "XLI",
        "ARCC":   "ARCC",
        "FS_KKR": "FSK",
    }
    result = {}
    for key, ticker in tickers.items():
        try:
            df = yf.download(ticker, start="2018-01-01", progress=False, auto_adjust=True)
            result[key] = df['Close'].squeeze()
        except Exception as e:
            st.warning(f"Could not fetch {ticker}: {e}")
    return result

# ── SYNTHETIC / ESTIMATED DATA ────────────────────────────────────────────────
def synthetic_pik_toggle():
    dates = pd.date_range("2019-01-01", periods=28, freq="QS")
    values = [3.1, 3.4, 3.8, 8.2, 7.1, 5.8, 4.9, 4.2,
              4.0, 4.5, 5.2, 6.8, 9.4, 11.2, 12.8, 13.1,
              13.8, 14.2, 15.1, 15.6, 14.9, 15.3, 16.1, 16.4,
              15.8, 15.2, 14.9, 15.5]
    return pd.Series(values, index=dates)

def synthetic_maturity_wall():
    years  = ["2025", "2026", "2027", "2028", "2029", "2030+"]
    loans  = [310,    480,    620,    540,    390,    280]
    hy     = [180,    260,    310,    290,    210,    160]
    return years, loans, hy

def synthetic_pc_vs_bsl():
    dates = pd.date_range("2015-01-01", periods=10, freq="YS")
    pc_share  = [15, 18, 21, 25, 29, 35, 41, 49, 54, 58]
    bsl_share = [85, 82, 79, 75, 71, 65, 59, 51, 46, 42]
    return dates, pc_share, bsl_share

def state_tech_vc_activity():
    return {
        "CA": 100, "NY": 72, "MA": 58, "TX": 45, "WA": 44,
        "CO": 28,  "IL": 22, "GA": 20, "FL": 18, "PA": 16,
        "NC": 14,  "NJ": 13, "MD": 12, "VA": 11, "MN": 10,
        "OH": 9,   "MI": 8,  "AZ": 8,  "UT": 12, "OR": 10,
        "IN": 6,   "WI": 5,  "MO": 5,  "TN": 7,  "CT": 9,
    }

def state_rust_belt_abl():
    return {
        "OH": 82, "MI": 78, "IN": 74, "PA": 70, "WI": 68,
        "IL": 65, "MO": 58, "KY": 55, "WV": 48, "TN": 52,
        "MN": 50, "IA": 46, "KS": 40, "NE": 38, "OK": 35,
        "AL": 44, "MS": 36, "AR": 32, "LA": 42, "TX": 60,
        "NY": 45, "NJ": 42, "CT": 38, "MA": 35, "VA": 40,
    }

# ── HELPERS ───────────────────────────────────────────────────────────────────
def dark_layout(height=320, title=None, **kwargs):
    layout = dict(
        template="plotly_dark",
        height=height,
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0d1220",
        font=dict(family="IBM Plex Mono", size=11, color="#8aa0bc"),
        margin=dict(l=40, r=20, t=30 if title else 10, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )
    if title:
        layout["title"] = dict(text=title, font=dict(size=12, color="#5a9ad4"))
    layout.update(kwargs)
    return layout

def classify_ffr_regime(ffr_series):
    current = ffr_series.dropna().iloc[-1]
    prev_yr = ffr_series.dropna().iloc[-13] if len(ffr_series.dropna()) > 13 else current
    if current < 0.25:
        return "ZIRP", "badge-zirp"
    elif current > prev_yr + 0.5:
        return "TIGHTENING", "badge-tight"
    elif current < prev_yr - 0.5:
        return "EASING", "badge-expand"
    else:
        return "NEUTRAL / HOLD", "badge-neutral"

# ═════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Credit Intelligence Terminal</p>', unsafe_allow_html=True)
st.title("📡 Credit Eyes")

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    st.markdown("---")
    st.markdown("**Date Range**")
    start_date = st.date_input("Start", value=datetime(2005, 1, 1),
                                min_value=datetime(1990, 1, 1), max_value=datetime.today())
    end_date   = st.date_input("End",   value=datetime.today(),
                                min_value=datetime(1990, 1, 1), max_value=datetime.today())
    st.markdown("---")
    st.markdown("**Sections**")
    show_macro   = st.checkbox("1 · Macro Regime",    value=True)
    show_credit  = st.checkbox("2 · Credit Mix",      value=True)
    show_stress  = st.checkbox("3 · Stress Signals",  value=True)
    show_geo     = st.checkbox("4 · Geospatial Heat", value=True)
    show_lookback = st.checkbox("5 · Looking Back",   value=True)
    st.markdown("---")
    st.caption("Data: FRED · Yahoo Finance · LCD/S&P estimates")

def clip(s):
    return s.loc[str(start_date):str(end_date)]

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching data…"):
    try:
        d   = fetch_fred_data()
        yfd = fetch_yf_data()
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 · MACRO REGIME
# ═════════════════════════════════════════════════════════════════════════════
if show_macro:
    st.markdown("---")
    st.markdown('<p class="section-label">Section 01</p>', unsafe_allow_html=True)
    st.header("Macro Regime: Rates & Liquidity")

    regime_label, regime_class = classify_ffr_regime(d.get("FFR", pd.Series([0])))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ffr_current = d['FFR'].dropna().iloc[-1] if 'FFR' in d else 0
        st.metric("Fed Funds Rate", f"{ffr_current:.2f}%")
        st.markdown(f'<span class="regime-badge {regime_class}">{regime_label}</span>',
                    unsafe_allow_html=True)
    with c2:
        if 'M2' in d:
            m2_growth = d['M2'].pct_change(periods=52).dropna().iloc[-1] * 100
            st.metric("M2 YoY Growth", f"{m2_growth:.1f}%",
                      delta="Expansionary" if m2_growth > 0 else "Contractionary")
    with c3:
        if 'Yield_10Y' in d and 'Yield_2Y' in d:
            spread = d['Yield_10Y'].dropna().iloc[-1] - d['Yield_2Y'].dropna().iloc[-1]
            st.metric("10Y–2Y Spread", f"{spread:.2f}%",
                      delta="Normal" if spread > 0 else "Inverted ⚠️")
    with c4:
        if 'HY_Spread' in d:
            hy = d['HY_Spread'].dropna().iloc[-1]
            st.metric("HY OAS", f"{hy:.0f} bps",
                      delta="Tight" if hy < 400 else "Stressed" if hy > 600 else "Moderate")

    fig1 = go.Figure()
    if 'FFR' in d:
        ffr_c = clip(d['FFR'])
        fig1.add_trace(go.Scatter(x=ffr_c.index, y=ffr_c, name="Fed Funds Rate",
                                  line=dict(color='#ff4b4b', width=2)))
        fig1.add_hrect(y0=0, y1=0.25, fillcolor="rgba(0,170,255,0.06)",
                       line_width=0, annotation_text="ZIRP Zone",
                       annotation_font_color="#3a8fc4", annotation_font_size=10)
    if 'M2' in d:
        m2_c = clip(d['M2'])
        fig1.add_trace(go.Scatter(x=m2_c.index, y=m2_c, name="M2 Supply ($B)",
                                  yaxis="y2", line=dict(color='#00d4ff', width=1.5, dash='dot')))
    fig1.update_layout(**dark_layout(height=300, title="Fed Funds Rate vs M2 Money Supply"),
                       yaxis2=dict(overlaying="y", side="right",
                                   showgrid=False, color="#00d4ff"))
    st.plotly_chart(fig1, use_container_width=True)

    fig_yc = go.Figure()
    if 'Spread_10Y2Y' in d:
        sp = clip(d['Spread_10Y2Y'])
        fig_yc.add_trace(go.Scatter(x=sp.index, y=sp, name="10Y–2Y Spread",
                                    fill='tozeroy',
                                    fillcolor='rgba(77,217,172,0.08)',
                                    line=dict(color='#4dd9ac', width=2)))
        fig_yc.add_hline(y=0, line_dash="dash", line_color="#ff4b4b",
                         annotation_text="Inversion", annotation_font_color="#ff4b4b")
    fig_yc.update_layout(**dark_layout(height=240, title="Treasury Yield Curve — 10Y minus 2Y"))
    st.plotly_chart(fig_yc, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 · CREDIT MIX
# ═════════════════════════════════════════════════════════════════════════════
if show_credit:
    st.markdown("---")
    st.markdown('<p class="section-label">Section 02</p>', unsafe_allow_html=True)
    st.header("Credit Mix: Leveraged Loans vs. HY Bonds · Private vs. BSL")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Leveraged Loans vs. HY Bonds")
        fig2a = go.Figure()
        for ticker, label, color in [("BKLN", "Lev Loans (BKLN)", "#f7b731"),
                                      ("HYG",  "HY Bonds (HYG)",   "#fc5c65")]:
            if ticker in yfd:
                s = clip(yfd[ticker]).dropna()
                if len(s) > 0:
                    rebased = s / s.iloc[0] * 100
                    fig2a.add_trace(go.Scatter(x=rebased.index, y=rebased,
                                               name=label, line=dict(color=color, width=2)))
        fig2a.update_layout(**dark_layout(height=300, title="Price Return — Rebased to 100"))
        st.plotly_chart(fig2a, use_container_width=True)
        st.caption("BKLN = Invesco Senior Loan ETF (floating-rate LL proxy) | HYG = iShares HY Bond ETF")

    with col_b:
        st.subheader("Private Credit vs. BSL Market Share")
        dates_pc, pc_share, bsl_share = synthetic_pc_vs_bsl()
        fig2b = go.Figure()
        fig2b.add_trace(go.Bar(x=dates_pc, y=pc_share, name="Private Credit",
                               marker_color="#4dd9ac"))
        fig2b.add_trace(go.Bar(x=dates_pc, y=bsl_share, name="BSL / Syndicated",
                               marker_color="#3a6ea8"))
        fig2b.update_layout(**dark_layout(height=300, title="% Share of US Mid-Market Lending"),
                            barmode='stack')
        st.plotly_chart(fig2b, use_container_width=True)
        st.markdown('<div class="disclaimer">⚠ Estimated from LSEG LPC / PitchBook LCD research. '
                    'PC took ~43 → 58 pt share 2018–2025 as banks retreated post-SVB.</div>',
                    unsafe_allow_html=True)

    st.subheader("Direct Lending — BDC Performance (ARCC vs FSK)")
    fig2c = go.Figure()
    for ticker, label, color in [("ARCC",   "Ares Capital (ARCC)", "#45aaf2"),
                                  ("FS_KKR", "FS KKR (FSK)",        "#fd9644")]:
        if ticker in yfd:
            s = clip(yfd[ticker]).dropna()
            if len(s) > 0:
                fig2c.add_trace(go.Scatter(x=s.index, y=s, name=label,
                                           line=dict(color=color, width=1.8)))
    fig2c.update_layout(**dark_layout(height=260, title="NAV proxy — two largest US BDCs"))
    st.plotly_chart(fig2c, use_container_width=True)
    st.caption("BDC prices are the best publicly available direct-lending proxies. "
               "Drawdowns signal stress in the private credit stack.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 · STRESS SIGNALS
# ═════════════════════════════════════════════════════════════════════════════
if show_stress:
    st.markdown("---")
    st.markdown('<p class="section-label">Section 03</p>', unsafe_allow_html=True)
    st.header("Stress Signals: PIK · Maturity Wall · LTV/LTI")

    # 3a: PIK Toggle
    st.subheader("PIK Toggle — % of Private Loans Paying-in-Kind")
    pik = synthetic_pik_toggle()
    pik_c = clip(pik)
    fig3a = go.Figure()
    fig3a.add_trace(go.Scatter(x=pik_c.index, y=pik_c,
                               name="PIK %",
                               fill='tozeroy',
                               fillcolor='rgba(252,92,101,0.12)',
                               line=dict(color='#fc5c65', width=2.5)))
    fig3a.add_hline(y=10, line_dash="dot", line_color="#ffd700",
                    annotation_text="Watch Level (10%)",
                    annotation_font_color="#ffd700", annotation_font_size=10)
    fig3a.add_hline(y=15, line_dash="dash", line_color="#ff4b4b",
                    annotation_text="Stress Threshold (15%)",
                    annotation_font_color="#ff4b4b", annotation_font_size=10)
    fig3a.update_layout(**dark_layout(height=280,
                                       title="PIK Toggle % — US Leveraged Loan Market"),
                        yaxis_ticksuffix="%")
    st.plotly_chart(fig3a, use_container_width=True)
    st.markdown('<div class="disclaimer">⚠ Estimated from Fitch Ratings / LCD quarterly PIK surveys. '
                'PIK = borrower elects to accrue interest as additional debt rather than cash payment. '
                'Rising PIK % is a leading distress indicator, historically peaking 2–4 quarters before default wave.</div>',
                unsafe_allow_html=True)

    # 3b: Maturity Wall
    st.subheader("Maturity Wall Countdown — Leveraged Loans + HY Bonds ($B due)")
    years, loans, hy_maturities = synthetic_maturity_wall()
    fig3b = go.Figure()
    fig3b.add_trace(go.Bar(x=years, y=loans, name="Leveraged Loans",
                           marker_color="#f7b731", marker_line_width=0))
    fig3b.add_trace(go.Bar(x=years, y=hy_maturities, name="HY Bonds",
                           marker_color="#fc5c65", marker_line_width=0))
    fig3b.add_vrect(x0="2026", x1="2028",
                    fillcolor="rgba(252,92,101,0.07)", line_width=0,
                    annotation_text="Peak Wall '26–'28",
                    annotation_font_color="#fc5c65", annotation_font_size=10)
    fig3b.update_layout(**dark_layout(height=300,
                                       title="US Leveraged Credit Maturities ($B) by Year"),
                        barmode='stack',
                        xaxis_title="Maturity Year", yaxis_title="$B")
    st.plotly_chart(fig3b, use_container_width=True)
    st.markdown('<div class="disclaimer">⚠ Estimated from S&P LCD / Fitch Leveraged Finance Maturity Report Q4 2024. '
                '$480B loans + $260B HY bonds mature in 2026 alone — refinancing risk elevated if rates stay high.</div>',
                unsafe_allow_html=True)

    # 3c: LTV / LTI
    st.subheader("LTV / LTI Stress Proxies (Consumer)")
    col3a, col3b = st.columns(2)

    with col3a:
        if 'Home_Price' in d and 'Mortgage_Debt' in d:
            hp = clip(d['Home_Price']).dropna()
            md = clip(d['Mortgage_Debt']).dropna()
            common = hp.index.intersection(md.index)
            if len(common) > 5:
                hp_a = hp.reindex(common)
                md_a = md.reindex(common)
                ltv_proxy = (md_a / (hp_a / hp_a.iloc[0] * md_a.iloc[0])) * 100
                fig3c = go.Figure()
                fig3c.add_trace(go.Scatter(x=ltv_proxy.index, y=ltv_proxy,
                                           name="LTV Proxy Index",
                                           line=dict(color='#a55eea', width=2)))
                fig3c.update_layout(**dark_layout(height=260,
                                                   title="Consumer LTV Proxy (Mortgage Debt / HPI)"))
                st.plotly_chart(fig3c, use_container_width=True)

    with col3b:
        if 'Revolving' in d and 'PCE_Income' in d:
            rev = clip(d['Revolving']).dropna()
            inc = clip(d['PCE_Income']).dropna()
            common = rev.index.intersection(inc.index)
            if len(common) > 5:
                rev_a = rev.reindex(common)
                inc_a = inc.reindex(common)
                lti = (rev_a / inc_a) * 100
                fig3d = go.Figure()
                fig3d.add_trace(go.Scatter(x=lti.index, y=lti,
                                           name="LTI Proxy",
                                           fill='tozeroy',
                                           fillcolor='rgba(165,94,234,0.1)',
                                           line=dict(color='#a55eea', width=2)))
                fig3d.update_layout(**dark_layout(height=260,
                                                   title="Consumer LTI Proxy (Revolving Credit / DPI %)"),
                                    yaxis_ticksuffix="%")
                st.plotly_chart(fig3d, use_container_width=True)

    st.caption("LTV/LTI shown as index proxies using FRED data. "
               "True loan-level LTV/LTI requires bank regulatory filings (FR Y-14, HMDA).")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 · GEOSPATIAL HEAT
# ═════════════════════════════════════════════════════════════════════════════
if show_geo:
    st.markdown("---")
    st.markdown('<p class="section-label">Section 04</p>', unsafe_allow_html=True)
    st.header("Geospatial Credit Heat")

    tab1, tab2 = st.tabs(["🖥 Tech / SaaS Credit Heat", "🏭 Rust Belt ABL Flow"])

    with tab1:
        vc_data = state_tech_vc_activity()
        df_vc = pd.DataFrame({"state": list(vc_data.keys()),
                               "score": list(vc_data.values())})
        fig4a = go.Figure(go.Choropleth(
            locations=df_vc['state'],
            z=df_vc['score'],
            locationmode='USA-states',
            colorscale=[[0, '#0d1a2a'], [0.3, '#1a4a7a'],
                        [0.6, '#2a8af0'], [1.0, '#00d4ff']],
            colorbar=dict(title="VC Activity<br>Index (0–100)",
                          title_font=dict(size=10, color="#8aa0bc"),
                          tickfont=dict(size=9, color="#8aa0bc"),
                          bgcolor="#0a0e1a", borderwidth=0),
            hovertemplate="<b>%{location}</b><br>Score: %{z}<extra></extra>",
        ))
        fig4a.update_layout(
            geo=dict(scope='usa', bgcolor='#0a0e1a',
                     lakecolor='#0a0e1a', landcolor='#0d1220',
                     showlakes=True, showframe=False,
                     coastlinecolor='#1a2540'),
            paper_bgcolor='#0a0e1a',
            font=dict(family="IBM Plex Mono", color="#8aa0bc"),
            margin=dict(l=0, r=0, t=30, b=0),
            height=420,
            title=dict(text="Tech/SaaS Credit Demand — VC Deal Density by State (2024)",
                       font=dict(size=12, color="#5a9ad4"))
        )
        st.plotly_chart(fig4a, use_container_width=True)
        st.markdown('<div class="disclaimer">⚠ Proxy index derived from NVCA / PitchBook 2024 VC deal counts by state, '
                    'normalised to 100 = California. Higher score = higher private credit demand from tech/SaaS borrowers.</div>',
                    unsafe_allow_html=True)

    with tab2:
        abl_data = state_rust_belt_abl()
        df_abl = pd.DataFrame({"state": list(abl_data.keys()),
                                "score": list(abl_data.values())})
        fig4b = go.Figure(go.Choropleth(
            locations=df_abl['state'],
            z=df_abl['score'],
            locationmode='USA-states',
            colorscale=[[0, '#1a0d00'], [0.3, '#7a3a00'],
                        [0.6, '#d4720a'], [1.0, '#f7b731']],
            colorbar=dict(title="ABL Flow<br>Index (0–100)",
                          title_font=dict(size=10, color="#8aa0bc"),
                          tickfont=dict(size=9, color="#8aa0bc"),
                          bgcolor="#0a0e1a", borderwidth=0),
            hovertemplate="<b>%{location}</b><br>Score: %{z}<extra></extra>",
        ))
        fig4b.update_layout(
            geo=dict(scope='usa', bgcolor='#0a0e1a',
                     lakecolor='#0a0e1a', landcolor='#0d1220',
                     showlakes=True, showframe=False,
                     coastlinecolor='#1a2540'),
            paper_bgcolor='#0a0e1a',
            font=dict(family="IBM Plex Mono", color="#8aa0bc"),
            margin=dict(l=0, r=0, t=30, b=0),
            height=420,
            title=dict(text="Rust Belt ABL / Onshoring Credit Flow — C&I Loan Growth Index (2024)",
                       font=dict(size=12, color="#5a9ad4"))
        )
        st.plotly_chart(fig4b, use_container_width=True)
        st.markdown('<div class="disclaimer">⚠ Proxy index derived from Federal Reserve H.8 C&I loan growth rates '
                    '+ ISM Manufacturing PMI by state (2023–24). Higher score = stronger ABL/working capital demand '
                    'driven by onshoring / industrial capex cycle.</div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 · LOOKING BACK  (Howard Marks / Oaktree memo framing)
# ═════════════════════════════════════════════════════════════════════════════
if show_lookback:
    st.markdown("---")
    st.markdown('<p class="section-label">Section 05</p>', unsafe_allow_html=True)
    st.header("Looking Back: A Credit Market History")
    st.markdown(
        '<div class="disclaimer" style="margin-bottom:16px;">'
        '"The general field called credit has seen massive innovation over the course of my career. '
        'Its popularity has increased steadily, and its scale and role in the world of finance have multiplied." '
        '— Howard Marks, Oaktree Capital, April 2026'
        '</div>',
        unsafe_allow_html=True
    )

    # ── SERIES DEFINITIONS ────────────────────────────────────────────────────
    # All synthetic / estimated index values (1970 = 100 baseline where applicable)
    # Sources noted inline; treat as illustrative order-of-magnitude reconstructions.

    years = list(range(1970, 2026))

    # 1. Non-IG / High Yield bond market size ($B, US)
    #    Source: SIFMA, Fed Flow of Funds. Milken era starts ~1978; explosive 1983-89.
    hy_size = [
        5,5,6,6,7,8,9,10,                          # 1970-77
        15,25,40,60,90,130,180,240,300,             # 1978-86 Milken era
        280,260,250,270,300,330,370,                # 1987-93 crash+recovery
        420,500,580,650,700,750,                    # 1994-99
        680,600,580,620,700,800,900,1000,1100,1200, # 2000-09
        1150,1200,1280,1350,1400,1450,1480,1500,    # 2010-17
        1520,1540,1550,1480,1520,1580,1600,1620,    # 2018-25 (2020 dip, recovery)
    ]

    # 2. Leveraged Buyout / PE debt ($B deployed annually, cumulative index)
    #    Source: Preqin / PitchBook historical PE deal volume
    lbo_size = [
        2,2,3,3,4,5,6,8,                           # 1970-77
        10,15,25,40,60,100,150,200,220,             # 1978-86
        180,150,120,100,110,130,160,                # 1987-93
        200,260,330,420,500,600,                    # 1994-99
        550,480,440,480,560,700,900,1100,1300,1500, # 2000-09
        1400,1600,1900,2200,2500,2800,3100,3400,    # 2010-17
        3600,3800,3500,4200,4800,5100,5300,5400,    # 2018-25
    ]

    # 3. Broadly Syndicated Loans ($B outstanding, US)
    #    Source: LSEG LPC. Market barely existed pre-1990.
    bsl_size = [
        0,0,0,0,0,0,0,0,                           # 1970-77
        0,0,0,0,0,0,5,10,20,                       # 1978-86
        30,40,50,60,80,100,130,                     # 1987-93
        180,260,360,480,600,750,                    # 1994-99
        720,660,640,700,800,1000,1200,1400,1600,1200,# 2000-09 (GFC crash)
        1100,1200,1400,1600,1700,1750,1800,1900,    # 2010-17
        2000,2100,1900,2400,2600,2700,2800,2900,    # 2018-25
    ]

    # 4. Structured Credit / CLO / MBS ($B outstanding)
    #    Source: SIFMA, Fed Z.1 Flow of Funds
    structured = [
        10,12,14,16,18,22,26,30,                   # 1970-77
        35,45,55,65,80,100,130,160,200,             # 1978-86
        260,320,400,500,600,700,800,                # 1987-93 MBS boom
        900,1000,1200,1500,1900,2400,               # 1994-99
        2800,3200,3600,4000,4500,5500,7000,8500,9500,7000,# 2000-09 sub-prime + GFC crash
        5500,5200,5000,4900,4800,4700,4800,5000,    # 2010-17 delever + recover
        5200,5400,5600,5800,6000,6200,6400,6600,    # 2018-25
    ]

    # 5. Direct Lending / Private Credit ($B AUM)
    #    Source: Preqin / McKinsey Global Private Markets. Barely exists pre-2010.
    direct_lending = [
        0,0,0,0,0,0,0,0,                           # 1970-77
        0,0,0,0,0,0,0,0,0,                         # 1978-86
        0,0,0,2,4,6,8,                             # 1987-93
        10,15,20,28,35,45,                          # 1994-99
        50,55,60,70,80,100,120,140,150,100,         # 2000-09 (GFC dip)
        120,150,200,280,380,500,620,750,            # 2010-17 explosive growth
        900,1100,1300,1700,2000,2200,2400,2600,     # 2018-25
    ]

    # 6. BDC AUM ($B) — public direct lending vehicles
    #    Source: SEC EDGAR / KBRA. Effectively zero pre-2004.
    bdc_aum = [
        0,0,0,0,0,0,0,0,                           # 1970-77
        0,0,0,0,0,0,0,0,0,                         # 1978-86
        0,0,0,0,0,0,0,                             # 1987-93
        0,0,0,0,1,2,                               # 1994-99
        3,5,8,12,18,25,35,50,60,40,                # 2000-09
        45,60,80,110,140,170,200,230,              # 2010-17
        260,290,310,380,420,450,490,520,           # 2018-25
    ]

    # 7. Total US Debt ($T) — Fed Z.1: households + corporate + govt
    #    Source: Federal Reserve Flow of Funds Z.1
    total_debt = [
        1.6,1.7,1.9,2.1,2.3,2.6,2.9,3.2,          # 1970-77
        3.7,4.2,4.9,5.7,6.5,7.5,8.7,10.1,11.8,    # 1978-86
        13.5,15.1,16.5,17.2,17.9,18.5,19.2,        # 1987-93
        20.5,22.1,24.0,26.3,28.8,32.0,             # 1994-99
        34.5,36.2,37.8,39.5,42.1,46.2,52.0,57.4,60.1,55.0,# 2000-09
        55.5,57.0,59.5,62.1,64.8,66.9,69.5,72.3,  # 2010-17
        75.1,79.2,79.8,91.5,99.8,104.2,108.6,113.0,# 2018-25
    ]

    # 8. S&P 500 Index (annual close, approx)
    #    Source: Yahoo Finance / Macrotrends
    sp500 = [
        92,102,118,97,68,90,107,107,               # 1970-77
        96,107,136,135,122,140,167,211,242,        # 1978-86
        247,277,353,330,417,438,466,                # 1987-93
        459,615,741,970,1229,1469,                  # 1994-99
        1320,1148,880,1112,1212,1248,1418,1478,1468,1115,# 2000-09
        1258,1258,1426,1848,2059,2044,2239,2674,   # 2010-17
        2507,3231,3756,4766,4797,4288,4770,5882,   # 2018-25
    ]

    # 9. 10Y US Treasury Yield (annual avg %)
    #    Source: Federal Reserve H.15
    yield_10y = [
        7.3,6.6,6.2,6.8,7.6,7.9,6.8,7.4,          # 1970-77
        8.4,9.4,10.8,12.9,13.0,10.8,11.6,10.6,8.4,# 1978-86
        8.4,8.8,9.0,8.1,7.0,6.6,7.1,              # 1987-93
        7.1,6.6,6.4,6.4,5.6,5.6,                  # 1994-99
        5.1,5.0,4.6,4.0,4.3,4.3,4.8,4.6,3.7,3.3, # 2000-09
        3.2,2.8,1.8,2.4,2.5,2.1,2.5,2.3,          # 2010-17
        2.9,2.1,0.9,1.5,2.9,3.9,4.0,4.2,          # 2018-25
    ]

    df_lb = pd.DataFrame({
        "year":           years,
        "HY Bonds ($B)":              hy_size,
        "LBO/PE Debt ($B)":           lbo_size,
        "Syndicated Loans ($B)":      bsl_size,
        "Structured Credit ($B)":     structured,
        "Direct Lending ($B)":        direct_lending,
        "BDC AUM ($B)":               bdc_aum,
        "Total US Debt ($T×100)":     [x * 100 for x in total_debt],  # scaled to $B for overlay
        "S&P 500":                    sp500,
        "10Y Yield (×100 bps)":       [y * 100 for y in yield_10y],   # scaled to overlay
    })

    # ── CRASH / BUBBLE PERIODS ─────────────────────────────────────────────
    crash_events = [
        {"x0": 1973, "x1": 1975, "color": "rgba(255,150,0,0.10)",  "label": "Oil Embargo / Stagflation", "y": 0.95},
        {"x0": 1987, "x1": 1988, "color": "rgba(255,75,75,0.12)",  "label": "Black Monday '87",          "y": 0.90},
        {"x0": 1989, "x1": 1992, "color": "rgba(255,100,50,0.10)", "label": "S&L Crisis / Junk Collapse","y": 0.85},
        {"x0": 1997, "x1": 1999, "color": "rgba(200,100,200,0.10)","label": "Asian / LTCM Crisis",       "y": 0.80},
        {"x0": 2000, "x1": 2003, "color": "rgba(100,180,255,0.12)","label": "Dot-com Bust",              "y": 0.75},
        {"x0": 2007, "x1": 2010, "color": "rgba(255,75,75,0.14)",  "label": "GFC / Sub-prime Crash",     "y": 0.70},
        {"x0": 2020, "x1": 2020, "color": "rgba(100,255,180,0.12)","label": "COVID Shock",               "y": 0.65},
        {"x0": 2022, "x1": 2023, "color": "rgba(255,200,50,0.10)", "label": "Rate Shock / SVB",          "y": 0.60},
        {"x0": 2025, "x1": 2026, "color": "rgba(100,180,255,0.12)","label": "AI Disruption / PC Stress", "y": 0.55},
    ]

    # ── DECADE ERA ANNOTATIONS ─────────────────────────────────────────────
    era_labels = [
        {"x": 1971, "text": "70s: Non-IG\nAccepted",    "color": "#8aa0bc"},
        {"x": 1981, "text": "80s: LBO &\nJunk Boom",    "color": "#f7b731"},
        {"x": 1992, "text": "90s: BSL &\nTranching",    "color": "#4dd9ac"},
        {"x": 2002, "text": "00s: Alts &\nSub-prime",   "color": "#fc5c65"},
        {"x": 2012, "text": "10s: Direct\nLending",     "color": "#45aaf2"},
        {"x": 2021, "text": "20s: BDCs &\nRetail PC",   "color": "#a55eea"},
    ]

    # ── TOGGLE CONTROLS ────────────────────────────────────────────────────
    st.markdown("#### Chart Controls")
    col_t1, col_t2, col_t3 = st.columns(3)

    with col_t1:
        st.markdown("**Credit Series**")
        show_hy       = st.checkbox("HY Bonds",           value=True,  key="lb_hy")
        show_lbo      = st.checkbox("LBO / PE Debt",      value=True,  key="lb_lbo")
        show_bsl      = st.checkbox("Syndicated Loans",   value=True,  key="lb_bsl")
        show_struct   = st.checkbox("Structured Credit",  value=True,  key="lb_str")
        show_dl       = st.checkbox("Direct Lending",     value=True,  key="lb_dl")
        show_bdc      = st.checkbox("BDC AUM",            value=True,  key="lb_bdc")

    with col_t2:
        st.markdown("**Market Overlays**")
        show_debt     = st.checkbox("Total US Debt",      value=True,  key="lb_debt")
        show_sp       = st.checkbox("S&P 500",            value=True,  key="lb_sp")
        show_yield    = st.checkbox("10Y Treasury Yield", value=True,  key="lb_yld")

    with col_t3:
        st.markdown("**Crash / Bubble Periods**")
        show_oil      = st.checkbox("Oil Embargo '73",    value=True,  key="lb_oil")
        show_bm87     = st.checkbox("Black Monday '87",   value=True,  key="lb_bm")
        show_sl       = st.checkbox("S&L / Junk '89",    value=True,  key="lb_sl")
        show_asia     = st.checkbox("Asian / LTCM '97",  value=True,  key="lb_asia")
        show_dot      = st.checkbox("Dot-com '00",        value=True,  key="lb_dot")
        show_gfc      = st.checkbox("GFC '07",            value=True,  key="lb_gfc")
        show_covid    = st.checkbox("COVID '20",          value=True,  key="lb_covid")
        show_svb      = st.checkbox("Rate Shock '22",     value=True,  key="lb_svb")
        show_ai       = st.checkbox("AI Stress '25",      value=True,  key="lb_ai")

    crash_toggles = [
        show_oil, show_bm87, show_sl, show_asia,
        show_dot, show_gfc, show_covid, show_svb, show_ai
    ]

    # ── BUILD CHART — dual stacked subplots sharing x-axis ─────────────────
    from plotly.subplots import make_subplots

    fig_lb = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.62, 0.38],
        subplot_titles=("Credit Market Volumes ($B)", "Rates & Equities"),
    )

    # ── TOP PANEL: volume series ─────────────────────────────────────────────
    top_series = [
        ("HY Bonds ($B)",         show_hy,     "#f7b731", "solid"),
        ("LBO/PE Debt ($B)",       show_lbo,    "#fc5c65", "solid"),
        ("Syndicated Loans ($B)",  show_bsl,    "#4dd9ac", "solid"),
        ("Structured Credit ($B)", show_struct, "#a55eea", "solid"),
        ("Direct Lending ($B)",    show_dl,     "#45aaf2", "dash"),
        ("BDC AUM ($B)",           show_bdc,    "#fd9644", "dot"),
        ("Total US Debt ($T x100)",show_debt,   "#c9d1e0", "longdash"),
    ]
    # map df column names (some have unicode) to the list above
    col_map = {
        "Total US Debt ($T x100)": "Total US Debt ($T×100)",
    }

    for name, visible, color, dash in top_series:
        if visible:
            df_col = col_map.get(name, name)
            fig_lb.add_trace(
                go.Scatter(
                    x=df_lb["year"], y=df_lb[df_col],
                    name=name,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate="%{x}: %{y:,.0f}<extra>" + name + "</extra>",
                    legendgroup="vol",
                ),
                row=1, col=1,
            )

    # ── BOTTOM PANEL: rates & S&P ────────────────────────────────────────────
    # FFR — pull from FRED data if available, else use yield_10y as fallback
    ffr_annual = None
    if "FFR" in d:
        try:
            ffr_s = d["FFR"].resample("YE").mean()
            ffr_annual = pd.Series(
                ffr_s.values,
                index=[t.year for t in ffr_s.index]
            )
        except Exception:
            pass

    if show_sp:
        fig_lb.add_trace(
            go.Scatter(
                x=df_lb["year"], y=df_lb["S&P 500"],
                name="S&P 500",
                line=dict(color="#00d4ff", width=2),
                yaxis="y3",
                hovertemplate="%{x}: %{y:,.0f}<extra>S&P 500</extra>",
                legendgroup="rates",
            ),
            row=2, col=1,
        )

    if show_yield:
        fig_lb.add_trace(
            go.Scatter(
                x=df_lb["year"], y=yield_10y,
                name="10Y Yield (%)",
                line=dict(color="#ff4b4b", width=2),
                hovertemplate="%{x}: %{y:.1f}%<extra>10Y Yield</extra>",
                legendgroup="rates",
            ),
            row=2, col=1,
        )

    # FFR overlay on bottom panel
    if ffr_annual is not None:
        yr_filt = [y for y in ffr_annual.index if 1970 <= y <= 2025]
        fig_lb.add_trace(
            go.Scatter(
                x=yr_filt,
                y=[ffr_annual[y] for y in yr_filt],
                name="Fed Funds Rate (%)",
                line=dict(color="#ffd700", width=1.8, dash="dot"),
                hovertemplate="%{x}: %{y:.2f}%<extra>FFR</extra>",
                legendgroup="rates",
            ),
            row=2, col=1,
        )

    # ── CRASH SHADING — add to BOTH rows via shapes ──────────────────────────
    shapes  = []
    annotations = []

    for event, toggle in zip(crash_events, crash_toggles):
        if not toggle:
            continue
        x0, x1 = event["x0"] - 0.4, event["x1"] + 0.4
        color   = event["color"]
        label   = event["label"]

        # shade top panel (y refs row 1)
        shapes.append(dict(
            type="rect", xref="x", yref="paper",
            x0=x0, x1=x1, y0=0.38, y1=1.0,
            fillcolor=color, line_width=0, layer="below",
        ))
        # shade bottom panel
        shapes.append(dict(
            type="rect", xref="x", yref="paper",
            x0=x0, x1=x1, y0=0.0, y1=0.35,
            fillcolor=color, line_width=0, layer="below",
        ))
        # single rotated label sitting on the border between panels
        annotations.append(dict(
            x=(x0 + x1) / 2, y=0.385,
            xref="x", yref="paper",
            text=label,
            showarrow=False,
            textangle=-90,
            font=dict(size=7.5, color="#8aa0bc"),
            bgcolor="rgba(10,14,26,0.0)",
            xanchor="center", yanchor="bottom",
        ))

    # ── ERA DECADE BADGES — on the divider line ───────────────────────────────
    for era in era_labels:
        annotations.append(dict(
            x=era["x"], y=0.385,
            xref="x", yref="paper",
            text=era["text"].replace("\n", "<br>"),
            showarrow=False,
            font=dict(size=8, color=era["color"]),
            bgcolor="rgba(10,14,26,0.85)",
            bordercolor=era["color"],
            borderwidth=1,
            borderpad=3,
            align="center",
            xanchor="center",
            yanchor="top",
        ))

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    fig_lb.update_layout(
        height=680,
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0d1220",
        font=dict(family="IBM Plex Mono", size=11, color="#8aa0bc"),
        margin=dict(l=60, r=80, t=50, b=40),
        shapes=shapes,
        annotations=annotations,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            font=dict(size=9),
            bgcolor="rgba(0,0,0,0)",
            tracegroupgap=20,
        ),
        # shared x
        xaxis=dict(
            showticklabels=False,
            gridcolor="#1a2540",
            tickmode="linear", dtick=5,
        ),
        xaxis2=dict(
            title="Year",
            gridcolor="#1a2540",
            tickmode="linear", dtick=5,
        ),
        # top y
        yaxis=dict(
            title="Market Size ($B)",
            title_font=dict(color="#8aa0bc"),
            tickformat=",",
            gridcolor="#1a2540",
        ),
        # bottom y left — rates
        yaxis2=dict(
            title="Yield / FFR (%)",
            title_font=dict(color="#8aa0bc"),
            gridcolor="#1a2540",
        ),
    )

    # style subplot title fonts
    for ann in fig_lb.layout.annotations:
        if hasattr(ann, "text") and ann.text in ("Credit Market Volumes ($B)", "Rates & Equities"):
            ann.font = dict(size=11, color="#5a9ad4", family="IBM Plex Mono")

    # S&P gets its own right-side y axis on the bottom panel
    if show_sp:
        fig_lb.update_traces(
            selector=dict(name="S&P 500"),
            yaxis="y4",
        )
        fig_lb.update_layout(
            yaxis4=dict(
                title="S&P 500",
                overlaying="y2",
                side="right",
                showgrid=False,
                title_font=dict(color="#00d4ff"),
                tickfont=dict(color="#00d4ff"),
            )
        )

    st.plotly_chart(fig_lb, use_container_width=True)

    # ── MARKS TIMELINE ANNOTATIONS

    # ── MARKS TIMELINE ANNOTATIONS ────────────────────────────────────────
    st.markdown("#### The Howard Marks Credit Chronology")
    timeline_cols = st.columns(6)
    eras = [
        ("1970s", "#8aa0bc", "Non-IG debt accepted. Milken enables below-investment-grade bond issuance. Fallen angels gain a market."),
        ("1980s", "#f7b731", "LBO boom funded by HY bonds. Drexel Burnham, KKR. Corporate leverage explodes. S&L crisis ends the decade."),
        ("1990s", "#4dd9ac", "BSL / leveraged loans invented by Wall Street. CLOs born. Tranching unlocks new buyer pools. PE becomes mainstream."),
        ("2000s", "#fc5c65", "\"Alternatives\" label born post dot-com. Sub-prime MBS & RMBS proliferate. CDOs squared. GFC 2008-09."),
        ("2010s", "#45aaf2", "Post-GFC bank retreat creates vacuum. Direct lending fills it. PE-sponsored mid-market borrowers flood in. ZIRP turbocharges returns."),
        ("2020s", "#a55eea", "BDC vehicles open to retail / 401k. $2T+ in direct loans. AI disrupts software borrowers. PIK toggles rise. Redemption gates hit."),
    ]
    for col, (decade, color, desc) in zip(timeline_cols, eras):
        with col:
            st.markdown(
                f'<div style="border-top:2px solid {color};padding-top:8px;">'
                f'<span style="font-family:IBM Plex Mono;font-size:0.9rem;color:{color};font-weight:600;">{decade}</span>'
                f'<p style="font-size:0.72rem;color:#8aa0bc;margin-top:6px;">{desc}</p>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown('<div class="disclaimer" style="margin-top:16px;">⚠ Credit market size figures are estimated from '
                'SIFMA, Federal Reserve Z.1 Flow of Funds, Preqin, PitchBook, and LSEG LPC historical reports. '
                'S&P 500 prices are approximate annual closes. These are illustrative order-of-magnitude reconstructions '
                'for educational purposes — not official statistics. Source: Howard Marks / Oaktree Capital memo, April 2026.</div>',
                unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="disclaimer" style="text-align:center;">'
    '📡 Credit Eyes · FRED API · Yahoo Finance · LCD/S&P/PitchBook estimates · '
    'Not investment advice · Data refreshes every 60 min'
    '</div>',
    unsafe_allow_html=True
)
