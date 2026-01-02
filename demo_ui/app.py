import streamlit as st
from demo_ui.pages import about_page, chat_page, health_page, inats, health

st.set_page_config(page_title="AION RAG Demo Dashboard", layout="wide")

st.sidebar.title("AION RAG Demo")
menu = [
    "📄 Ingest Sample Documents",
    "🔍 Query Knowledge Base",
    "📊 Show System Statistics",
    "🩺 Health Check",
    "⚙️ Show Configuration"
]
choice = st.sidebar.radio("Menu", menu)

if choice == menu[0]:
    if uploaded_files:
        # Save uploaded files to disk and ingest
        st.write("**Sources:**", result.sources)
    st.subheader("Alerts")

page_map = {
    menu[0]: ingest.render,
    menu[1]: chat_page.render,
    menu[2]: stats.render,
    menu[3]: health_page.render,
    menu[4]: about_page.render,
}

page_map[choice]()
