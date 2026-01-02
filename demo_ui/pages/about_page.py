import streamlit as st
import json
from datetime import datetime
from typing import Any, Dict
from collections import OrderedDict
import pandas as pd


def render():
    """
    Visually appealing infographic page for the AION demo.
    Focus: short, speakable 30-40s summary + a quick visual tour.
    """

    # local import so page import is cheap if backend import is heavy
    from demo_ui import backend

    # -----------------------
    # Helpers
    # -----------------------
    def _normalize(x: Any):
        """Recursively convert config objects into JSON-serializable primitives."""
        if isinstance(x, (str, int, float, bool)) or x is None:
            return x
        if hasattr(x, "__fspath__"):
            try:
                return str(x)
            except Exception:
                return repr(x)
        if isinstance(x, dict):
            return {k: _normalize(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [_normalize(v) for v in x]
        if hasattr(x, "model_dump"):
            try:
                return _normalize(x.model_dump())
            except Exception:
                pass
        if hasattr(x, "__dict__"):
            try:
                return _normalize(vars(x))
            except Exception:
                pass
        try:
            return str(x)
        except Exception:
            return repr(x)

    def _flatten(d: Dict[str, Any], parent: str = "") -> OrderedDict:
        out = OrderedDict()
        if not isinstance(d, dict):
            return out
        for k, v in d.items():
            path = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                out.update(_flatten(v, path))
            else:
                out[path] = v
        return out

    def _preview(v, n=140):
        try:
            if isinstance(v, (str, int, float, bool)) or v is None:
                s = str(v)
            else:
                s = json.dumps(v, ensure_ascii=False)
        except Exception:
            s = str(v)
        s = s.replace("\n", " ")
        return (s[: n - 3] + "...") if len(s) > n else s

    # -----------------------
    # Load config
    # -----------------------
    try:
        raw_cfg = backend.get_config() or {}
    except Exception as exc:
        st.error("Could not load configuration from backend.")
        st.exception(exc)
        return

    cfg = _normalize(raw_cfg)
    flat = _flatten(cfg)

    # -----------------------
    # Build short speakable summary
    # -----------------------
    llm = cfg.get("llm", {}) or {}
    embedding = cfg.get("embedding", {}) or {}
    vectorstore = cfg.get("vectorstore", {}) or {}
    chunking = cfg.get("chunking", {}) or {}
    retrieval = cfg.get("retrieval", {}) or {}

    one_line = (
        f"LLM: {llm.get('provider','-')} {llm.get('model', llm.get('chat_model','-'))} • "
        f"Embeddings: {embedding.get('model','-')} • "
        f"Vector store: {vectorstore.get('collection', vectorstore.get('name','-'))} • "
        f"Chunking: {chunking.get('method','-')}({chunking.get('chunk_size','-')}) • "
        f"Retrieval: top_k={retrieval.get('top_k','-')}"
    )

    # -----------------------
    # High-level "Story" section
    # -----------------------
    st.markdown("### The AION Story")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 🔍 The Problem")
        st.markdown("Operational knowledge (logs, docs, tickets) is siloed and vast. Finding root causes is a slow, manual process of connecting dots across different systems.")
    with c2:
        st.markdown("#### 💡 The Solution")
        st.markdown("AION creates a unified intelligence layer. It ingests data from all sources and uses a RAG pipeline to provide fast, contextual answers to natural language questions.")
    with c3:
        st.markdown("#### 🚀 The Impact")
        st.markdown("Dramatically reduce diagnostic time from days to hours. Empower engineers with instant access to correlated information, improving resolution speed and accuracy.")

    st.markdown("---")

    # -----------------------
    # Visual cards (big) — audience friendly
    # -----------------------
    st.markdown("### Core Components")
    def _card(icon: str, title: str, headline: str, sub: str, col):
        with col:
            st.markdown(
                f"""
                <div style="border: 1px solid #e6eef8; border-radius:12px; padding:18px; background-color: #fcfdff;
                            box-shadow:0 4px 12px rgba(2,6,23,0.04); margin-bottom:12px; height: 160px;">
                  <div style="font-size: 1.5rem; margin-bottom: 8px;">{icon}</div>
                  <div style="font-weight:600; font-size:15px; color:#0f172a;">{title}</div>
                  <div style="font-size:13px; color:#475569; margin-top:4px;">{headline}<br><span style='font-size:11px; color:#94a3b8;'>{sub}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    cols = st.columns([1, 1, 1])
    _card("🧠", "LLM", f"{llm.get('provider','-')}/{llm.get('model', '-')}", "Synthesizes answers from context.", cols[0])
    _card("→", "Embedding", f"{embedding.get('model','-')}", "Converts text into searchable vectors.", cols[1])
    _card("🗄️", "Vector Store", f"{vectorstore.get('collection','-')}", "Stores and indexes document vectors.", cols[2])

    cols2 = st.columns([1, 1, 1])
    _card("✂️", "Chunking", f"{chunking.get('method','-')} (size: {chunking.get('chunk_size','-')})", "Splits docs into manageable pieces.", cols2[0])
    _card("🎯", "Retrieval", f"top_k = {retrieval.get('top_k','-')}", "Fetches the most relevant chunks.", cols2[1])
    _card("📝", "Ingestion", f"{len(cfg.get('corpus_subdirs',[]))} source types", "Loads data from various sources.", cols2[2])

    st.markdown("---")

    # -----------------------
    # Pipeline diagram (SVG) — screenshot-friendly
    # -----------------------
    st.subheader("Pipeline Diagram")
    emb_model = embedding.get("model", "-")
    ch_size = chunking.get("chunk_size", "-")
    collection_name = vectorstore.get("collection", "-")
    topk = retrieval.get("top_k", "-")

    svg = f'''
    <svg width="100%" height="160" viewBox="0 0 1200 160" xmlns="http://www.w3.org/2000/svg">
        <style>
            .box {{ fill: #f8fafc; stroke: #e2e8f0; rx: 8; ry: 8; }}
            .label {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; fill: #0f172a; font-weight: 600; }}
            .sub {{ font-size: 11px; fill: #64748b; }}
            .arrow {{ stroke: #cbd5e1; stroke-width: 2; marker-end: url(#arrowhead); }}
            .query-path {{ stroke: #4f46e5; stroke-width: 2.5; marker-end: url(#arrowhead-query); stroke-dasharray: 4; }}
        </style>
        <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6 Z" fill="#94a3b8"/>
            </marker>
            <marker id="arrowhead-query" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6 Z" fill="#4f46e5"/>
            </marker>
        </defs>

        <!-- Ingestion Path -->
        <rect x="20" y="40" width="160" height="60" class="box"/>
        <text x="100" y="65" text-anchor="middle" class="label">Corpus</text>
        <text x="100" y="82" text-anchor="middle" class="sub">Logs, Docs, Jira</text>

        <rect x="240" y="40" width="160" height="60" class="box"/>
        <text x="320" y="65" text-anchor="middle" class="label">Chunker</text>
        <text x="320" y="82" text-anchor="middle" class="sub">size={ch_size}</text>

        <rect x="460" y="40" width="160" height="60" class="box"/>
        <text x="540" y="65" text-anchor="middle" class="label">Embeddings</text>
        <text x="540" y="82" text-anchor="middle" class="sub">{emb_model}</text>

        <rect x="680" y="40" width="160" height="60" class="box"/>
        <text x="760" y="65" text-anchor="middle" class="label">Vector Store</text>
        <text x="760" y="82" text-anchor="middle" class="sub">{collection_name}</text>

        <!-- Query Path -->
        <rect x="900" y="40" width="160" height="60" class="box"/>
        <text x="980" y="65" text-anchor="middle" class="label">Retriever</text>
        <text x="980" y="82" text-anchor="middle" class="sub">top_k={topk}</text>

        <!-- Arrows -->
        <line x1="180" y1="70" x2="240" y2="70" class="arrow"/>
        <line x1="400" y1="70" x2="460" y2="70" class="arrow"/>
        <line x1="620" y1="70" x2="680" y2="70" class="arrow"/>
        <line x1="840" y1="70" x2="900" y2="70" class="query-path"/>
    </svg>
    '''

    st.components.v1.html(svg, height=200, scrolling=False)
    st.download_button("Download diagram (SVG)", data=svg, file_name=f"aion_pipeline_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.svg", mime="image/svg+xml", key="dl_svg_crux")

    st.markdown("---")

    # -----------------------
    # Speaker notes (30-40s script)
    # -----------------------
    st.markdown("""
        <div style="
            background-color: #f8f9fa; 
            border-left: 5px solid #0d6efd; 
            padding: 15px 20px; 
            margin-top: 20px; 
            border-radius: 5px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        ">
            <h4 style="margin-top: 0; color: #343a40;">✨ Key Differentiators</h4>
            <ul style="color: #495057; line-height: 1.7; padding-left: 20px; margin-bottom: 0;">
                <li><b>Multi-Source Ingestion:</b> Unifies knowledge from diverse sources like Jira, Confluence, logs, and release notes.</li>
                <li><b>Intelligent Augmentation:</b> Dynamically detects query intent (e.g., QA, Summarization, Troubleshooting) to provide tailored, accurate responses.</li>
                <li><b>Persistent Vector Store:</b> Ensures efficient, stateful document synchronization and fast retrieval via ChromaDB.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # -----------------------
    # Downloads (JSON & flattened CSV)
    # -----------------------
    payload = json.dumps(cfg, indent=2, ensure_ascii=False)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.download_button("Download full JSON", data=payload, file_name=f"aion_config_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json", mime="application/json", key="dl_json_crux")
    with col_b:
        # try pandas CSV; fallback to simple CSV (sanitizing quotes)
        try:            
            df_flat = pd.DataFrame(list(flat.items()), columns=["key", "value"])
            df_flat["preview"] = df_flat["value"].apply(lambda x: _preview(x, n=120))
            csv = df_flat[["key", "preview"]].to_csv(index=False)
            st.download_button("Download flattened CSV", data=csv, file_name=f"aion_config_flat_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv", mime="text/csv", key="dl_csv_crux")
        except Exception:
            csv_lines = ["key,preview"]
            for k, v in flat.items():
                prev = _preview(v).replace('"', "'")
                # safe CSV line (double-quoted fields)
                csv_lines.append(f'"{k}","{prev}"')
            csv = "\n".join(csv_lines)
            st.download_button("Download flattened CSV", data=csv, file_name=f"aion_config_flat_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv", mime="text/csv", key="dl_csv_fallback_crux")

    st.markdown("---")

    # -----------------------
    # Developer view (collapsed)
    # -----------------------
    with st.expander("Developer view — full normalized config", expanded=False):
        st.json(cfg)
