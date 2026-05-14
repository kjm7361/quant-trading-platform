import streamlit as st

def setup_page(title, subtitle="", icon="📊"):
    st.set_page_config(page_title=title, layout="wide")

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        h1 {
            font-size: 2.4rem !important;
            font-weight: 850 !important;
            letter-spacing: -0.04em;
            color: #111827;
        }

        h2, h3 {
            font-weight: 750 !important;
            color: #1f2937;
        }

        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.85);
            border: 1px solid rgba(148,163,184,0.25);
            padding: 18px 20px;
            border-radius: 18px;
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.85rem;
            color: #64748b;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.65rem;
            font-weight: 800;
            color: #0f172a;
        }

        section[data-testid="stSidebar"] {
            background: #0f172a;
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }

        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] select {
            color: #111827 !important;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 700;
            border: 1px solid #2563eb;
            background: linear-gradient(135deg, #2563eb, #4f46e5);
            color: white;
            transition: 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(37,99,235,0.25);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(148,163,184,0.25);
            box-shadow: 0 8px 22px rgba(15,23,42,0.05);
        }

        .hero-card {
            background: linear-gradient(135deg, #111827, #1e3a8a);
            padding: 28px 32px;
            border-radius: 24px;
            color: white;
            box-shadow: 0 18px 45px rgba(15,23,42,0.22);
            margin-bottom: 24px;
        }

        .hero-title {
            font-size: 2.1rem;
            font-weight: 850;
            margin-bottom: 6px;
        }

        .hero-subtitle {
            color: #dbeafe;
            font-size: 1rem;
        }

        .section-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 18px;
            padding: 18px 20px;
            margin: 14px 0 18px 0;
            box-shadow: 0 8px 22px rgba(15,23,42,0.04);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="hero-card">
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
            <h3 style="margin-bottom: 0.25rem;">{title}</h3>
            <p style="color:#64748b; margin-bottom:0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def next_step(text):
    st.divider()
    st.subheader("Next Step")
    st.info(text)