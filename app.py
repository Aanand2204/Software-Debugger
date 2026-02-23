import streamlit as st
import os
import tempfile
from src.utils.github_utils import GitHubUtils
from src.agents.orchestrator import Orchestrator
from src.config import logger

# Diagnostic: Check for autogen dependencies
try:
    import google.generativeai
    logger.info("google-generativeai is available.")
except ImportError:
    logger.error("google-generativeai NOT FOUND. Debugging session will fail.")

st.set_page_config(page_title="Autonomous Software Debugger", layout="wide")

st.title("🚀 Autonomous Software Debugging Assistant")
st.markdown("""
Upload a GitHub repository URL, and our multi-agent system will:
1. **Analyze** the codebase 📂
2. **Identify** potential bugs 🐞
3. **Suggest** patches 🔧
4. **Generate** PR-ready fixes 🚀
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    repo_url = st.text_input("GitHub Repo URL", placeholder="https://github.com/user/repo")
    process_button = st.button("Analyze Codebase")

if process_button and repo_url:
    with st.status("Processing Repository...", expanded=True) as status:
        # Step 1: Clone Repository
        st.write("Cloning repository...")
        temp_dir = tempfile.mkdtemp()
        success = GitHubUtils.clone_repository(repo_url, temp_dir)
        
        if success:
            st.write("Parsing files...")
            files = GitHubUtils.list_files(temp_dir)
            
            # Create a summary of the codebase (simplified for now)
            repo_summary = ""
            for file_path in files[:10]: # Limit to first 10 files for initial summary
                content = GitHubUtils.read_file_content(file_path)
                if content:
                    repo_summary += f"--- Path: {os.path.relpath(file_path, temp_dir)} ---\n{content[:1000]}\n\n"
            
            # Step 2: Orchestrate Agents
            st.write("Initializing Agents...")
            orchestrator = Orchestrator()
            messages = orchestrator.run_debugging_session(repo_summary)
            
            # Step 3: Display Results
            st.header("Agent Analysis & Suggestions")
            for msg in messages:
                role = msg.get("name", "Agent")
                content = msg.get("content", "")
                
                if role == "System":
                    st.warning(content)
                elif role == "Error":
                    st.error(content)
                else:
                    with st.chat_message(role):
                        st.write(f"**{role}**")
                        st.markdown(content)
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)
        else:
            st.error("Failed to clone repository. Please check the URL.")
            status.update(label="Process Failed", state="error")

else:
    st.info("Please enter a GitHub Repository URL and click 'Analyze Codebase'.")
