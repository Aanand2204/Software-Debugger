import streamlit as st
import os
import tempfile
import base64
import zlib
import re
import time
import threading
import queue
from src.utils.github_utils import GitHubUtils
from src.agents.orchestrator import Orchestrator
from src.config import logger
from src.database.db_manager import init_firebase, save_analysis_result, get_analysis_history
import inspect
import src.agents.orchestrator as orch_mod

# --- DIAGNOSTIC ---
orch_file = inspect.getfile(orch_mod.Orchestrator)
# ------------------

# Diagnostic: Check for autogen dependencies
try:
    import google.generativeai
    logger.info("google-generativeai is available.")
except ImportError:
    logger.error("google-generativeai NOT FOUND. Debugging session will fail.")

# Initialize Firebase
db = init_firebase()

st.set_page_config(page_title="Autonomous Software Debugger", layout="wide")

st.title("🚀 Autonomous Software Debugger")
st.markdown("**Welcome to the Codebase Analyzer!** 📂")
st.markdown("""
Upload a GitHub repository URL, and our multi-agent system will:
1. **Analyze** the codebase 📂
2. **Identify** potential bugs 🐞
3. **Suggest** patches 🔧
4. **Generate** PR-ready fixes 🚀
""")

# Sidebar for configuration
def normalize_path():
    if st.session_state.local_repo_path:
        cleaned = st.session_state.local_repo_path.strip().strip('"').strip("'")
        st.session_state.local_repo_path = os.path.normpath(cleaned)

with st.sidebar:
    st.header("Configuration")
    st.text_input("GitHub Repo URL", key="repo_url", placeholder="https://github.com/user/repo")
    st.text_input("Local Repo Path", key="local_repo_path", placeholder="C:/path/to/repo", on_change=normalize_path)
    process_button = st.button("Analyze Codebase")
    reset_button = st.button("Reset Session")
    st.sidebar.divider()
    st.sidebar.caption(f"🔧 Debug: Orchestrator at `{orch_file}`")

if reset_button:
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

# Function to render diagrams
def render_svg(code, name="diagram"):
    """Renders Raw SVG code by injecting it directly via st.components (Most Robust)."""
    try:
        clean_svg = code.strip()
        # Remove potential surrounding backticks
        if "```" in clean_svg:
            match = re.search(r"```(?:svg)?\n?(.*?)\n?```", clean_svg, re.DOTALL)
            if match: clean_svg = match.group(1).strip()
        
        # Ensure it starts with <svg
        if not clean_svg.startswith("<svg"):
            idx = clean_svg.find("<svg")
            if idx != -1: clean_svg = clean_svg[idx:]
            else: clean_svg = f'<svg viewBox="0 0 800 600" xmlns="http://www.xml.org/2000/svg">{clean_svg}</svg>'
        
        # Cleanup trailing junk
        last_tag = clean_svg.rfind("</svg>")
        if last_tag != -1: clean_svg = clean_svg[:last_tag+6]

        st.components.v1.html(f"""
            <div style="background: #2d2d2d; border-radius: 8px; padding: 10px; display: flex; justify-content: center; align-items: center; overflow: auto;">
                {clean_svg}
            </div>
            <style>
                svg {{ max-width: 100%; height: auto; display: block; margin: auto; }}
                body {{ margin: 0; background: #2d2d2d; }}
            </style>
        """, height=500, scrolling=True)
        
        st.download_button(label=f"📥 Download {name}.svg", data=clean_svg, file_name=f"{name}.svg", mime="image/svg+xml")
    except Exception as e:
        st.error(f"Failed to render visualization: {e}")
        st.code(code, language="xml")

def render_diagram(code, name="diagram", lang="mermaid"):
    """Fallback for legacy content."""
    if lang == "svg": render_svg(code, name)
    else:
        st.info(f"Rendering {lang} is restricted on this host. Below is the source:")
        st.code(code, language=lang)

