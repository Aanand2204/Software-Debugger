import streamlit as st

def render_verifying_stage():
    st.subheader("🖥️ Execution Output")
    if st.session_state.last_exec_output:
        st.code(st.session_state.last_exec_output)
    else:
        st.warning("No execution output captured.")
    
    ret_code = st.session_state.get("last_exec_returncode", 0)
    if ret_code != 0:
        st.error(f"❌ Execution failed with exit code {ret_code}. Please review the errors.")
        if not st.session_state.get("rectification_feedback"):
            err_lines = [line for line in (st.session_state.last_exec_output or "").split("\n") if "Error" in line or "Exception" in line or "Traceback" in line]
            st.session_state.rectification_feedback = "The code crashed during execution. " + " ".join(err_lines[-3:]) if err_lines else f"Execution failed with exit code {ret_code}."
    else:
        if st.session_state.get("rectification_feedback") and "The code crashed" in st.session_state.rectification_feedback:
            st.session_state.rectification_feedback = ""

    st.divider()
    st.markdown("### ❓ Are you satisfied with these changes?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("👍 Yes, it's perfect!", use_container_width=True):
            st.session_state.patch_stage = "FINAL_APPLY"
            st.rerun()
    with col_n:
        if st.button("👎 No, I want changes", use_container_width=True):
            st.session_state.patch_stage = "RECTIFY"
            st.rerun()
