import streamlit as st
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import markdown
import uuid
from demo_ui import backend

def render():
    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    def _make_id(): return str(uuid.uuid4())

    def _safe(x):
        try: return "" if x is None else str(x)
        except: return ""

    def _append(user, aion, sources=None, metadata=None):
        msg = {
            "id": _make_id(),
            "user": _safe(user),
            "aion": _safe(aion),
            "sources": sources or [],
            "metadata": metadata or {},
            "ts": datetime.utcnow().isoformat() + "Z"
        }
        st.session_state.chat_history.append(msg)

    def _bubble(msg):
        # --- timestamp ---
        try:
            ts = datetime.fromisoformat(msg['ts'].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except:
            ts = "now"

        # --- user bubble ---
        st.markdown(
            f"""
            <div style='display:flex;justify-content:flex-end;margin:4px 0 12px 0;'>
              <div style='max-width:75%;background:#0d6efd;color:white;
                          padding:10px 14px;border-radius:18px 18px 6px 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);'>
                {msg['user'].replace(chr(10), '<br/>')}
                <div style='font-size:0.7rem;text-align:right;color:#e0e0e0;margin-top:4px;'>{ts}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # --- bot bubble ---
        st.markdown(
            f"""
            <div style='display:flex;justify-content:flex-start;margin:4px 0 12px 0;'>
              <div style='width:36px;height:36px;border-radius:10px;background:#F7B32B;
                          display:flex;align-items:center;justify-content:center;
                          font-weight:bold;margin-right:10px;'>A</div>
              <div style='max-width:75%;background:#eef8ff;color:#071433;
                          padding:10px 14px;border-radius:18px 18px 18px 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);'>
                <!-- Render the markdown content as HTML -->
                {markdown.markdown(msg['aion'], extensions=['fenced_code', 'tables'])}
                <div style='font-size:0.7rem;text-align:right;color:#94a3b8;margin-top:4px;'>{ts}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- sources and metadata ---
        sources = msg.get("sources", [])
        metadata = msg.get("metadata", {})

        if sources or metadata:
            with st.expander("metadata info", expanded=False):
                # The backend returns performance metrics in the top-level metadata dict.
                demo_meta = {
                    "Retrieval Strategy": metadata.get("query_type"),
                    "Prompt Template": metadata.get("template_type"),
                    "Retrieval Time": f"{metadata.get('retrieval_time', 'N/A')}s",
                    "Augmentation Time": f"{metadata.get('augmentation_time', 'N/A')}s",
                    "Total Time": f"{metadata.get('total_time', 'N/A')}s",
                    "Contexts Returned": metadata.get("contexts_returned"),
                    "Context Hit": "Yes" if metadata.get("hit") else "No",
                    "LLM Model": metadata.get("llm_model"),
                    "Prompt Tokens": metadata.get("prompt_tokens"),
                    "Response Tokens": metadata.get("response_tokens"),
                }
                # Filter out any keys that have no value
                demo_meta = {k: v for k, v in demo_meta.items() if v is not None and v not in ["N/As", "N/A"]}

                # Use columns for a tight, professional layout
                col1, col2 = st.columns([1, 1.5])

                if demo_meta:
                    with col1:
                        st.markdown("<b style='color: #475569; font-size: 0.9rem;'>Performance</b>", unsafe_allow_html=True)
                        # Use st.code for syntax highlighting and custom CSS for subtle styling
                        st.code(json.dumps(demo_meta), language='json')

                if sources:
                    with col2:
                        st.markdown("<b style='color: #475569; font-size: 0.9rem;'>Sources</b>", unsafe_allow_html=True)
                        sources_html = "<div style='font-size: 0.85rem; margin-top: 5px;'>"
                        for src in sources:
                            sources_html += f"<div style='margin-bottom: 4px;'>- <code>{src}</code></div>"
                        st.markdown(sources_html, unsafe_allow_html=True)

    # ------------------------------------------------------
    # State
    # ------------------------------------------------------
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ------------------------------------------------------
    # Layout Styling — CHAT BOX FIXED BOTTOM, HISTORY ABOVE
    # ------------------------------------------------------
    # This CSS uses Grid to create a layout with a scrollable history and a fixed footer.
    st.markdown(
    """
    <style>
    /* Main container for the chat page, using CSS Grid */
    .aion-container {
        display: grid;
        grid-template-rows: 1fr auto; /* History takes all space, footer is auto-sized */
        height: calc(100vh - 160px); /* Adjust height to fit viewport */
    }
    
    /* Custom styling for the code block in "metadata info" */
    div[data-testid="stExpander"] div[data-testid="stCodeBlock"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        padding: 8px;
        font-size: 0.8rem;
    }

    /* Chat history area */
    .aion-history {
        overflow-y: auto; /* This makes the history scrollable */
        padding: 12px 6px 0 6px;
    }

    /* Footer containing the chat input box */
    .aion-footer {
        background: white;
        padding: 12px;
        box-shadow: 0 -4px 12px rgba(0,0,0,0.05);
        z-index: 999;
        /* This is part of the grid, so it stays at the bottom */
    }

    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------
    # Title bar
    # ------------------------------------------------------
    st.markdown("""
        <div style="border-bottom: 1px solid #e6e6e6; padding-bottom: 8px; margin-bottom: 15px;">
            <h3 style="margin-bottom: 0.1rem;">AION — Chat</h3>
            <p style="font-size: 0.85rem; color: #6c757d; margin: 0;">
                AI-driven RCA & diagnostics — Chat with the knowledge base
            </p>
        </div>
    """, unsafe_allow_html=True)


    # ------------------------------------------------------
    # Main container (history ABOVE, footer BELOW)
    # ------------------------------------------------------
    container_class = "aion-container" if st.session_state.chat_history else ""
    st.markdown(f"<div class='{container_class}'>", unsafe_allow_html=True)

    # ======================================================
    # CHAT HISTORY (always ABOVE the chat box)
    # ======================================================
    st.markdown("<div class='aion-history' id='chat-history'>", unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown("<div style='color:#94a3b8;text-align:center;padding-top:20px;'>No conversation yet — say hi 👋</div>", unsafe_allow_html=True)
    else:
        for m in st.session_state.chat_history:
            _bubble(m)
    
    # Clear chat button inside history but outside loop
    if st.session_state.chat_history:
        if st.button("Clear Chat History", key="clear_chat"):
            st.session_state.chat_history = []

    st.markdown("</div>", unsafe_allow_html=True)  # close history

    # ======================================================
    # CHAT BOX — FIXED AT BOTTOM (footer)
    # ======================================================
    st.markdown("<div class='aion-footer'>", unsafe_allow_html=True)

    # --- chat input form ---
    with st.form(key="chat_form", clear_on_submit=True):
        user_query = st.text_area(
            "Ask a question",
            placeholder='Try: "What does error E002 mean?"',
            height=90,
            label_visibility="collapsed"
        )
        attachment = st.file_uploader(
            "Attach a file (e.g., logs)",
            type=['txt', 'log', 'md', 'json'],
            label_visibility="collapsed"
        )
        c1, c2 = st.columns([1, 1])
        send = c1.form_submit_button("Send")
        short = c2.form_submit_button("Short Reply")

        # --------------------------------------------------
        # Process SEND with attachment
        # --------------------------------------------------
        if send and user_query.strip() and attachment is not None:
            with st.spinner(f"Analyzing {attachment.name}..."):
                # Save temp file to pass its path to backend
                temp_dir = Path("data/temp_uploads")
                temp_dir.mkdir(exist_ok=True)
                file_path = temp_dir / attachment.name
                file_path.write_bytes(attachment.getvalue())
                res = backend.sync_query_with_attachment(user_query, str(file_path))
            
            # Check for and display a detailed error if one occurred
            if "error" in res.get("metadata", {}):
                error_detail = res["metadata"]["error"]
                _append(user_query, f"**Error Processing Attachment:**\n\n```\n{error_detail}\n```")
            else:
                _append(user_query, res.get("answer", ""), res.get("sources", []), res.get("metadata", {}))
            st.rerun()
        # --------------------------------------------------
        # Process SEND immediately — response shows above instantly
        # --------------------------------------------------
        if send and user_query.strip():
            with st.spinner("AION is thinking..."):
                try:
                    res = backend.sync_query_knowledge_base(user_query)
                except Exception as exc:
                    _append(user_query, f"Error: {_safe(exc)}")
                else:
                    ans = _safe(res.get("answer", "")) if isinstance(res, dict) else _safe(res)
                    _append(user_query, ans,
                            res.get("sources", []) if isinstance(res, dict) else [],
                            res.get("metadata", {}) if isinstance(res, dict) else {})
            st.session_state.last_query = user_query
            st.rerun()

        # --------------------------------------------------
        # Short summary
        # --------------------------------------------------
        if short and st.session_state.get("last_query"):
            q = f"Summarize this in 2–3 bullet points: {st.session_state.last_query}"
            with st.spinner("AION is summarizing..."):
                res = backend.sync_query_knowledge_base(q)
            ans = _safe(res.get("answer", "")) if isinstance(res, dict) else _safe(res)
            _append(q, ans,
                    res.get("sources", []) if isinstance(res, dict) else [],
                    res.get("metadata", {}) if isinstance(res, dict) else {})
            st.rerun()

    # --- quick prompts ---
    try:
        prompts = backend.get_sample_queries()[:8]
    except:
        prompts = []

    if prompts:
        cols = st.columns(len(prompts))
        for i, p in enumerate(prompts):
            if cols[i].button(p, key=f"q{i}"):
                with st.spinner("AION is thinking..."):
                    res = backend.sync_query_knowledge_base(p)
                ans = _safe(res.get("answer", "")) if isinstance(res, dict) else _safe(res)
                _append(p, ans,
                        res.get("sources", []) if isinstance(res, dict) else [],
                        res.get("metadata", {}) if isinstance(res, dict) else {})
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # close footer
    st.markdown("</div>", unsafe_allow_html=True)  # close container

    # ------------------------------------------------------
    # Auto-scroll to latest
    # ------------------------------------------------------
    if st.session_state.chat_history:
        st.components.v1.html(
            """
            <script>
            const chat = window.parent.document.getElementById("chat-history");
            if(chat){ chat.scrollTop = chat.scrollHeight; }
            </script>
            """,
            height=0,
            scrolling=False
        )