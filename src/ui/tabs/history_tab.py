import streamlit as st
from src.database.db_manager import get_analysis_history
from src.ui.components.diagrams import display_content_with_diagrams

def render_history_tab():
    st.header("Recent Analysis History")
    history = get_analysis_history()
    if history:
        for item in history:
            repo_url = item.get('repo_url', 'Unknown')
            parts = repo_url.rstrip('/').split('/')
            repo_display = "/".join(parts[-2:]) if len(parts) >= 2 else repo_url
            with st.expander(f"📁 {repo_display}"):
                st.caption(f"Analyzed on: {item.get('timestamp')}")
                for h_idx, msg in enumerate(item['results']):
                    role = msg.get('name', 'Agent')
                    content = msg.get('content', '')
                    if role == "Diagram_Generator":
                        with st.expander("🖼️ View Diagrams", expanded=False):
                            display_content_with_diagrams(content, key_prefix=f"tab4_{item.get('timestamp')}_{h_idx}")
                    else: st.markdown(f"**{role}**: {content}")
    else: st.info("No history found.")
