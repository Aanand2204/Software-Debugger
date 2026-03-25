import streamlit as st
from src.agents.orchestrator import Orchestrator
from src.database.db_manager import save_analysis_result
from src.ui.components.diagrams import display_content_with_diagrams
from src.ui.state import DIAG_OPTIONS

def render_visualizations_tab():
    st.header("🎨 Visualizations & Diagrams")
    st.session_state.diag_selection = st.multiselect("Select diagram types:", DIAG_OPTIONS, default=st.session_state.diag_selection)
    
    if st.button("🔄 Regenerate Selected Diagrams"):
        if st.session_state.repo_summary:
            if st.session_state.diag_selection:
                with st.spinner("Generating diagrams..."):
                    orchestrator = Orchestrator()
                    new_diag_msg = orchestrator.generate_diagrams_only(st.session_state.repo_summary, st.session_state.diag_selection)
                    if new_diag_msg.get("name") != "Error":
                        st.session_state.analysis_results = [m for m in st.session_state.analysis_results if m.get("name") != "Diagram_Generator"]
                        st.session_state.analysis_results.append(new_diag_msg)
                        save_analysis_result(st.session_state.get("repo_url") or st.session_state.get("local_repo_path"), st.session_state.analysis_results)
                        st.success("Diagrams updated!")
                    else: st.error(new_diag_msg.get("content"))
            else: st.warning("Select types first.")
        else: st.warning("Run analysis first.")

    st.divider()
    found_diagrams = False
    if st.session_state.analysis_results:
        for d_idx, msg in enumerate(st.session_state.analysis_results):
            if msg.get("name") == "Diagram_Generator":
                found_diagrams = True
                display_content_with_diagrams(msg.get("content", ""), key_prefix=f"tab3_{d_idx}")
    if not found_diagrams:
        st.info("No diagrams available.")
