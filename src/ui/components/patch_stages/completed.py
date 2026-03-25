import streamlit as st
import os
import time
import threading
import queue
from src.agents.orchestrator import Orchestrator

def render_completed_stage():
    st.success(f"🎉 Changes successfully applied to `{st.session_state.local_repo_path}`!")
    st.markdown("### 🏁 Final Verification")
    st.info("Run one last check in your original folder to ensure everything is integrated correctly.")
    
    with st.expander("🔍 Explore Original Workspace"):
        st.info(f"Listing files in `{st.session_state.local_repo_path}`")
        all_files = []
        for root, dirs, files in os.walk(st.session_state.local_repo_path):
            if any(x in root for x in [".git", "__pycache__", "venv", "node_modules"]): continue
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), st.session_state.local_repo_path)
                all_files.append(rel)
        st.markdown("\n".join([f"- `{f}`" for f in sorted(all_files)[:50]]))

    final_cmd = st.text_input("Final verification command", value=st.session_state.test_command, key="final_verify_cmd")
    
    if st.button("🚀 Run Verification", type="primary", use_container_width=True):
        orchestrator = Orchestrator()
        proc = orchestrator.spawn_command(st.session_state.local_repo_path, final_cmd)
        if proc:
            st.session_state.current_process = proc
            st.session_state.exec_output = f"**Working Dir:** `{st.session_state.local_repo_path}`\n**Command:** `{final_cmd}`\n\n"
            st.session_state.exec_start_time = time.time()
            st.session_state.last_exec_returncode = 0
            st.session_state.patch_stage = "EXECUTING_FINAL"
            
            st.session_state.output_queue = queue.Queue()
            def capture_final(p, q):
                try:
                    for line in iter(p.stdout.readline, ''):
                        q.put(line)
                    for line in iter(p.stderr.readline, ''):
                        q.put(line)
                except: pass
            
            t = threading.Thread(target=capture_final, args=(proc, st.session_state.output_queue))
            t.daemon = True
            t.start()
            
            st.rerun()
        else:
            st.error("Failed to start process.")

    if st.session_state.last_exec_output:
        st.divider()
        st.subheader("🖥️ Last Verification Output")
        st.code(st.session_state.last_exec_output)
        
        if not st.session_state.get("is_finally_done"):
            st.subheader("❓ Final Verdict: Are you satisfied?")
            st.markdown("If everything looks good, we can finish. Otherwise, we can keep improving!")
            
            col_fin, col_more = st.columns(2)
            
            with col_fin:
                if st.button("🏁 Yes, Mission Accomplished! 🎉", type="primary", use_container_width=True):
                    st.session_state.is_finally_done = True
                    st.balloons()
                    st.rerun()
            
            with col_more:
                if st.button("🔄 No, I need more improvements", use_container_width=True):
                    st.session_state.needs_more_work = True
                    st.rerun()

    if st.session_state.get("is_finally_done"):
        st.success("### 🎊 Congratulations! Your codebase is now better, faster, and bug-free.")
        st.info("You can start a new session by modifying the repository path in the sidebar.")
        st.divider()
        st.markdown("### 📈 Analysis Summary (Updated)")
        st.info("Debugging Session Finalized. Great job!")

    if st.session_state.get("needs_more_work") and not st.session_state.get("is_finally_done"):
        st.divider()
        st.markdown("### 📝 Provide Feedback for the Next Round")
        feedback = st.text_area("What else should be fixed or improved?", placeholder="e.g., 'Optimize the database query', 'Fix the CSS alignment'...")
        
        if st.button("🚀 Re-Analyze with Feedback", type="primary", use_container_width=True):
            st.session_state.initial_analysis_requested = True
            st.session_state.analysis_results = [] 
            st.session_state.patch_stage = "SUGGESTED"
            st.session_state.needs_more_work = False
            st.session_state.is_finally_done = False
            st.session_state.last_exec_output = None
            st.rerun()
