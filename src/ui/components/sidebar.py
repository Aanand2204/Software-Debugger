import streamlit as st
import os

def render_sidebar():
    """Renders the sidebar configuration and returns button states."""
    def normalize_path():
        if "local_repo_path" in st.session_state and st.session_state.local_repo_path:
            cleaned = st.session_state.local_repo_path.strip().strip('"').strip("'")
            st.session_state.local_repo_path = os.path.normpath(cleaned)

    with st.sidebar:
        st.header("Configuration")
        
        st.text_input("GitHub Repo URL", key="repo_url", placeholder="https://github.com/user/repo")
        st.text_input("Local Repo Path", key="local_repo_path", placeholder="C:/path/to/repo", on_change=normalize_path)
        
        process_button = st.button("Analyze Codebase")
        reset_button = st.button("Reset Session")
        
        st.sidebar.divider()
        
    if reset_button:
        # Save the layout setting if any, then clear
        st.session_state.clear()
        st.session_state["repo_url"] = ""
        st.session_state["local_repo_path"] = ""
        st.rerun()

    if process_button:
        st.session_state.initial_analysis_requested = True
        # Reset workflow state on a fresh analysis click
        st.session_state.patch_stage = "SUGGESTED"
        st.session_state.analysis_results = []
        st.session_state.pending_patches = []

    return process_button
