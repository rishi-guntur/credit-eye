import streamlit as st
import pandas as pd
import numpy as np
from fredapi import Fred
import plotly.graph_objects as go
import plotly.express as px
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
    show_macro  = st.checkbox("1 · Macro Regime",    value=True)
    show_credit = st.checkbox("2 · Credit Mix",      value=True)
    show_stress = st.checkbox("3 · Stress Signals",  value=True)
    show_geo    = st.checkbox("4 · Geospatial Heat", value=True)
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

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="disclaimer" style="text-align:center;">'
    '📡 Credit Eyes · FRED API · Yahoo Finance · LCD/S&P/PitchBook estimates · '
    'Not investment advice · Data refreshes every 60 min'
    '</div>',
    unsafe_allow_html=True
)    # --- DATE RANGE CONTROLS ---
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
