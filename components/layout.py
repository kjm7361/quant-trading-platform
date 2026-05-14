import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(16,185,129,0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(59,130,246,0.20), transparent 30%),
                linear-gradient(135deg, #f8fafc 0%, #eef2ff 55%, #f0fdf4 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1450px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020617 0%, #0f172a 50%, #064e3b 100%);
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }

        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            background: rgba(255,255,255,0.95) !important;
            color: #0f172a !important;
            border-radius: 12px !important;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(240,253,244,0.92));
            border: 1px solid rgba(148,163,184,0.28);
            padding: 18px 20px;
            border-radius: 20px;
            box-shadow: 0 12px 30px rgba(15,23,42,0.08);
        }

        .hero-card {
            background: linear-gradient(135deg, #020617, #1e3a8a, #059669);
            padding: 34px 38px;
            border-radius: 30px;
            color: white;
            box-shadow: 0 24px 60px rgba(15,23,42,0.28);
            margin-bottom: 28px;
        }

        .hero-title {
            font-size: 2.35rem;
            font-weight: 900;
            letter-spacing: -0.04em;
            margin-bottom: 8px;
        }

        .hero-subtitle {
            color: #dbeafe;
            font-size: 1rem;
        }

        .section-card {
            background: rgba(255,255,255,0.9);
            border-left: 6px solid #10b981;
            border-radius: 20px;
            padding: 18px 22px;
            margin: 18px 0;
            box-shadow: 0 10px 30px rgba(15,23,42,0.07);
        }

        .brand-box {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 18px;
        }

        .brand-title {
            font-size: 1.1rem;
            font-weight: 900;
            color: white;
        }

        .brand-subtitle {
            font-size: 0.78rem;
            color: #bbf7d0;
            margin-top: 4px;
        }

        .ticker-strip {
            background: #020617;
            color: white;
            border-radius: 18px;
            padding: 12px 18px;
            margin-bottom: 18px;
            box-shadow: 0 10px 26px rgba(15,23,42,0.18);
            overflow: hidden;
            white-space: nowrap;
        }

        .ticker-positive {
            color: #86efac;
            font-weight: 800;
            margin-right: 26px;
        }

        .ticker-negative {
            color: #fca5a5;
            font-weight: 800;
            margin-right: 26px;
        }

        .quick-card {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 14px;
            margin-top: 16px;
            margin-bottom: 18px;
        }

        .quick-title {
            font-weight: 900;
            color: white;
            margin-bottom: 10px;
        }

        .quick-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            margin-bottom: 6px;
        }

        .stButton > button {
            border-radius: 14px;
            font-weight: 800;
            border: none;
            color: white;
            background: linear-gradient(135deg, #2563eb, #10b981);
            box-shadow: 0 10px 24px rgba(37,99,235,0.28);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def sidebar_brand():
    st.sidebar.markdown(
        """
        <div class="brand-box">
            <div class="brand-title">⚡ Quant Terminal</div>
            <div class="brand-subtitle">Trading · Risk · Portfolio Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def market_ticker():
    st.markdown(
        """
        <div class="ticker-strip">
            <span class="ticker-positive">SPY +0.42%</span>
            <span class="ticker-positive">QQQ +0.68%</span>
            <span class="ticker-negative">IWM -0.21%</span>
            <span class="ticker-positive">NVDA +1.14%</span>
            <span class="ticker-negative">TSLA -0.76%</span>
            <span class="ticker-positive">AAPL +0.31%</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def quick_stats(equity="N/A", pnl="N/A", positions="N/A", status="Normal"):
    st.sidebar.markdown(
        f"""
        <div class="quick-card">
            <div class="quick-title">📊 Quick Stats</div>
            <div class="quick-row"><span>Equity</span><span>{equity}</span></div>
            <div class="quick-row"><span>Day P&L</span><span>{pnl}</span></div>
            <div class="quick-row"><span>Positions</span><span>{positions}</span></div>
            <div class="quick-row"><span>Status</span><span>{status}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )


def setup_page(title, subtitle="", icon="📊"):
    st.set_page_config(page_title=title, layout="wide")
    inject_global_css()
    sidebar_brand()
    market_ticker()

    st.markdown(
        f"""
        <div class="hero-card">
            <div style="font-size:0.85rem; font-weight:800; color:#bbf7d0; margin-bottom:10px;">
                LIVE QUANT TERMINAL · PYTHON · STREAMLIT · RISK ANALYTICS
            </div>
            <div class="hero-title">{icon} {title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section(title, subtitle=""):
    st.markdown(
        f"""
        <div class="section-card">
            <h3 style="margin-bottom:0.2rem;">{title}</h3>
            <p style="color:#64748b; margin-bottom:0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def next_step(text):
    st.divider()
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #ecfdf5, #eff6ff);
            border: 1px solid rgba(16,185,129,0.28);
            border-radius: 20px;
            padding: 22px;
            box-shadow: 0 10px 28px rgba(15,23,42,0.07);
        ">
            <h3 style="margin-bottom:6px;">🚀 Next Step</h3>
            <p style="margin-bottom:0; color:#334155;">{text}</p>
        </div>
        """,
        unsafe_allow_html=True
    )