import streamlit as st
from demo_ui import backend
from pathlib import Path

def render():
    st.header("Ingest Sample Documents")
    st.info("Upload or select sample documents to ingest into the knowledge base.")
    uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)
    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded.")
        sample_dir = Path("data/sample_docs")
        sample_dir.mkdir(parents=True, exist_ok=True)
        file_paths = []
        for file in uploaded_files:
            file_path = sample_dir / file.name
            file_paths.append(str(file_path))
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
        st.info("Starting ingestion...")
        with st.spinner("Ingesting documents..."):
            stats = backend.sync_ingest_documents(file_paths)
        st.success("Ingestion complete!")
        st.json(stats)