def display_content_with_diagrams(content, headers=None):
    """Helper to detect and display diagrams within a message."""
    svg_blocks = re.findall(r"```svg\n?(.*?)\n?```", content, re.DOTALL)
    mermaid_blocks = re.findall(r"```mermaid\n?(.*?)\n?```", content, re.DOTALL)
    dot_blocks = re.findall(r"```(?:dot|graphviz)\n?(.*?)\n?```", content, re.DOTALL)
    
    # Emergency Fallback: Raw tags (More robust regex)
    if not any([svg_blocks, mermaid_blocks, dot_blocks]):
        svg_blocks = re.findall(r"(<svg\b[^>]*>.*?</svg>)", content, re.DOTALL | re.IGNORECASE)
    
    if svg_blocks or mermaid_blocks or dot_blocks:
        if headers is None:
            headers = re.findall(r"###?\s+(.*?)\n", content)
        
        block_idx = 0
        for block in svg_blocks:
            label = headers[block_idx] if block_idx < len(headers) else f"Visualization {block_idx+1}"
            st.subheader(f"🖼️ {label}")
            render_svg(block, name=label)
            block_idx += 1
            
        for block in mermaid_blocks:
            label = headers[block_idx] if block_idx < len(headers) else f"Mermaid Code {block_idx+1}"
            render_diagram(block, name=label, lang="mermaid")
            block_idx += 1
            
        for block in dot_blocks:
            label = headers[block_idx] if block_idx < len(headers) else f"DOT Code {block_idx+1}"
            render_diagram(block, name=label, lang="dot")
            block_idx += 1
    else:
        st.markdown(content)

# Initialize session state for persistent data
if "messages" not in st.session_state:
    st.session_state.messages = []
if "repo_summary" not in st.session_state:
    st.session_state.repo_summary = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []
if "cloned_repo_path" not in st.session_state:
    st.session_state.cloned_repo_path = None
if "pending_patches" not in st.session_state:
    st.session_state.pending_patches = []
if "patch_status" not in st.session_state:
    st.session_state.patch_status = {}
if "rectify_mode" not in st.session_state:
    st.session_state.rectify_mode = False
if "rectification_feedback" not in st.session_state:
    st.session_state.rectification_feedback = ""
if "patches_reviewed" not in st.session_state:
    st.session_state.patches_reviewed = False
if "initial_analysis_requested" not in st.session_state:
    st.session_state.initial_analysis_requested = False
if "patch_stage" not in st.session_state:
    st.session_state.patch_stage = "SUGGESTED"
if "current_process" not in st.session_state:
    st.session_state.current_process = None
if "exec_output" not in st.session_state:
    st.session_state.exec_output = ""
if "exec_start_time" not in st.session_state:
    st.session_state.exec_start_time = 0
if "is_finally_done" not in st.session_state:
    st.session_state.is_finally_done = False
if "needs_more_work" not in st.session_state:
    st.session_state.needs_more_work = False

DIAG_OPTIONS = ["Flowchart", "Master Flow Chart", "System Design", "Use Case Diagram", "Class Diagram", "Sequence Diagram", "Activity Diagram", "State Diagram", "ER Diagram"]

if "diag_selection" not in st.session_state:
    st.session_state.diag_selection = []
elif not isinstance(st.session_state.diag_selection, list):
    st.session_state.diag_selection = []
else:
    st.session_state.diag_selection = [opt for opt in st.session_state.diag_selection if opt in DIAG_OPTIONS]
tab1, tab_patch, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "🛡️ Patch & Test", "💬 Chat", "🎨 Visualizations", "📜 History"])

