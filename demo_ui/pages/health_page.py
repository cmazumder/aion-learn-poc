import streamlit as st
from demo_ui import backend
import time
from datetime import datetime

def render():
    st.markdown("## Health Check")
    st.markdown("Monitor the operational status of the AION pipeline components.")

    st.markdown("""
        <style>
        .health-card {
            border: 1px solid #e6eef8;
            border-radius: 12px;
            padding: 18px;
            background-color: #fcfdff;
            box-shadow: 0 4px 12px rgba(2,6,23,0.04);
            margin-bottom: 1rem;
        }
        .status-healthy { background-color: #dcfce7; border-left: 5px solid #22c55e; }
        .status-degraded { background-color: #fee2e2; border-left: 5px solid #ef4444; }
        </style>
    """, unsafe_allow_html=True)

    # --- Top controls ---
    col1, col2 = st.columns([3, 1])
    auto_refresh = col2.toggle("Auto-refresh (10s)", value=False, key="health_auto_refresh")
    col1.button("🔄 Refresh", use_container_width=False) # The button's existence triggers a rerun
    
    # --- Auto-refresh logic ---
    # Place this near the top for clarity. If the toggle is on, it will sleep and rerun.
    if auto_refresh:
        try:
            time.sleep(10)
            st.rerun()
        except Exception as e:
            st.session_state.health_auto_refresh = False # Disable on error to prevent loop
            st.warning(f"Auto-refresh disabled due to an error: {e}")
            
    # --- Data Fetching ---
    spinner_text = "Running health check..." if not st.session_state.get("health_auto_refresh") else "Refreshing..."
    with st.spinner(spinner_text):
        try:
            health = backend.sync_health_check()
        except Exception as e:
            st.error("Failed to run health check.")
            st.exception(e)
            return

    last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall = health.get("overall", "unknown")
    components = health.get("components", {})

    # --- Overall Status Card ---
    st.markdown("#### Overall Status")
    status_class = "status-healthy" if overall == "healthy" else "status-degraded"
    status_message = "All systems are currently operational" if overall == "healthy" else "One or more components are reporting issues"
    icon = "✅" if overall == "healthy" else "⚠️"
    st.markdown(f"""
        <div class="health-card {status_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: #1e293b;">{icon} {overall.title()}</div>
                    <p style="margin: 0.25rem 0 0 0; color: #475569;">{status_message}.</p>
                </div>
                <p style="margin: 0; color: #94a3b8; font-size: 0.8rem; text-align: right; white-space: nowrap;">Last checked: {last_checked}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Component Status")

    # --- Component Cards ---
    if not components:
        st.info("No component health data available.")
    else:
        num_cols = len(components) if len(components) <= 4 else 4
        cols = st.columns(num_cols)
        for i, (comp, status) in enumerate(components.items()):
            icon = "✅" if status == "healthy" else "⚠️"
            with cols[i % num_cols]:
                st.markdown(f"""
                    <div class="health-card">
                        <p style="font-size: 0.9rem; font-weight: 500; color: #64748b; margin: 0 0 0.5rem 0;">{comp.title()}</p>
                        <p style="font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0;">{icon} {status.title()}</p>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    with st.expander("Raw Health Data"):
        st.json(health)

    st.markdown("---")
    with st.expander("Live Log Stream (Last 200 Lines)"):
        log_content = backend.get_log_content(lines=200)
        st.code(log_content, language='log', line_numbers=True)
