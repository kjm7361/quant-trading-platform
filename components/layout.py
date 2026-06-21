"""
Bloomberg Terminal / BlackRock Aladdin inspired design system.
Single source of truth for all visual styling.
"""

import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import datetime, timezone
import pytz

# ── Palette ──────────────────────────────────────────────────────────────────
# Bloomberg Terminal inspired color system
_BG          = "#0A0F1A"                    # deep charcoal — page background
_BG_CARD     = "#0D1421"                    # card surface
_BG_SURF     = "#111C2E"                    # elevated surface / sidebar
_BG_HOVER    = "#162035"                    # hover state
_AMBER       = "#F59E0B"                    # Bloomberg amber — primary accent
_AMBER_DIM   = "#D97706"                    # amber dark
_AMBER_GLOW  = "rgba(245,158,11,0.10)"      # amber ambient glow
_AMBER_GLOW2 = "rgba(245,158,11,0.18)"      # stronger glow for hover
_CYAN        = "#06B6D4"                    # cyan — secondary accent
_CYAN_DIM    = "#0891B2"
_GREEN       = "#10B981"                    # gains / success
_GREEN_DIM   = "#059669"
_RED         = "#EF4444"                    # losses / danger
_RED_DIM     = "#DC2626"
_PURPLE      = "#8B5CF6"                    # portfolio / analytics
_TEXT_PRI    = "#E2E8F0"                    # primary text
_TEXT_SEC    = "#94A3B8"                    # secondary text
_TEXT_MUT    = "#475569"                    # muted / labels
_BORDER      = "rgba(245,158,11,0.14)"      # amber-tinted default border
_BORDER_DIM  = "rgba(51,65,85,0.50)"        # neutral border

# Back-compat aliases (referenced by existing page code)
_ACCENT      = _GREEN
_ACCENT_DIM  = _GREEN_DIM
_NAVY        = _BG
_SURFACE     = _BG_CARD
_SURFACE_LO  = "rgba(13,20,33,0.72)"
_MUTED       = _TEXT_MUT
_CARD        = _SURFACE_LO
_BLUE        = _CYAN


# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_global_css():
    st.markdown(
        f"""
        <style>
        /* ═══════════════════════════════════════════════════════════════════
           0.  FONTS — Inter UI + JetBrains Mono (terminal numerics)
        ═══════════════════════════════════════════════════════════════════ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        /* ═══════════════════════════════════════════════════════════════════
           1.  CSS ANIMATIONS
        ═══════════════════════════════════════════════════════════════════ */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(14px); }}
            to   {{ opacity: 1; transform: translateY(0);    }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; }} to {{ opacity: 1; }}
        }}
        @keyframes pulse-dot {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.55); }}
            50%       {{ box-shadow: 0 0 0 5px rgba(16,185,129,0);  }}
        }}
        @keyframes amber-pulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(245,158,11,0.55); }}
            50%       {{ box-shadow: 0 0 0 5px rgba(245,158,11,0);  }}
        }}
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }}
        }}
        @keyframes ticker-flow {{
            0%   {{ transform: translateX(0%);    }}
            100% {{ transform: translateX(-50%);  }}
        }}
        @keyframes shimmer {{
            0%   {{ background-position: -200% center; }}
            100% {{ background-position:  200% center; }}
        }}

        /* ═══════════════════════════════════════════════════════════════════
           2.  GLOBAL RESET + TYPOGRAPHY
        ═══════════════════════════════════════════════════════════════════ */
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', system-ui, sans-serif !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           3.  PAGE SHELL
        ═══════════════════════════════════════════════════════════════════ */
        .stApp {{
            background: {_BG} !important;
        }}

        /* subtle grid texture overlay */
        .stApp::before {{
            content: '';
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(245,158,11,0.015) 1px, transparent 1px),
                linear-gradient(90deg, rgba(245,158,11,0.015) 1px, transparent 1px);
            background-size: 48px 48px;
            pointer-events: none;
            z-index: 0;
        }}

        .block-container {{
            padding: 1.8rem 2.4rem 4rem !important;
            max-width: 1560px !important;
            animation: fadeInUp 0.35s ease both;
        }}

        /* Custom scrollbar */
        ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        ::-webkit-scrollbar-track {{ background: {_BG}; }}
        ::-webkit-scrollbar-thumb {{
            background: rgba(245,158,11,0.22);
            border-radius: 999px;
        }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(245,158,11,0.45); }}

        /* ═══════════════════════════════════════════════════════════════════
           4.  SIDEBAR — sleek terminal nav panel
        ═══════════════════════════════════════════════════════════════════ */
        /* hide default Streamlit auto-nav */
        [data-testid="stSidebarNav"] {{ display: none !important; }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #04080F 0%, #060B14 50%, #080E1A 100%) !important;
            border-right: 1px solid rgba(245,158,11,0.12) !important;
            box-shadow: 4px 0 32px rgba(0,0,0,0.5) !important;
        }}

        /* collapse arrow button — amber tinted */
        [data-testid="collapsedControl"] {{
            background: #060B14 !important;
            border-right: 1px solid rgba(245,158,11,0.10) !important;
        }}

        /* sidebar widget labels */
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] label {{
            color: {_TEXT_MUT} !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.10em !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {{
            background: rgba(10,15,26,0.90) !important;
            color: {_TEXT_PRI} !important;
            border: 1px solid rgba(245,158,11,0.18) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        /* Sidebar page links — strip all box/border styling */
        section[data-testid="stSidebar"] [data-testid="stPageLink"],
        section[data-testid="stSidebar"] [data-testid="stPageLink"] > div,
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a,
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a > div,
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a > div > div,
        section[data-testid="stSidebar"] [data-testid="stPageLink"] p,
        section[data-testid="stSidebar"] [data-testid="stPageLink"] span {{
            border: none !important;
            border-radius: 4px !important;
            background: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        /* The actual link element */
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            padding: 6px 12px 6px 14px !important;
            margin: 1px 6px !important;
            border-left: 2px solid transparent !important;
            border-radius: 5px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            color: #64748B !important;
            transition: all 0.15s ease !important;
            text-decoration: none !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
            color: #E2E8F0 !important;
            background: rgba(245,158,11,0.07) !important;
            border-left-color: rgba(245,158,11,0.5) !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {{
            color: #F59E0B !important;
            background: rgba(245,158,11,0.10) !important;
            border-left-color: #F59E0B !important;
            font-weight: 600 !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           5.  METRIC CARDS — Bloomberg KPI tiles
        ═══════════════════════════════════════════════════════════════════ */
        [data-testid="stMetric"] {{
            background: linear-gradient(135deg, rgba(13,20,33,0.95) 0%, rgba(17,28,46,0.90) 100%);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(245,158,11,0.14);
            border-top: 2px solid {_AMBER};
            padding: 18px 20px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.40), 0 0 0 0 rgba(245,158,11,0);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
            animation: fadeInUp 0.4s ease both;
        }}

        [data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 36px rgba(0,0,0,0.50),
                        0 0 0 1px rgba(245,158,11,0.28),
                        0 0 20px rgba(245,158,11,0.06);
            border-color: rgba(245,158,11,0.38);
        }}

        [data-testid="stMetricLabel"] p {{
            color: {_AMBER} !important;
            font-size: 0.65rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.12em !important;
            font-family: 'JetBrains Mono', monospace !important;
            margin-bottom: 6px !important;
            opacity: 0.85;
        }}

        [data-testid="stMetricValue"] {{
            color: {_TEXT_PRI} !important;
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            font-family: 'JetBrains Mono', monospace !important;
            line-height: 1.15 !important;
        }}

        [data-testid="stMetricDelta"] {{
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            font-family: 'JetBrains Mono', monospace !important;
            margin-top: 4px !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           6.  BUTTONS — institutional action style
        ═══════════════════════════════════════════════════════════════════ */
        .stButton > button {{
            background: linear-gradient(135deg, {_AMBER} 0%, {_AMBER_DIM} 100%) !important;
            color: #000 !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 800 !important;
            font-size: 0.82rem !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            padding: 0.50rem 1.15rem !important;
            box-shadow: 0 3px 14px rgba(245,158,11,0.30) !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 7px 24px rgba(245,158,11,0.46) !important;
            filter: brightness(1.08) !important;
        }}

        .stButton > button:active {{
            transform: translateY(0) !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           7.  FORM ELEMENTS
        ═══════════════════════════════════════════════════════════════════ */
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput > div > div > input {{
            background: rgba(10,15,26,0.85) !important;
            border: 1px solid rgba(245,158,11,0.18) !important;
            border-radius: 6px !important;
            color: {_TEXT_PRI} !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.875rem !important;
            transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
        }}

        .stTextInput > div > div > input:focus,
        .stTextArea textarea:focus,
        .stNumberInput > div > div > input:focus {{
            border-color: {_AMBER} !important;
            box-shadow: 0 0 0 2px rgba(245,158,11,0.14) !important;
            outline: none !important;
        }}

        [data-testid="stWidgetLabel"] p {{
            color: {_AMBER} !important;
            font-size: 0.66rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.10em !important;
            font-family: 'JetBrains Mono', monospace !important;
            opacity: 0.80;
        }}

        /* Select boxes */
        .stSelectbox > div > div {{
            background: rgba(10,15,26,0.85) !important;
            border: 1px solid rgba(245,158,11,0.18) !important;
            border-radius: 6px !important;
            color: {_TEXT_PRI} !important;
        }}

        /* Sliders */
        .stSlider [data-baseweb="slider"] [role="slider"] {{
            background: {_AMBER} !important;
            border: 2px solid {_AMBER} !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           8.  TABS
        ═══════════════════════════════════════════════════════════════════ */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2px;
            background: rgba(10,15,26,0.80);
            border-radius: 7px;
            padding: 4px;
            border: 1px solid rgba(245,158,11,0.12);
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 5px !important;
            padding: 6px 16px !important;
            color: {_TEXT_MUT} !important;
            font-weight: 700 !important;
            font-size: 0.78rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            font-family: 'JetBrains Mono', monospace !important;
            transition: all 0.14s ease !important;
            background: transparent !important;
            border: none !important;
        }}

        .stTabs [data-baseweb="tab"]:hover {{
            color: {_AMBER} !important;
            background: rgba(245,158,11,0.07) !important;
        }}

        .stTabs [aria-selected="true"] {{
            background: rgba(245,158,11,0.12) !important;
            color: {_AMBER} !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           9.  EXPANDERS
        ═══════════════════════════════════════════════════════════════════ */
        .streamlit-expanderHeader {{
            background: rgba(13,20,33,0.85) !important;
            border: 1px solid rgba(245,158,11,0.14) !important;
            border-radius: 7px !important;
            color: {_TEXT_SEC} !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            font-family: 'JetBrains Mono', monospace !important;
            padding: 10px 14px !important;
            transition: all 0.14s ease !important;
        }}

        .streamlit-expanderHeader:hover {{
            border-color: rgba(245,158,11,0.35) !important;
            color: {_AMBER} !important;
        }}

        .streamlit-expanderContent {{
            border: 1px solid rgba(245,158,11,0.10) !important;
            border-top: none !important;
            border-radius: 0 0 7px 7px !important;
            background: rgba(10,15,26,0.60) !important;
            padding: 12px 14px !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           10.  ALERTS
        ═══════════════════════════════════════════════════════════════════ */
        [data-testid="stAlert"] {{
            border-radius: 7px !important;
            border-left-width: 3px !important;
            font-size: 0.875rem !important;
            font-family: 'JetBrains Mono', monospace !important;
            animation: fadeIn 0.3s ease both !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           11.  DATAFRAMES — Bloomberg table style
        ═══════════════════════════════════════════════════════════════════ */
        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(245,158,11,0.14) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           12.  DIVIDERS
        ═══════════════════════════════════════════════════════════════════ */
        hr {{
            border: none !important;
            border-top: 1px solid rgba(245,158,11,0.10) !important;
            margin: 1.8rem 0 !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           13.  PAGE LINKS — compact sidebar nav rows, card style elsewhere
        ═══════════════════════════════════════════════════════════════════ */

        /* Sidebar section header label */
        .sb-section {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.55rem;
            font-weight: 800;
            color: rgba(245,158,11,0.45);
            text-transform: uppercase;
            letter-spacing: 0.20em;
            padding: 12px 14px 4px 16px;
        }}

        /* General page links outside sidebar — keep a subtle card style */
        [data-testid="stPageLink"] a {{
            border: 1px solid rgba(245,158,11,0.18) !important;
            border-radius: 7px !important;
            padding: 9px 14px !important;
            background: rgba(13,20,33,0.80) !important;
            display: block !important;
            transition: all 0.15s ease !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
        }}
        [data-testid="stPageLink"] a:hover {{
            border-color: {_AMBER} !important;
            background: rgba(245,158,11,0.08) !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           14.  HERO CARD — terminal command center style
        ═══════════════════════════════════════════════════════════════════ */
        .hero-card {{
            background:
                radial-gradient(ellipse at 20% 0%, rgba(245,158,11,0.08) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 100%, rgba(6,182,212,0.05) 0%, transparent 55%),
                linear-gradient(160deg, #060B14 0%, #0A1020 40%, #080E1A 100%);
            padding: 30px 38px;
            border-radius: 10px;
            border: 1px solid rgba(245,158,11,0.18);
            border-top: 1px solid rgba(245,158,11,0.35);
            box-shadow: 0 24px 64px rgba(0,0,0,0.60),
                        0 0 0 1px rgba(245,158,11,0.05);
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
            animation: fadeInUp 0.40s ease both;
        }}

        .hero-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 1px;
            background: linear-gradient(90deg,
                transparent 0%, {_AMBER} 30%, {_CYAN} 70%, transparent 100%);
            opacity: 0.55;
        }}

        .hero-eyebrow {{
            font-size: 0.62rem;
            font-weight: 700;
            color: {_AMBER};
            letter-spacing: 0.20em;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
            opacity: 0.80;
        }}

        .hero-title {{
            font-size: 1.85rem;
            font-weight: 900;
            letter-spacing: -0.025em;
            margin-bottom: 6px;
            line-height: 1.12;
            background: linear-gradient(95deg, {_TEXT_PRI} 0%, {_AMBER} 55%, {_CYAN} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .hero-subtitle {{
            color: {_TEXT_SEC};
            font-size: 0.875rem;
            line-height: 1.65;
            max-width: 620px;
            opacity: 0.75;
        }}

        /* Blinking cursor for terminal aesthetic */
        .term-cursor {{
            display: inline-block;
            width: 8px; height: 16px;
            background: {_AMBER};
            margin-left: 3px;
            vertical-align: middle;
            animation: blink 1.1s step-end infinite;
            border-radius: 1px;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           15.  SECTION CARD
        ═══════════════════════════════════════════════════════════════════ */
        .section-card {{
            background: linear-gradient(90deg,
                rgba(245,158,11,0.08) 0%, transparent 100%);
            border-left: 3px solid {_AMBER};
            border-radius: 0 7px 7px 0;
            padding: 7px 16px;
            margin: 14px 0 8px;
            animation: fadeIn 0.3s ease both;
        }}

        .section-card h3 {{
            color: {_TEXT_PRI} !important;
            margin: 0 0 2px !important;
            font-size: 0.85rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            text-transform: uppercase !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        /* Tighter global density */
        .block-container {{ padding-top: 1rem !important; padding-bottom: 1rem !important; }}
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {{ gap: 0.4rem !important; }}

        .section-card p {{
            color: {_TEXT_MUT} !important;
            margin: 0 !important;
            font-size: 0.80rem !important;
            line-height: 1.5 !important;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           CUSTOM SIDEBAR NAV — hide default, show grouped
        ═══════════════════════════════════════════════════════════════════ */

        /* ═══════════════════════════════════════════════════════════════════
           WORKFLOW BREADCRUMB
        ═══════════════════════════════════════════════════════════════════ */
        .wf-bar {{
            display: flex;
            align-items: center;
            gap: 0;
            flex-wrap: wrap;
            margin-bottom: 14px;
            background: rgba(10,15,26,0.60);
            border: 1px solid rgba(245,158,11,0.10);
            border-radius: 6px;
            padding: 7px 14px;
        }}
        .wf-step {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.60rem;
            font-weight: 700;
            color: {_TEXT_MUT};
            text-transform: uppercase;
            letter-spacing: 0.09em;
            padding: 2px 0;
        }}
        .wf-step.active {{
            color: {_AMBER};
        }}
        .wf-arrow {{
            color: rgba(245,158,11,0.22);
            margin: 0 7px;
            font-size: 0.60rem;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           DASHBOARD PANELS
        ═══════════════════════════════════════════════════════════════════ */
        .db-panel {{
            background: linear-gradient(145deg, rgba(13,20,33,0.95), rgba(17,28,46,0.88));
            border: 1px solid rgba(245,158,11,0.12);
            border-radius: 9px;
            padding: 16px 18px;
            height: 100%;
        }}

        .db-panel-title {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.62rem;
            font-weight: 800;
            color: {_AMBER};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 10px;
            opacity: 0.80;
            padding-bottom: 7px;
            border-bottom: 1px solid rgba(245,158,11,0.10);
        }}

        .news-item {{
            padding: 8px 0;
            border-bottom: 1px solid rgba(245,158,11,0.07);
        }}
        .news-item:last-child {{ border-bottom: none; }}

        .news-headline {{
            font-size: 0.80rem;
            color: {_TEXT_SEC};
            line-height: 1.45;
            font-weight: 500;
        }}
        .news-headline:hover {{ color: {_AMBER}; }}

        .news-meta {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.62rem;
            color: {_TEXT_MUT};
            margin-top: 2px;
        }}

        .signal-chip {{
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 3px 9px;
            border-radius: 4px;
            margin-right: 6px;
        }}
        .signal-buy  {{ background:rgba(16,185,129,0.14); color:{_GREEN}; border:1px solid rgba(16,185,129,0.25); }}
        .signal-sell {{ background:rgba(239,68,68,0.12);  color:{_RED};   border:1px solid rgba(239,68,68,0.22); }}
        .signal-hold {{ background:rgba(245,158,11,0.10); color:{_AMBER}; border:1px solid rgba(245,158,11,0.22); }}

        .risk-score-bar {{
            height: 6px;
            border-radius: 3px;
            background: rgba(245,158,11,0.12);
            margin-top: 4px;
            overflow: hidden;
        }}
        .risk-score-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           16.  NEXT STEP CARD
        ═══════════════════════════════════════════════════════════════════ */
        .next-step-card {{
            background: rgba(245,158,11,0.055);
            border: 1px solid rgba(245,158,11,0.18);
            border-radius: 8px;
            padding: 16px 22px;
            margin-top: 12px;
            animation: fadeIn 0.3s ease both;
        }}

        .next-step-label {{
            font-size: 0.62rem;
            font-weight: 700;
            color: {_AMBER};
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 5px;
            opacity: 0.85;
        }}

        .next-step-text {{
            color: {_TEXT_SEC};
            font-size: 0.88rem;
            line-height: 1.65;
        }}

        /* ═══════════════════════════════════════════════════════════════════
           17.  SIDEBAR MICRO-WIDGETS
        ═══════════════════════════════════════════════════════════════════ */
        .brand-box {{
            background: linear-gradient(135deg,
                rgba(245,158,11,0.08) 0%, rgba(6,182,212,0.04) 100%);
            border: 1px solid rgba(245,158,11,0.18);
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        }}

        .brand-box::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, {_AMBER}, {_CYAN});
            opacity: 0.60;
        }}

        .brand-title {{
            font-size: 0.90rem;
            font-weight: 900;
            color: {_TEXT_PRI} !important;
            letter-spacing: 0.02em;
            font-family: 'JetBrains Mono', monospace;
        }}

        .brand-subtitle {{
            font-size: 0.62rem;
            color: {_AMBER} !important;
            margin-top: 2px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
            opacity: 0.75;
        }}

        /* ── Ticker strip ── */
        .ticker-outer {{
            background: rgba(10,15,26,0.90);
            border: 1px solid rgba(245,158,11,0.14);
            border-radius: 7px;
            padding: 7px 12px;
            margin-bottom: 12px;
            overflow: hidden;
            white-space: nowrap;
            position: relative;
        }}

        .ticker-inner {{
            display: inline-block;
        }}

        .ticker-label {{
            color: {_AMBER};
            font-weight: 800;
            font-size: 0.62rem;
            margin-right: 10px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
            opacity: 0.80;
        }}

        .ticker-positive {{
            color: {_GREEN};
            font-weight: 700;
            font-size: 0.76rem;
            margin-right: 16px;
            font-family: 'JetBrains Mono', monospace;
        }}

        .ticker-negative {{
            color: {_RED};
            font-weight: 700;
            font-size: 0.76rem;
            margin-right: 16px;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* ── Quick stats card ── */
        .quick-card {{
            background: rgba(10,15,26,0.85);
            border: 1px solid rgba(245,158,11,0.12);
            border-radius: 8px;
            padding: 10px 13px;
            margin: 6px 0;
        }}

        .quick-title {{
            font-weight: 800;
            color: {_AMBER} !important;
            margin-bottom: 7px;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-family: 'JetBrains Mono', monospace;
            opacity: 0.80;
        }}

        .quick-row {{
            display: flex;
            justify-content: space-between;
            font-size: 0.76rem;
            margin-bottom: 4px;
            color: {_TEXT_SEC};
            font-family: 'JetBrains Mono', monospace;
        }}

        .quick-row span:last-child {{
            color: {_TEXT_PRI};
            font-weight: 600;
        }}

        /* ── Status dot ── */
        .status-dot {{
            display: inline-block;
            width: 7px; height: 7px;
            border-radius: 50%;
            margin-right: 5px;
            vertical-align: middle;
        }}
        .status-dot.green {{
            background: {_GREEN};
            animation: pulse-dot 2s infinite;
        }}
        .status-dot.red {{
            background: {_RED};
            animation: amber-pulse 2s infinite;
        }}
        .status-dot.amber {{
            background: {_AMBER};
            animation: amber-pulse 2s infinite;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Module-level cached market data (TTL=300s = 5 min) ───────────────────────
@st.cache_data(ttl=300)
def _fetch_ticker_strip():
    try:
        from market.prices import fetch_latest_prices
        return fetch_latest_prices(
            ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "BTC-USD"],
            period="5d", interval="1d",
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def _fetch_spy_sidebar():
    try:
        price = yf.Ticker("SPY").fast_info.last_price
        if price is not None and price == price:
            return float(price)
    except Exception:
        pass
    return None


def _market_is_open() -> bool:
    """True if NYSE is currently in regular session (9:30–16:00 ET, Mon–Fri)."""
    try:
        et = pytz.timezone("America/New_York")
        now = datetime.now(et)
        if now.weekday() >= 5:
            return False
        open_t  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
        close_t = now.replace(hour=16, minute=0,  second=0, microsecond=0)
        return open_t <= now <= close_t
    except Exception:
        return False


# ── Plotly chart configuration ────────────────────────────────────────────────
def plotly_config(**overrides):
    """Bloomberg / TradingView inspired Plotly layout defaults."""
    base = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,15,26,0.60)",
        font=dict(
            color=_TEXT_SEC,
            size=11,
            family="JetBrains Mono, monospace",
        ),
        colorway=[_AMBER, _CYAN, _GREEN, _RED, _PURPLE, "#F472B6", "#34D399"],
        margin=dict(l=10, r=10, t=44, b=10),
        legend=dict(
            bgcolor="rgba(6,11,20,0.88)",
            bordercolor="rgba(245,158,11,0.20)",
            borderwidth=1,
            font=dict(size=10.5, color=_TEXT_SEC,
                      family="JetBrains Mono, monospace"),
        ),
        xaxis=dict(
            gridcolor="rgba(245,158,11,0.06)",
            showgrid=True,
            zeroline=False,
            linecolor="rgba(245,158,11,0.12)",
            tickfont=dict(size=10, color=_TEXT_MUT,
                          family="JetBrains Mono, monospace"),
        ),
        yaxis=dict(
            gridcolor="rgba(245,158,11,0.06)",
            showgrid=True,
            zeroline=False,
            linecolor="rgba(245,158,11,0.12)",
            tickfont=dict(size=10, color=_TEXT_MUT,
                          family="JetBrains Mono, monospace"),
        ),
        hoverlabel=dict(
            bgcolor="rgba(6,11,20,0.96)",
            bordercolor="rgba(245,158,11,0.30)",
            font=dict(color=_TEXT_PRI, size=12,
                      family="JetBrains Mono, monospace"),
        ),
        title_font=dict(
            size=12,
            color=_AMBER,
            family="JetBrains Mono, monospace",
        ),
        title_x=0.0,
    )
    base.update(overrides)
    return base


# ── Workflow definition ───────────────────────────────────────────────────────
_WORKFLOW_STEPS = [
    "Market Intel",
    "Alpha Research",
    "Portfolio",
    "Risk",
    "Execution",
    "Monitoring",
]

_NAV_SECTIONS = [
    ("HOME", [
        ("app.py",                              "⚡ Command Center",     ),
        ("pages/0_dashboard.py",                "📊 Dashboard",          ),
    ]),
    ("📡 Market Intelligence", [
        ("pages/2_Market_Prices.py",            "Market Prices"          ),
        ("pages/4_Market_News.py",              "Market News"            ),
        ("pages/6_Daily_Picks.py",              "Daily Picks"            ),
        ("pages/17_Market_Regime.py",           "Market Regime"          ),
        ("pages/3_Market_Anomalies.py",         "Anomalies"              ),
    ]),
    ("🔬 Alpha Research", [
        ("pages/20_Pairs_Trading.py",           "Pairs Trading"          ),
        ("pages/1_backtest.py",                 "Backtest Engine"        ),
        ("pages/22_Factor_Research.py",         "Factor Research"        ),
        ("pages/23_ML_Alpha_Lab.py",            "ML Alpha Lab"           ),
        ("pages/24_News_Sentiment.py",          "News Sentiment"         ),
    ]),
    ("📊 Portfolio", [
        ("pages/16_Portfolio_Optimizer.py",     "Optimizer"              ),
        ("pages/7_watchlist.py",                "Watchlist"              ),
    ]),
    ("🛡️ Risk Management", [
        ("pages/10_RiskEngine.py",              "Risk Engine"            ),
        ("pages/18_VaR_CVaR_Risk.py",           "VaR / CVaR"             ),
        ("pages/11_MonteCarlo.py",              "Monte Carlo"            ),
    ]),
    ("⚡ Execution", [
        ("pages/5_Trading_Sim.py",              "Trading Sim"            ),
        ("pages/8_Execution.py",                "TWAP / VWAP"            ),
        ("pages/21_Order_Book_Microstructure.py","Order Book"            ),
    ]),
    ("📈 Monitoring", [
        ("pages/9_performance.py",              "Performance"            ),
        ("pages/15_Alerts.py",                  "Alerts"                 ),
        ("pages/14_Trading_Bot.py",             "Trading Bot"            ),
    ]),
    ("🧬 Advanced", [
        ("pages/12_Strategy_DNA.py",            "Strategy DNA"           ),
        ("pages/13_Counterfactual_Replay.py",   "Counterfactual"         ),
        ("pages/19_Options_Pricing.py",         "Options Pricing"        ),
    ]),
]


def render_sidebar_nav():
    """Render compact grouped sidebar navigation."""
    with st.sidebar:
        # ── MARKETS ──────────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">MARKETS</div>', unsafe_allow_html=True)
        st.page_link("pages/2_Market_Prices.py",    label="Market Prices")
        st.page_link("pages/3_Market_Anomalies.py", label="Anomalies")
        st.page_link("pages/4_Market_News.py",      label="Market News")
        st.page_link("pages/6_Daily_Picks.py",      label="Daily Picks")
        st.page_link("pages/7_watchlist.py",        label="Watchlist")

        # ── RESEARCH ─────────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">RESEARCH</div>', unsafe_allow_html=True)
        st.page_link("pages/1_backtest.py",                  label="Backtest Engine")
        st.page_link("pages/5_Trading_Sim.py",               label="Trading Sim")
        st.page_link("pages/12_Strategy_DNA.py",             label="Strategy DNA")
        st.page_link("pages/13_Counterfactual_Replay.py",    label="Counterfactual Replay")

        # ── INTELLIGENCE ─────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">INTELLIGENCE</div>', unsafe_allow_html=True)
        st.page_link("pages/22_Factor_Research.py",          label="🔬 Factor Research")
        st.page_link("pages/23_ML_Alpha_Lab.py",             label="🤖 ML Alpha Lab")
        st.page_link("pages/24_News_Sentiment.py",           label="📰 News Sentiment")

        # ── PORTFOLIO ────────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">PORTFOLIO</div>', unsafe_allow_html=True)
        st.page_link("pages/0_dashboard.py",             label="Dashboard")
        st.page_link("pages/9_performance.py",           label="Performance")
        st.page_link("pages/16_Portfolio_Optimizer.py",  label="Portfolio Optimizer")
        st.page_link("pages/8_Execution.py",             label="Execution")

        # ── RISK ─────────────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">RISK</div>', unsafe_allow_html=True)
        st.page_link("pages/10_RiskEngine.py",    label="Risk Engine")
        st.page_link("pages/11_MonteCarlo.py",    label="Monte Carlo")
        st.page_link("pages/15_Alerts.py",        label="Alerts")
        st.page_link("pages/18_VaR_CVaR_Risk.py", label="VaR / CVaR")

        # ── AUTOMATION ───────────────────────────────────────────────────
        st.sidebar.markdown('<div class="sb-section">AUTOMATION</div>', unsafe_allow_html=True)
        st.page_link("pages/14_Trading_Bot.py",   label="Trading Bot")
        st.page_link("pages/17_Market_Regime.py", label="Market Regime")

        # ── Pipeline stepper ─────────────────────────────────────────────
        _eq = st.session_state.get("equity_curve") is not None
        _has_risk = _eq  # proxy
        st.sidebar.markdown(f"""
            <div style="padding:12px 16px; border-top:1px solid rgba(245,158,11,0.10); margin-top:8px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.52rem;
                    color:rgba(245,158,11,0.40);text-transform:uppercase;letter-spacing:0.18em;
                    margin-bottom:8px;">Workflow</div>
                <div style="display:flex;align-items:center;gap:4px;font-family:'JetBrains Mono',monospace;font-size:0.60rem;">
                    <span style="width:8px;height:8px;border-radius:50%;background:{'#F59E0B' if _eq else '#1E293B'};
                        border:1px solid {'#F59E0B' if _eq else '#334155'};flex-shrink:0;"></span>
                    <span style="color:{'#F59E0B' if _eq else '#475569'};">Backtest</span>
                    <span style="color:#1E293B;flex:1;border-top:1px dashed #1E293B;margin:0 2px;"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:{'#F59E0B' if _has_risk else '#1E293B'};
                        border:1px solid {'#F59E0B' if _has_risk else '#334155'};flex-shrink:0;"></span>
                    <span style="color:{'#F59E0B' if _has_risk else '#475569'};">Risk</span>
                    <span style="color:#1E293B;flex:1;border-top:1px dashed #1E293B;margin:0 2px;"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#1E293B;
                        border:1px solid #334155;flex-shrink:0;"></span>
                    <span style="color:#475569;">Monte Carlo</span>
                </div>
            </div>
        """, unsafe_allow_html=True)


def workflow_breadcrumb(current: str = ""):
    """Horizontal workflow progress bar showing the 6-step quant workflow."""
    steps_html = ""
    for i, step in enumerate(_WORKFLOW_STEPS):
        is_active = current.lower() in step.lower() or step.lower() in current.lower()
        cls = "wf-step active" if is_active else "wf-step"
        steps_html += f'<span class="{cls}">{i+1}. {step}</span>'
        if i < len(_WORKFLOW_STEPS) - 1:
            steps_html += '<span class="wf-arrow">›</span>'
    st.markdown(f'<div class="wf-bar">{steps_html}</div>', unsafe_allow_html=True)


# ── Sidebar helpers ───────────────────────────────────────────────────────────
def sidebar_brand():
    mkt_open  = _market_is_open()
    dot_color = "#10B981" if mkt_open else "#EF4444"
    mkt_label = "OPEN" if mkt_open else "CLOSED"
    try:
        et  = pytz.timezone("America/New_York")
        now = datetime.now(et).strftime("%H:%M ET")
    except Exception:
        now = datetime.now().strftime("%H:%M")

    st.sidebar.markdown(f"""
        <div style="padding:22px 16px 16px; border-bottom:1px solid rgba(245,158,11,0.12); margin-bottom:6px;">
            <div style="
                font-family:'JetBrains Mono',monospace;
                font-size:1.1rem; font-weight:800;
                background: linear-gradient(90deg, #F59E0B 0%, #FCD34D 50%, #F59E0B 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; letter-spacing:0.04em; line-height:1.1;
            ">⚡ QUANT TERMINAL</div>
            <div style="
                font-family:'Inter',sans-serif; font-size:0.62rem;
                color:#475569; letter-spacing:0.08em;
                text-transform:uppercase; margin-top:5px;
            ">Institutional Research OS</div>
            <div style="
                display:flex; align-items:center; gap:7px;
                margin-top:10px; font-family:'JetBrains Mono',monospace; font-size:0.60rem;
            ">
                <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};
                    box-shadow:0 0 7px {dot_color};display:inline-block;flex-shrink:0;"></span>
                <span style="color:{dot_color};font-weight:700;">NYSE {mkt_label}</span>
                <span style="color:#334155;">·</span>
                <span style="color:#475569;">{now}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def market_ticker():
    df = _fetch_ticker_strip()
    ts = datetime.now().strftime("%H:%M")

    if df.empty:
        inner = '<span class="ticker-label">Market data unavailable</span>'
    else:
        spans = []
        for tkr, row in df.iterrows():
            price = row["price"]
            pct   = row["pct_change"]
            sign  = "+" if pct >= 0 else ""
            css   = "ticker-positive" if pct >= 0 else "ticker-negative"
            price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
            spans.append(
                f'<span class="{css}">{tkr} {price_str} {sign}{pct:.2f}%</span>'
            )
        inner = "".join(spans)

    st.markdown(
        f'<div class="ticker-outer">'
        f'<div class="ticker-inner">'
        f'<span class="ticker-label">{ts}</span>'
        f'{inner}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def quick_stats(equity="N/A", pnl="N/A", positions="N/A", status="Normal", spy_price=None):
    spy_row = ""
    if spy_price is not None:
        spy_row = f'<div class="quick-row"><span>SPY</span><span>${spy_price:,.2f}</span></div>'
    st.sidebar.markdown(
        f"""
        <div class="quick-card">
            <div class="quick-title">Quick Stats</div>
            {spy_row}
            <div class="quick-row"><span>Equity</span><span>{equity}</span></div>
            <div class="quick-row"><span>Day P&amp;L</span><span>{pnl}</span></div>
            <div class="quick-row"><span>Positions</span><span>{positions}</span></div>
            <div class="quick-row"><span>Status</span><span>{status}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Top navigation bar ────────────────────────────────────────────────────────
_NAV_OPTIONS = [
    ("── Navigate ──",                          None),
    ("⚡  Command Center",                       "app.py"),
    ("📊  Dashboard",                            "pages/0_dashboard.py"),
    ("── 📡 Market Intelligence ──",             None),
    ("   Market Prices",                         "pages/2_Market_Prices.py"),
    ("   Market News",                           "pages/4_Market_News.py"),
    ("   Daily Picks",                           "pages/6_Daily_Picks.py"),
    ("   Market Regime",                         "pages/17_Market_Regime.py"),
    ("   Anomalies",                             "pages/3_Market_Anomalies.py"),
    ("── 🔬 Alpha Research ──",                  None),
    ("   Pairs Trading",                         "pages/20_Pairs_Trading.py"),
    ("   Backtest Engine",                       "pages/1_backtest.py"),
    ("   Factor Research",                       "pages/22_Factor_Research.py"),
    ("   ML Alpha Lab",                          "pages/23_ML_Alpha_Lab.py"),
    ("   News Sentiment",                        "pages/24_News_Sentiment.py"),
    ("── 📊 Portfolio ──",                       None),
    ("   Optimizer",                             "pages/16_Portfolio_Optimizer.py"),
    ("   Watchlist",                             "pages/7_watchlist.py"),
    ("── 🛡️ Risk Management ──",                 None),
    ("   Risk Engine",                           "pages/10_RiskEngine.py"),
    ("   VaR / CVaR",                            "pages/18_VaR_CVaR_Risk.py"),
    ("   Monte Carlo",                           "pages/11_MonteCarlo.py"),
    ("── ⚡ Execution ──",                        None),
    ("   Trading Sim",                           "pages/5_Trading_Sim.py"),
    ("   TWAP / VWAP",                           "pages/8_Execution.py"),
    ("   Order Book",                            "pages/21_Order_Book_Microstructure.py"),
    ("── 📈 Monitoring ──",                      None),
    ("   Performance",                           "pages/9_performance.py"),
    ("   Alerts",                                "pages/15_Alerts.py"),
    ("   Trading Bot",                           "pages/14_Trading_Bot.py"),
    ("── 🧬 Advanced ──",                        None),
    ("   Strategy DNA",                          "pages/12_Strategy_DNA.py"),
    ("   Counterfactual",                        "pages/13_Counterfactual_Replay.py"),
    ("   Options Pricing",                       "pages/19_Options_Pricing.py"),
]
_NAV_LABELS = [label for label, _ in _NAV_OPTIONS]
_NAV_PATHS  = {label: path for label, path in _NAV_OPTIONS}


def _top_nav_bar():
    nav_col, spacer = st.columns([2, 5])
    with nav_col:
        choice = st.selectbox(
            "nav",
            _NAV_LABELS,
            index=0,
            key=f"_topnav_{id(st)}",
            label_visibility="collapsed",
        )
    if choice and not choice.startswith("──") and _NAV_PATHS.get(choice):
        st.switch_page(_NAV_PATHS[choice])


# ── Page setup ────────────────────────────────────────────────────────────────
def setup_page(title, subtitle="", icon="📊"):
    st.set_page_config(page_title=title, layout="wide")
    inject_global_css()

    # Restore persisted equity/returns data on every page load
    try:
        from session_persist import restore_session
        _restored = restore_session()
        if _restored:
            _ts = st.session_state.get("_session_restored", "")
            st.toast(f"Session data restored · {_ts}", icon="💾")
    except Exception:
        pass

    sidebar_brand()
    render_sidebar_nav()
    market_ticker()

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-eyebrow">LIVE QUANT TERMINAL · PYTHON · STREAMLIT</div>
            <div class="hero-title">{icon} {title}<span class="term-cursor"></span></div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Content helpers ───────────────────────────────────────────────────────────
def section(title, subtitle=""):
    st.markdown(
        f"""
        <div class="section-card">
            <h3>{title}</h3>
            {"<p>" + subtitle + "</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def next_step(text):
    st.divider()
    st.markdown(
        f"""
        <div class="next-step-card">
            <div class="next-step-label">→ Next Step</div>
            <div class="next-step-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def nav_hub():
    """Full navigation grid rendered on the dashboard — replaces sidebar nav."""
    _sections = [
        ("📡 Market Intelligence", _CYAN, [
            ("pages/2_Market_Prices.py",  "Market Prices",  "Live equity, index & crypto prices"),
            ("pages/4_Market_News.py",    "Market News",    "Financial headlines & RSS feed"),
            ("pages/6_Daily_Picks.py",    "Daily Picks",    "Momentum-based stock picks"),
            ("pages/17_Market_Regime.py", "Market Regime",  "Bull / Bear / Stress classification"),
            ("pages/3_Market_Anomalies.py","Anomalies",     "Cost-aware anomaly signals"),
        ]),
        ("🔬 Alpha Research", _AMBER, [
            ("pages/20_Pairs_Trading.py",       "Pairs Trading",    "Cointegration & stat-arb pairs"),
            ("pages/1_backtest.py",             "Backtest Engine",  "Historical strategy backtesting"),
            ("pages/22_Factor_Research.py",     "Factor Research",  "Multi-factor equity scoring"),
            ("pages/23_ML_Alpha_Lab.py",        "ML Alpha Lab",     "RF / GBM / LR signal generation"),
            ("pages/24_News_Sentiment.py",      "News Sentiment",   "Google News RSS sentiment scoring"),
        ]),
        ("📊 Portfolio", _GREEN, [
            ("pages/16_Portfolio_Optimizer.py", "Optimizer","Mean-variance & risk-parity"),
            ("pages/7_watchlist.py",      "Watchlist",      "Track symbols & set price alerts"),
        ]),
        ("🛡️ Risk Management", _RED, [
            ("pages/10_RiskEngine.py",    "Risk Engine",    "Drawdown, vol & kill-switch"),
            ("pages/18_VaR_CVaR_Risk.py", "VaR / CVaR",    "Value-at-Risk & tail risk"),
            ("pages/11_MonteCarlo.py",    "Monte Carlo",    "Forward scenario simulation"),
        ]),
        ("⚡ Execution", _AMBER, [
            ("pages/5_Trading_Sim.py",    "Trading Sim",    "Paper trading broker"),
            ("pages/8_Execution.py",      "TWAP / VWAP",    "Algorithmic execution algos"),
            ("pages/21_Order_Book_Microstructure.py", "Order Book", "LOB microstructure sim"),
        ]),
        ("📈 Monitoring", _GREEN, [
            ("pages/9_performance.py",    "Performance",    "Equity curve & trade blotter"),
            ("pages/15_Alerts.py",        "Alerts",         "Risk threshold notifications"),
            ("pages/14_Trading_Bot.py",   "Trading Bot",    "Automated signal generation"),
        ]),
        ("🧬 Advanced", _CYAN, [
            ("pages/12_Strategy_DNA.py",          "Strategy DNA",      "Behavioural strategy fingerprint"),
            ("pages/13_Counterfactual_Replay.py", "Counterfactual",    "What-if trade replay"),
            ("pages/19_Options_Pricing.py",       "Options Pricing",   "Black-Scholes & Greeks"),
        ]),
    ]

    st.markdown(
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:0.62rem;'
        f'font-weight:800;color:{_AMBER};text-transform:uppercase;'
        f'letter-spacing:0.18em;margin:28px 0 14px;">Platform Navigation</p>',
        unsafe_allow_html=True,
    )

    # Render two columns of sections
    left_sections  = _sections[:4]
    right_sections = _sections[4:]
    col_l, col_r   = st.columns(2)

    for col, section_group in ((col_l, left_sections), (col_r, right_sections)):
        with col:
            for sec_label, accent, pages in section_group:
                st.markdown(
                    f"""
                    <div style="
                        border-left: 3px solid {accent};
                        padding: 6px 0 6px 12px;
                        margin: 16px 0 6px;
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 0.68rem;
                        font-weight: 800;
                        color: {accent};
                        text-transform: uppercase;
                        letter-spacing: 0.14em;
                    ">{sec_label}</div>
                    """,
                    unsafe_allow_html=True,
                )
                for path, label, desc in pages:
                    link_col, desc_col = st.columns([1, 1.6])
                    with link_col:
                        st.page_link(path, label=label)
                    with desc_col:
                        st.markdown(
                            f'<span style="font-size:0.68rem;color:{_TEXT_MUT};'
                            f'font-family:Inter,sans-serif;line-height:2.2;">{desc}</span>',
                            unsafe_allow_html=True,
                        )


def status_badge(label, status):
    s = str(status).lower()
    if s in ("good", "normal", "buy", "positive", "off"):
        st.success(f"{label}: {s.upper()}")
    elif s in ("warning", "hold", "medium"):
        st.warning(f"{label}: {s.upper()}")
    elif s in ("critical", "sell", "danger", "active"):
        st.error(f"{label}: {s.upper()}")
    else:
        st.info(f"{label}: {s.upper()}")


def metric_row(items):
    cols = st.columns(len(items))
    for i, (label, value) in enumerate(items):
        cols[i].metric(label, value)