with tab1:
    st.header("📊 Repository Analysis")
    r_url = st.session_state.get("repo_url")
    l_path = st.session_state.get("local_repo_path")
    
    # ONLY run analysis if button is pressed OR if results are missing BUT requested
    should_analyze = process_button or (st.session_state.initial_analysis_requested and not st.session_state.analysis_results)

    if should_analyze:
        with st.status("Processing Repository...", expanded=True) as status:
            temp_dir = tempfile.mkdtemp()
            success = False
            
            if r_url:
                st.write("Cloning remote repository...")
                if GitHubUtils.clone_repository(r_url, temp_dir):
                    success = True
                else:
                    st.error("Failed to clone remote repository.")
            elif l_path:
                st.write(f"Copying local repository from {l_path}...")
                try:
                    import shutil
                    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    if os.path.isfile(l_path):
                        # Handle single file repository
                        shutil.copy2(l_path, os.path.join(temp_dir, os.path.basename(l_path)))
                        st.info("Single file detected. Processing as a one-file repository.")
                        success = True
                    elif os.path.isdir(l_path):
                        # Expanded ignore list to speed up copying
                        ignore_list = shutil.ignore_patterns(
                            '.git', 'node_modules', '__pycache__', 'softenv', 
                            '.venv', 'venv', 'env', '.idea', '.vscode', 
                            'dist', 'build', '.pytest_cache', '.next', '.nuxt', 
                            'vendor', 'target', '.terraform', '.serverless',
                            '*.pyc', '*.pyo', '*.pyd', '.DS_Store'
                        )
                        shutil.copytree(l_path, temp_dir, dirs_exist_ok=True, ignore=ignore_list)
                        success = True
                    else:
                        st.error(f"Path not found: {l_path}")
                except Exception as e:
                    st.error(f"Failed to copy local repository: {e}")

            if success:
                st.session_state.cloned_repo_path = temp_dir
                st.write("Parsing files...")
                files = GitHubUtils.list_files(temp_dir)
                repo_summary = ""
                # Use a larger slice if local to be more comprehensive
                max_summary_files = 20 if l_path else 10
                workspace_files = [os.path.relpath(fp, temp_dir) for fp in files]
                st.session_state.workspace_files = workspace_files
                
                for file_path in files[:max_summary_files]:
                    content = GitHubUtils.read_file_content(file_path)
                    if content:
                        repo_summary += f"--- Path: {os.path.relpath(file_path, temp_dir)} ---\n{content[:2000]}\n\n"
                st.session_state.repo_summary = repo_summary
                
                st.write("Initializing Agents...")
                orchestrator = Orchestrator()
                do_gen = len(st.session_state.diag_selection) > 0
                st.session_state.analysis_results = orchestrator.run_debugging_session(
                    repo_summary, 
                    generate_diagrams=do_gen, 
                    diagram_types=st.session_state.diag_selection,
                    workspace_files=workspace_files
                )
                
                # Extract pending patches
                patch_msg = next((m for m in st.session_state.analysis_results if m.get("name") == "Patch_Generator"), None)
                if patch_msg:
                    st.session_state.pending_patches = orchestrator.parse_patches(patch_msg["content"])
                    # Reset workflow state ONLY for new results
                    st.session_state.patch_stage = "SUGGESTED"
                    st.session_state.patch_status = {}
                    st.session_state.last_exec_output = None
                    st.session_state.test_command = ""
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                if st.session_state.analysis_results and not any(msg.get("name") in ["System", "Error"] for msg in st.session_state.analysis_results):
                    save_analysis_result(r_url or l_path, st.session_state.analysis_results)
            else:
                status.update(label="Process Failed", state="error")

    if st.session_state.analysis_results:
        for msg in st.session_state.analysis_results:
            role = msg.get("name", "Agent")
            content = msg.get("content", "")
            if role == "System": st.warning(content)
            elif role == "Error": st.error(content)
            elif role == "Diagram_Generator": pass
            else:
                with st.chat_message(role): st.markdown(content)
                
    else:
        st.info("Enter a GitHub URL or Local Path in the sidebar and click 'Analyze Codebase' to start.")

