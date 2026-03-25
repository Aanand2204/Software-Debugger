import streamlit as st
import tempfile
import os
from src.utils.github_utils import GitHubUtils
from src.agents.orchestrator import Orchestrator
from src.database.db_manager import save_analysis_result

def render_analysis_tab(process_button):
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
