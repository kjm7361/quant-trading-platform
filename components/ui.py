import streamlit as st

def page_header(title, subtitle):
    st.title(title)
    st.caption(subtitle)
    st.divider()

def section(title, description=None):
    st.subheader(title)
    if description:
        st.caption(description)

def status_badge(label, status):
    status = str(status).lower()

    if status in ["good", "normal", "buy", "positive", "off"]:
        st.success(f"{label}: {status.upper()}")
    elif status in ["warning", "hold", "medium"]:
        st.warning(f"{label}: {status.upper()}")
    elif status in ["critical", "sell", "danger", "active"]:
        st.error(f"{label}: {status.upper()}")
    else:
        st.info(f"{label}: {status.upper()}")

def next_step(text):
    st.divider()
    st.subheader("Next Step")
    st.info(text)

def metric_row(items):
    cols = st.columns(len(items))
    i = 0
    while i < len(items):
        label, value = items[i]
        cols[i].metric(label, value)
        i += 1