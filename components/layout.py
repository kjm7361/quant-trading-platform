import streamlit as st

def setup_page(title, subtitle="", icon="📊"):
    st.set_page_config(page_title=title, layout="wide")

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        h1 {
            font-size: 2.2rem;
            font-weight: 800;
        }

        h2, h3 {
            font-weight: 700;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.6rem;
            font-weight: 700;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title(f"{icon} {title}")

    if subtitle:
        st.caption(subtitle)

    st.divider()


def section(title, subtitle=""):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def next_step(text):
    st.divider()
    st.subheader("Next Step")
    st.info(text)