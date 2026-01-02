# app.py — Simple, reliable sidebar navigation (one-click, same tab)
import streamlit as st
import traceback

from demo_ui import backend
from demo_ui.pages import about_page, chat_page, ingest_page, analytics_page, health_page

st.set_page_config(page_title="AION RAG Demo", layout="wide")

# --- Main App Layout ---

try:
    # Create horizontal tabs for navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Chat", "Ingest", "Analytics", "Health", "About"])

    with tab1:
        chat_page.render()

    with tab2:
        ingest_page.render()

    with tab3:
        analytics_page.render()

    with tab4:
        health_page.render()

    with tab5:
        about_page.render()

except Exception:
    st.error("An error occurred while rendering the page.")
    st.code(traceback.format_exc())