import streamlit as st
import time
import queue
from src.agents.orchestrator import Orchestrator

def render_executing_final_stage():
    st.subheader("🖥️ Final Verification (Streaming)")
    
    if st.button("⏹️ Stop Verification", use_container_width=True):
        orchestrator = Orchestrator()
        orchestrator.kill_process(st.session_state.current_process)
        st.session_state.last_exec_output = st.session_state.exec_output
        st.session_state.patch_stage = "COMPLETED"
        st.session_state.current_process = None
        st.rerun()

    st.code(st.session_state.exec_output)
    
    proc = st.session_state.current_process
    if proc:
        elapsed = time.time() - st.session_state.exec_start_time

        while not st.session_state.output_queue.empty():
            try:
                line = st.session_state.output_queue.get_nowait()
                st.session_state.exec_output += line
            except queue.Empty: break

        ret = proc.poll()
        if ret is not None and st.session_state.output_queue.empty():
            st.session_state.last_exec_output = st.session_state.exec_output
            st.session_state.last_exec_returncode = ret
            st.session_state.patch_stage = "COMPLETED"
            st.session_state.current_process = None
            st.rerun()
        else:
            st.caption(f"Executing... {int(elapsed)}s elapsed.")
            time.sleep(0.3)
            st.rerun()
