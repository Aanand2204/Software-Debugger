import streamlit as st
from src.ui.components.patch_stages import (
    render_suggested_stage,
    render_testing_stage,
    render_executing_stage,
    render_verifying_stage,
    render_final_apply_stage,
    render_completed_stage,
    render_executing_final_stage,
    render_rectify_stage
)

def render_patch_tab():
    st.header("🛡️ Patch & Test")
    if st.session_state.get("repo_url"):
        st.warning("⚠️ The Patch & Test workflow is disabled for remote GitHub repositories. Please analyze a local repository to use this feature.")
    elif st.session_state.analysis_results:
        # --- Safe Patching Workflow (Sequential) ---
        if st.session_state.pending_patches:
            st.divider()
            st.subheader("🛡️ Safe Patching Workflow")

            # Initialize workflow stage if not set
            if "patch_stage" not in st.session_state:
                st.session_state.patch_stage = "SUGGESTED"
            if "last_exec_output" not in st.session_state:
                st.session_state.last_exec_output = None
            if "test_command" not in st.session_state:
                st.session_state.test_command = ""

            # --- GLOBAL ERROR GUARD ---
            # If any patch has an error, we stay in SUGGESTED and show why.
            has_patch_errors = any(r.get("status") != "Success" for r in st.session_state.patch_status.values())
            if has_patch_errors and st.session_state.patch_stage != "SUGGESTED":
                st.session_state.patch_stage = "SUGGESTED"
                st.rerun()

            # State Router
            if st.session_state.patch_stage == "SUGGESTED":
                render_suggested_stage()
            elif st.session_state.patch_stage == "TESTING":
                render_testing_stage()
            elif st.session_state.patch_stage == "EXECUTING":
                render_executing_stage()
            elif st.session_state.patch_stage == "VERIFYING":
                render_verifying_stage()
            elif st.session_state.patch_stage == "FINAL_APPLY":
                render_final_apply_stage()
            elif st.session_state.patch_stage == "COMPLETED":
                render_completed_stage()
            elif st.session_state.patch_stage == "EXECUTING_FINAL":
                render_executing_final_stage()
            elif st.session_state.patch_stage == "RECTIFY":
                render_rectify_stage()
        else:
            st.info("No patches were suggested in the current analysis.")
    else:
        st.info("Run an analysis first to unlock the patching workflow.")
