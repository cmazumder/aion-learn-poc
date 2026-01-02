# demo_ui/pages/statistics_page.py
import streamlit as st
from datetime import datetime
import pandas as pd

from demo_ui import backend

def render():
    # st.set_page_config is only allowed in the main app.py
    st.markdown("""
        <style>
        .card {
            border: 1px solid #e6eef8;
            border-radius: 12px;
            padding: 18px;
            background-color: #fcfdff;
            box-shadow: 0 4px 12px rgba(2,6,23,0.04);
            margin-bottom: 1rem;
            height: 100%;
        }
        .metric-card {
            border: 1px solid #e6eef8;
            border-radius: 12px;
            padding: 18px;
            background-color: #fcfdff;
            box-shadow: 0 4px 12px rgba(2,6,23,0.04);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## System Analytics")
    st.markdown("Real-time ingestion, corpus, and vector-store statistics.")

    # Top controls: Refresh + last fetched
    cols_top = st.columns([1, 5])
    with cols_top[0]:
        if st.button("Refresh"):
            st.rerun()
    with cols_top[1]:
        if "stats_last_fetched" in st.session_state:
            try:
                ts = datetime.fromisoformat(st.session_state['stats_last_fetched'].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S UTC")
                st.caption(f"Last fetched: {ts}")
            except:
                st.caption(f"Last fetched: {st.session_state['stats_last_fetched']}")
        else:
            st.markdown("**Last:** -")

    with st.spinner("Loading system statistics..."):
        try:
            stats = backend.sync_get_system_stats() or {}
        except Exception as exc:
            st.error("Failed to load system statistics from backend.")
            st.exception(exc)
            return

    # record fetch time
    st.session_state["stats_last_fetched"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    # defensive extraction
    pipeline_stats = stats.get("pipeline_stats", {}) or {}
    vector_store = stats.get("vector_store", {}) or {}
    corpus_profile = stats.get("corpus_profile", {}) or {}
    corpus_report = stats.get("corpus_report", {}) or {}
    query_metrics = stats.get("query_metrics", {}) or {}
    recent_queries = stats.get("recent_queries", []) or []
    alerts = stats.get("alerts", []) or []
    configuration = stats.get("configuration", {}) or {}

    st.markdown("---")

    # KPI metrics
    st.markdown("#### Key Metrics")
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        with st.container(border=True):
            st.metric(
                "Total Documents",
                value=pipeline_stats.get("total_documents", "—"),
                delta=pipeline_stats.get("documents_added_last_run", None),
            )
    with kpi_cols[1]:
        with st.container(border=True):
            st.metric(
                "Total Chunks",
                value=pipeline_stats.get("total_chunks", "—"),
            )
    with kpi_cols[2]:
        with st.container(border=True):
            st.metric(
                "Stored Chunks",
                value=vector_store.get("stored_chunks", "—"),
            )
    with kpi_cols[3]:
        with st.container(border=True):
            st.metric(
                "Total Queries",
                value=query_metrics.get("total_queries", 0),
            )
    with kpi_cols[4]:
        with st.container(border=True):
            last_ing = pipeline_stats.get("last_ingestion_duration_seconds")
            st.metric(
                "Last Ingestion (s)",
                value=round(last_ing, 2) if isinstance(last_ing, (int, float)) else "—",
            )

    st.markdown("---")

    left, right = st.columns([2, 1])

    # Left: charts and tables
    with left:
        with st.container(border=True):
            st.subheader("Corpus Composition")
            # Documents per source directory (bar)
            source_dirs = corpus_profile.get("source_directories", {}) or {}
            if source_dirs:
                try:
                    df_dirs = pd.DataFrame(source_dirs.items(), columns=["Directory", "Documents"]).sort_values("Documents", ascending=False)
                    st.bar_chart(df_dirs.set_index("Directory"))
                except Exception as e:
                    st.warning("Could not render source directories chart.")
            else:
                st.info("No directory breakdown available.")

        with st.container(border=True):
            st.subheader("Directory Ingestion Summary")
            dir_summaries = corpus_report.get("directory_summaries", []) or []
            if dir_summaries:
                try:
                    rows = []
                    for d in dir_summaries:
                        if isinstance(d, dict):
                            rows.append({
                                "Directory": d.get("directory", "unknown"),
                                "Files Processed": int(d.get("files_processed", 0) or 0),
                                "Documents Added": int(d.get("documents_added", 0) or 0),
                            })
                    df_sum = pd.DataFrame(rows).set_index("Directory")
                    if not df_sum.empty:
                        st.line_chart(df_sum)
                    else:
                        st.info("Directory summaries present but empty.")
                except Exception as e:
                    st.warning("Could not render directory summary chart.")
            else:
                st.info("No directory summaries available.")

    # Right: vector store, queries, alerts, config preview
    with right:
        with st.container(border=True):
            st.subheader("AI Quality Metrics")
            ai_quality_kv = {
                "Hit Ratio": query_metrics.get("hit_ratio"),
                "Avg. Confidence": query_metrics.get("avg_confidence"),
                "Avg. Retrieval Score": query_metrics.get("avg_retrieval_score"),
                "Last Query Confidence": query_metrics.get("last_query_confidence"),
            }
            for key, value in ai_quality_kv.items():
                if value is not None:
                    # Format percentages and floats nicely
                    val_str = f"{value:.2%}" if "Ratio" in key or "Confidence" in key else f"{value:.4f}" if isinstance(value, float) else str(value)
                    st.markdown(f"**{key}:** `{val_str}`")
                else:
                    st.markdown(f"**{key}:** `N/A`")

        with st.container(border=True):
            st.subheader("Corpus Profile")
            corpus_kv = {
                "Avg. Chunk Length": corpus_profile.get("average_chunk_length"),
                "Avg. Tokens / Chunk": corpus_profile.get("average_tokens_per_chunk"),
                "Chunks / Document": corpus_profile.get("chunks_per_document"),
                "Duplicate Chunks": corpus_profile.get("duplicate_chunks"),
                "Empty Chunks": corpus_profile.get("empty_chunks"),
                "Est. Token Count": corpus_profile.get("estimated_token_count"),
            }
            for key, value in corpus_kv.items():
                val_str = f"{value:,}" if isinstance(value, int) else str(value) if value is not None else "—"
                st.markdown(f"**{key}:** `{val_str}`")

        with st.container(border=True):
            st.subheader("Vector Store")
            vs_table = {
                "Provider": vector_store.get("provider"),
                "Collection": vector_store.get("collection_name") or vector_store.get("collection"),
                "Tracked Files": vector_store.get("tracked_files"),
                "Stored Chunks": vector_store.get("stored_chunks"),
                "Last Synced": vector_store.get("last_synced_at"),
            }
            # Create a cleaner display than st.json
            for key, value in vs_table.items():
                st.markdown(f"**{key}:** `{value}`")

        if alerts:
            with st.container(border=True):
                st.subheader("⚠️ Alerts")
                for a in alerts:
                    st.warning(a)
                else:
                    st.info("No alerts.")

    st.markdown("---")
    with st.expander("Raw stats (full JSON)", expanded=False):
        st.json(stats)