with tab_patch:
    st.header("🛡️ Patch & Test")
    if st.session_state.get("repo_url"):
        st.warning("⚠️ The Patch & Test workflow is disabled for remote GitHub repositories. Please analyze a local repository to use this feature.")
    elif st.session_state.analysis_results:
        # --- NEW: Safe Patching Workflow (Sequential) ---
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
            if st.session_state.patch_stage == "SUGGESTED":
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
                                # Do NOT advance the stage
                            else:
                                st.session_state.test_command = orchestrator.suggest_entry_point(st.session_state.cloned_repo_path)
                                st.session_state.patch_stage = "TESTING"
                                st.rerun()
                    else: st.warning("No cloned repository found. Run analysis first.")

            # STAGE 2: TESTING (Applied to clone, ready to execute)
            elif st.session_state.patch_stage == "TESTING":
                st.success("✅ Step 2: Patches applied to temporary clone. Now, let's verify if the code works as expected.")
                
                # Show Diff
                with st.expander("🔍 View Changes in Clone"):
                    for path, res in st.session_state.patch_status.items():
                        st.markdown(f"**Path:** `{path}` ({'✅ Syntax OK' if res.get('syntax_ok') else '❌ Syntax Error'})")
                        if res['status'] == "Success":
                            col_a, col_b = st.columns(2)
                            with col_a: st.code(res.get('old_content', ''), language="python")
                            with col_b: st.code(res.get('new_content', ''), language="python")
                        else:
                            st.error(f"Failed to apply patch: {res['status']}")

                # Workspace Explorer
                with st.expander("📂 Explore Workspace Files"):
                    st.info(f"Listing files in `{st.session_state.cloned_repo_path}`")
                    all_files = []
                    for root, dirs, files in os.walk(st.session_state.cloned_repo_path):
                        # Filter out common junk
                        if any(x in root for x in [".git", "__pycache__", "venv", "node_modules"]): continue
                        for f in files:
                            rel = os.path.relpath(os.path.join(root, f), st.session_state.cloned_repo_path)
                            all_files.append(rel)
                    
                    st.markdown("\n".join([f"- `{f}`" for f in sorted(all_files)[:50]]))
                    if len(all_files) > 50: st.caption(f"... and {len(all_files)-50} more.")

                # Execution Input
                st.session_state.test_command = st.text_input("Command to execute (e.g., `python app.py`)", value=st.session_state.test_command)
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    has_reqs = os.path.exists(os.path.join(st.session_state.cloned_repo_path, "requirements.txt"))
                    if has_reqs:
                        if st.button("📦 Install Dependencies", use_container_width=True):
                            with st.spinner("Installing..."):
                                import sys
                                orchestrator = Orchestrator()
                                # Use sys.executable to ensure it installs into the current environment
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
                            
                            # Start output capture thread
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

            # STAGE: EXECUTING (Streaming Output)
            elif st.session_state.patch_stage == "EXECUTING":
                st.subheader("🖥️ Execution Output (Streaming)")
                
                # Satisfaction Buttons (Clickable anytime!)
                col_s, col_r = st.columns(2)
                with col_s:
                    if st.button("👍 Perfect! I'm Satisfied", type="primary", use_container_width=True):
                        orchestrator = Orchestrator()
                        orchestrator.kill_process(st.session_state.current_process)
                        st.session_state.last_exec_output = st.session_state.exec_output
                        st.session_state.patch_stage = "FINAL_APPLY"
                        st.session_state.current_process = None
                        st.rerun()
                with col_r:
                    if st.button("👎 Stop & Rectify", use_container_width=True):
                        orchestrator = Orchestrator()
                        orchestrator.kill_process(st.session_state.current_process)
                        st.session_state.last_exec_output = st.session_state.exec_output
                        st.session_state.patch_stage = "RECTIFY"
                        st.session_state.current_process = None
                        st.rerun()

                # Display Console
                st.code(st.session_state.exec_output)
                
                proc = st.session_state.current_process
                if proc:
                    elapsed = time.time() - st.session_state.exec_start_time

                    # Drain queue
                    new_data = False
                    while not st.session_state.output_queue.empty():
                        try:
                            line = st.session_state.output_queue.get_nowait()
                            st.session_state.exec_output += line
                            new_data = True
                        except queue.Empty: break

                    ret = proc.poll()
                    if ret is not None and st.session_state.output_queue.empty():
                        st.session_state.last_exec_output = st.session_state.exec_output
                        st.session_state.last_exec_returncode = ret
                        st.session_state.patch_stage = "VERIFYING"
                        st.session_state.current_process = None
                        st.rerun()
                    else:
                        st.caption(f"Executing... {int(elapsed)}s elapsed.")
                        time.sleep(0.3) # Smoother loop
                        st.rerun()

            # STAGE 3: VERIFYING (Static Output)
            elif st.session_state.patch_stage == "VERIFYING":
                st.subheader("🖥️ Execution Output")
                if st.session_state.last_exec_output:
                    st.code(st.session_state.last_exec_output)
                else:
                    st.warning("No execution output captured.")
                
                ret_code = st.session_state.get("last_exec_returncode", 0)
                if ret_code != 0:
                    st.error(f"❌ Execution failed with exit code {ret_code}. Please review the errors.")
                    # Auto-populate rectification feedback
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

            # STAGE 4: FINAL_APPLY (Apply to workspace)
            elif st.session_state.patch_stage == "FINAL_APPLY":
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
                                    
                                    # Strip leading slashes to ensure joining works on Windows
                                    clean_rel_path = rel_path.lstrip("/\\")
                                    src = os.path.join(st.session_state.cloned_repo_path, clean_rel_path)
                                    dst = os.path.join(st.session_state.local_repo_path, clean_rel_path) 
                                    
                                    if os.path.exists(src):
                                        # Ensure destination parent directory exists
                                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                                        shutil.copy2(src, dst)
                                        st.write(f"✅ Applied: `{clean_rel_path}`")
                                        success_count += 1
                                    else:
                                        st.error(f"❌ Patch failed for {clean_rel_path}: Source not found at {src}")

                                if success_count > 0:
                                    st.balloons()
                                    st.session_state.patch_stage = "COMPLETED"
                                    st.session_state.last_exec_output = None # Clear old clone output
                                    st.rerun()
                                else:
                                    st.error("No compatible patches were successfully applied.")
                            except Exception as e:
                                st.error(f"Commit failed: {e}")
                else:
                    st.info("Direct workspace commit is only available for Local Repo Paths.")

            # STAGE 6: COMPLETED (Final Verification & Repeat Loop)
            elif st.session_state.patch_stage == "COMPLETED":
                st.success(f"🎉 Changes successfully applied to `{st.session_state.local_repo_path}`!")
                st.markdown("### 🏁 Final Verification")
                st.info("Run one last check in your original folder to ensure everything is integrated correctly.")
                
                # Workspace Explorer (Original)
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
                        
                        # Start output capture thread
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

                # --- Moved Satisfaction Check & More Work Logic to COMPLETED ---
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

                # Path A: Celebration
                if st.session_state.get("is_finally_done"):
                    st.success("### 🎊 Congratulations! Your codebase is now better, faster, and bug-free.")
                    st.info("You can start a new session by modifying the repository path in the sidebar.")
                    st.divider()
                    st.markdown("### 📈 Analysis Summary (Updated)")
                    st.info("Debugging Session Finalized. Great job!")

                # Path B: More Work (Feedback Loop)
                if st.session_state.get("needs_more_work") and not st.session_state.get("is_finally_done"):
                    st.divider()
                    st.markdown("### 📝 Provide Feedback for the Next Round")
                    feedback = st.text_area("What else should be fixed or improved?", placeholder="e.g., 'Optimize the database query', 'Fix the CSS alignment'...")
                    
                    if st.button("🚀 Re-Analyze with Feedback", type="primary", use_container_width=True):
                        # The key is to clear analysis results so the 'should_analyze' logic triggers
                        st.session_state.initial_analysis_requested = True
                        st.session_state.analysis_results = [] 
                        st.session_state.patch_stage = "SUGGESTED"
                        st.session_state.needs_more_work = False # Reset for next cycle
                        st.session_state.is_finally_done = False
                        st.session_state.last_exec_output = None
                        st.rerun()

            # STAGE: EXECUTING_FINAL (Streaming Output for Original Folder)
            elif st.session_state.patch_stage == "EXECUTING_FINAL":
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

                    # Drain queue
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

            # STAGE 5: RECTIFY (Ask for suggestions)
            elif st.session_state.patch_stage == "RECTIFY":
                st.warning("⚠️ Let's fix it! Please provide your suggestions below.")
                feedback = st.text_area("What should be corrected?", value=st.session_state.rectification_feedback)
                if st.button("🔥 Re-generate Patches", type="primary", use_container_width=True):
                    with st.status("Re-analyzing with feedback...", expanded=True) as status:
                        orchestrator = Orchestrator()
                        prompt = f"Repository Summary:\n{st.session_state.repo_summary}\n\nUSER FEEDBACK ON PREVIOUS PATCHES: {feedback}\n\nTask: Re-evaluate and suggest better patches."
                        msg, is_err = orchestrator._run_step_with_rotation(orchestrator.factory.create_bug_detection_agent, orchestrator.factory.create_user_proxy(), prompt, "Bug Re-detection")
                        if not is_err:
                            file_list_str = "\n".join([f"- {f}" for f in st.session_state.workspace_files]) if st.session_state.get("workspace_files") else "None provided."
                            patch_prompt = f"Previous Analysis:\n{msg}\n\nWorkspace File List (Available modules):\n{file_list_str}\n\nFeedback: {feedback}\n\nTask: Generate revised code patches."
                            p_msg, p_is_err = orchestrator.run_patch_generation_cycle(patch_prompt, st.session_state.get("workspace_files"), orchestrator.factory.create_user_proxy())
                            
                            if not p_is_err:
                                # Update analysis results with new patches
                                for m in st.session_state.analysis_results:
                                    if m.get("name") == "Patch_Generator": 
                                        m["content"] = p_msg
                                
                                st.session_state.pending_patches = orchestrator.parse_patches(p_msg)
                                
                                # Automatically apply new patches to the existing clone to jump straight to testing
                                if st.session_state.cloned_repo_path:
                                    results = orchestrator.apply_patches_to_dir(st.session_state.pending_patches, st.session_state.cloned_repo_path, st.session_state.get("workspace_files"))
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
        else:
            st.info("No patches were suggested in the current analysis.")

    else:
        st.info("Run an analysis first to unlock the patching workflow.")

