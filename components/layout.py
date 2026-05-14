import streamlit as st

def setup_page(title, subtitle="", icon="📊"):
    st.set_page_config(page_title=title, layout="wide")

    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34,197,94,0.18), transparent 30%),
                radial-gradient(circle at top right, rgba(59,130,246,0.20), transparent 30%),
                linear-gradient(135deg, #f8fafc 0%, #eef2ff 55%, #f0fdf4 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1450px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020617 0%, #0f172a 48%, #064e3b 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
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

        .hero-card {
            background:
                linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,64,175,0.95), rgba(5,150,105,0.92));
            padding: 34px 38px;
            border-radius: 30px;
            color: white;
            box-shadow: 0 24px 60px rgba(15,23,42,0.28);
            margin-bottom: 28px;
            border: 1px solid rgba(255,255,255,0.14);
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
            max-width: 900px;
        }

        .section-card {
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(148,163,184,0.28);
            border-left: 6px solid #10b981;
            border-radius: 20px;
            padding: 18px 22px;
            margin: 18px 0;
            box-shadow: 0 10px 30px rgba(15,23,42,0.07);
        }

        .section-card h3 {
            margin-bottom: 0.2rem;
            color: #0f172a;
            font-weight: 850;
        }

        .section-card p {
            color: #64748b;
            margin-bottom: 0;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(240,253,244,0.9));
            border: 1px solid rgba(148,163,184,0.28);
            padding: 18px 20px;
            border-radius: 20px;
            box-shadow: 0 12px 30px rgba(15,23,42,0.08);
            transition: 0.2s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 18px 38px rgba(15,23,42,0.12);
        }

        [data-testid="stMetricLabel"] {
            color: #64748b !important;
            font-weight: 700;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.65rem;
            font-weight: 900;
            color: #0f172a;
        }

        .stButton > button {
            border-radius: 14px;
            font-weight: 800;
            border: none;
            color: white;
            background: linear-gradient(135deg, #2563eb, #10b981);
            box-shadow: 0 10px 24px rgba(37,99,235,0.28);
            transition: 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 34px rgba(16,185,129,0.32);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(148,163,184,0.28);
            box-shadow: 0 12px 32px rgba(15,23,42,0.07);
        }

        .stAlert {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

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
            <h3>{title}</h3>
            <p>{subtitle}</p>
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