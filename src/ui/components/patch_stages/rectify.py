import streamlit as st
from src.agents.orchestrator import Orchestrator

def render_rectify_stage():
    st.warning("⚠️ Let's fix it! Please provide your suggestions below.")
    feedback = st.text_area("What should be corrected?", value=st.session_state.rectification_feedback)
    if st.button("🔥 Re-generate Patches", type="primary", use_container_width=True):
        with st.status("Re-analyzing with feedback...", expanded=True) as status:
            orchestrator = Orchestrator()
            prompt = f"Repository Summary:\n{st.session_state.repo_summary}\n\nUSER FEEDBACK ON PREVIOUS PATCHES: {feedback}\n\nTask: Re-evaluate and suggest better patches."
            msg, is_err = orchestrator._run_step_with_rotation(
                orchestrator.factory.create_bug_detection_agent, 
                orchestrator.factory.create_user_proxy(), 
                prompt, 
                "Bug Re-detection"
            )
            if not is_err:
                file_list_str = "\n".join([f"- {f}" for f in st.session_state.workspace_files]) if st.session_state.get("workspace_files") else "None provided."
                patch_prompt = f"Previous Analysis:\n{msg}\n\nWorkspace File List (Available modules):\n{file_list_str}\n\nFeedback: {feedback}\n\nTask: Generate revised code patches."
                p_msg, p_is_err = orchestrator.run_patch_generation_cycle(
                    patch_prompt, 
                    st.session_state.get("workspace_files"), 
                    orchestrator.factory.create_user_proxy()
                )
                
                if not p_is_err:
                    for m in st.session_state.analysis_results:
                        if m.get("name") == "Patch_Generator": 
                            m["content"] = p_msg
                    
                    st.session_state.pending_patches = orchestrator.parse_patches(p_msg)
                    
                    if st.session_state.cloned_repo_path:
                        results = orchestrator.apply_patches_to_dir(
                            st.session_state.pending_patches, 
                            st.session_state.cloned_repo_path, 
                            st.session_state.get("workspace_files")
                        )
                        st.session_state.patch_status = {r['path']: r for r in results}
                        st.session_state.patch_stage = "TESTING"
                    else:
                        st.session_state.patch_stage = "SUGGESTED"
                    
                    st.session_state.last_exec_output = None
                    status.update(label="Patches revised and applied to clone!", state="complete")
                    st.rerun()
                else: st.error("Patch generation failed.")
            else: st.error("Detection failed.")
    
    if st.button("⬅️ Back"):
        st.session_state.patch_stage = "VERIFYING"
        st.rerun()