with tab2:
    st.header("💬 Chat with Repository")
    if st.session_state.repo_summary:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                display_content_with_diagrams(message["content"])

        if prompt := st.chat_input("Ask something..."):
            with st.chat_message("user"): st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            orchestrator = Orchestrator()
            with st.spinner("Thinking..."):
                response_msg = orchestrator.chat_with_repo(st.session_state.repo_summary, prompt, st.session_state.messages)
            
            role = response_msg.get("name", "Agent")
            content = response_msg.get("content", "")
            if role == "Error": st.error(content)
            else:
                with st.chat_message(role): display_content_with_diagrams(content)
                st.session_state.messages.append({"role": "assistant", "content": content})
    else:
        st.info("Run an analysis first to enable chat.")

with tab3:
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
        for msg in st.session_state.analysis_results:
            if msg.get("name") == "Diagram_Generator":
                found_diagrams = True
                display_content_with_diagrams(msg.get("content", ""))
    if not found_diagrams:
        st.info("No diagrams available.")

with tab4:
    st.header("Recent Analysis History")
    history = get_analysis_history()
    if history:
        for item in history:
            repo_url = item.get('repo_url', 'Unknown')
            parts = repo_url.rstrip('/').split('/')
            repo_display = "/".join(parts[-2:]) if len(parts) >= 2 else repo_url
            with st.expander(f"📁 {repo_display}"):
                st.caption(f"Analyzed on: {item.get('timestamp')}")
                for msg in item['results']:
                    role = msg.get('name', 'Agent')
                    content = msg.get('content', '')
                    if role == "Diagram_Generator":
                        with st.expander("🖼️ View Diagrams", expanded=False):
                            display_content_with_diagrams(content)
                    else: st.markdown(f"**{role}**: {content}")
    else: st.info("No history found.")
