import streamlit as st
from src.agents.orchestrator import Orchestrator

def render_suggested_stage():
    st.info(f"Step 1: AI has suggested {len(st.session_state.pending_patches)} patches. Would you like to test them in an isolated clone?")
    if st.button("🧪 Yes, Test in Isolated Clone", use_container_width=True):
        if st.session_state.cloned_repo_path:
            with st.spinner("Applying patches to clone..."):
                orchestrator = Orchestrator()
                results = orchestrator.apply_patches_to_dir(st.session_state.pending_patches, st.session_state.cloned_repo_path, st.session_state.get("workspace_files"))
                st.session_state.patch_status = {r['path']: r for r in results}
                
                # Fail-Fast: Check for errors
                errors = [r for r in results if r.get("status") != "Success"]
                if errors:
                    for err in errors:
                        st.error(f"❌ Failed to apply patch to `{err['path']}`: {err['status']}")
                    st.warning("Please check your API keys/quota and try again.")
                else:
                    st.session_state.test_command = orchestrator.suggest_entry_point(st.session_state.cloned_repo_path)
                    st.session_state.patch_stage = "TESTING"
                    st.rerun()
        else:
            st.warning("No cloned repository found. Run analysis first.")
