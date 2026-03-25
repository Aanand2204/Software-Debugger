import streamlit as st
import os
import time
import threading
import queue
from src.agents.orchestrator import Orchestrator

def render_testing_stage():
    st.success("✅ Step 2: Patches applied to temporary clone. Now, let's verify if the code works as expected.")
    
    with st.expander("🔍 View Changes in Clone"):
        for path, res in st.session_state.patch_status.items():
            st.markdown(f"**Path:** `{path}` ({'✅ Syntax OK' if res.get('syntax_ok') else '❌ Syntax Error'})")
            if res['status'] == "Success":
                col_a, col_b = st.columns(2)
                with col_a: st.code(res.get('old_content', ''), language="python")
                with col_b: st.code(res.get('new_content', ''), language="python")
            else:
                st.error(f"Failed to apply patch: {res['status']}")

    with st.expander("📂 Explore Workspace Files"):
        st.info(f"Listing files in `{st.session_state.cloned_repo_path}`")
        all_files = []
        for root, dirs, files in os.walk(st.session_state.cloned_repo_path):
            if any(x in root for x in [".git", "__pycache__", "venv", "node_modules"]): continue
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), st.session_state.cloned_repo_path)
                all_files.append(rel)
        
        st.markdown("\n".join([f"- `{f}`" for f in sorted(all_files)[:50]]))
        if len(all_files) > 50: st.caption(f"... and {len(all_files)-50} more.")

    st.session_state.test_command = st.text_input("Command to execute (e.g., `python app.py`)", value=st.session_state.test_command)
    
    c1, c2 = st.columns([1, 4])
    with c1:
        has_reqs = os.path.exists(os.path.join(st.session_state.cloned_repo_path, "requirements.txt"))
        if has_reqs:
            if st.button("📦 Install Dependencies", use_container_width=True):
                with st.spinner("Installing..."):
                    import sys
                    orchestrator = Orchestrator()
                    pip_cmd = f'"{sys.executable}" -m pip install -r requirements.txt -q'
                    out, ok = orchestrator.execute_command(st.session_state.cloned_repo_path, pip_cmd, timeout=300)
                    if ok: st.success("Installed!")
                    else: st.error(f"Install failed: {out}")
        else:
            st.info("No requirements.txt found.")
    
    with c2:
        if st.button("🚀 Run & View Output", type="primary", use_container_width=True):
            orchestrator = Orchestrator()
            proc = orchestrator.spawn_command(st.session_state.cloned_repo_path, st.session_state.test_command)
            if proc:
                st.session_state.current_process = proc
                st.session_state.exec_output = f"**Working Dir:** `{st.session_state.cloned_repo_path}`\n**Command:** `{st.session_state.test_command}`\n\n"
                st.session_state.exec_start_time = time.time()
                st.session_state.last_exec_returncode = 0
                st.session_state.patch_stage = "EXECUTING"
                
                st.session_state.output_queue = queue.Queue()
                def capture(p, q):
                    try:
                        for line in iter(p.stdout.readline, ''):
                            q.put(line)
                        for line in iter(p.stderr.readline, ''):
                            q.put(line)
                    except: pass
                
                t = threading.Thread(target=capture, args=(proc, st.session_state.output_queue))
                t.daemon = True
                t.start()
                
                st.rerun()
            else:
                st.error("Failed to start process.")
