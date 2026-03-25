import streamlit as st
import os

def render_final_apply_stage():
    st.success("✨ Excellent! Final Step: Apply these verified changes to your original workspace.")
    l_path = st.session_state.get("local_repo_path")
    if l_path:
        if st.button("🚀 Apply Changes to Original Folder", type="primary", use_container_width=True):
            with st.spinner("Syncing changes..."):
                try:
                    import shutil
                    success_count = 0
                    for rel_path in st.session_state.patch_status:
                        res = st.session_state.patch_status[rel_path]
                        if res.get("status") != "Success": continue
                        
                        clean_rel_path = rel_path.lstrip("/\\")
                        src = os.path.join(st.session_state.cloned_repo_path, clean_rel_path)
                        dst = os.path.join(st.session_state.local_repo_path, clean_rel_path) 
                        
                        if os.path.exists(src):
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                            st.write(f"✅ Applied: `{clean_rel_path}`")
                            success_count += 1
                        else:
                            st.error(f"❌ Patch failed for {clean_rel_path}: Source not found at {src}")

                    if success_count > 0:
                        st.balloons()
                        st.session_state.patch_stage = "COMPLETED"
                        st.session_state.last_exec_output = None
                        st.rerun()
                    else:
                        st.error("No compatible patches were successfully applied.")
                except Exception as e:
                    st.error(f"Commit failed: {e}")
    else:
        st.info("Direct workspace commit is only available for Local Repo Paths.")
