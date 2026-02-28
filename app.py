import streamlit as st
import os
import tempfile
from src.utils.github_utils import GitHubUtils
from src.agents.orchestrator import Orchestrator
from src.config import logger
from src.database.db_manager import init_firebase, save_analysis_result, get_analysis_history

# Diagnostic: Check for autogen dependencies
try:
    import google.generativeai
    logger.info("google-generativeai is available.")
except ImportError:
    logger.error("google-generativeai NOT FOUND. Debugging session will fail.")

# Initialize Firebase
db = init_firebase()

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

# Function to render Mermaid diagrams
def render_mermaid(code):
    """Simple wrapper to render Mermaid code in Streamlit with dark mode support."""
    components_html = f"""
    <div class="mermaid">
        {code}
    </div>
    <style>
        .mermaid svg {{
            font-family: 'Inter', sans-serif !important;
        }}
        /* Ensure arrows and lines are visible in dark backgrounds */
        .mermaid .edgePath .path {{
            stroke: #ffffff !important;
            stroke-width: 2px !important;
        }}
        .mermaid .marker {{
            fill: #ffffff !important;
            stroke: #ffffff !important;
        }}
    </style>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.5/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true, 
            theme: 'dark',
            themeVariables: {{
                primaryColor: '#BB86FC',
                primaryTextColor: '#fff',
                primaryBorderColor: '#BB86FC',
                lineColor: '#ffffff',
                secondaryColor: '#03DAC6',
                tertiaryColor: '#3700B3'
            }}
        }});
    </script>
    """
    st.components.v1.html(components_html, height=500, scrolling=True)

# Initialize session state for persistent data
if "messages" not in st.session_state:
    st.session_state.messages = []
if "repo_summary" not in st.session_state:
    st.session_state.repo_summary = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# List of valid diagram types
DIAG_OPTIONS = ["Flowchart", "System Design", "Use Case Diagram", "Class Diagram", "Sequence Diagram", "Activity Diagram", "State Diagram", "ER Diagram"]

if "diag_selection" not in st.session_state:
    st.session_state.diag_selection = ["Flowchart", "System Design"]
elif not isinstance(st.session_state.diag_selection, list):
    # Fix for any lingering non-list values from previous versions
    st.session_state.diag_selection = ["Flowchart", "System Design"]
else:
    # Filter out any non-existent options
    st.session_state.diag_selection = [opt for opt in st.session_state.diag_selection if opt in DIAG_OPTIONS]

# Always show tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "💬 Chat", "🎨 Visualizations", "📜 History"])

with tab1:
    st.header("📊 Repository Analysis")
    if process_button and repo_url:
        with st.status("Processing Repository...", expanded=True) as status:
            # Step 1: Clone Repository
            st.write("Cloning repository...")
            import tempfile
            temp_dir = tempfile.mkdtemp()
            success = GitHubUtils.clone_repository(repo_url, temp_dir)
            
            if success:
                st.write("Parsing files...")
                files = GitHubUtils.list_files(temp_dir)
                repo_summary = ""
                for file_path in files[:10]:
                    content = GitHubUtils.read_file_content(file_path)
                    if content:
                        repo_summary += f"--- Path: {os.path.relpath(file_path, temp_dir)} ---\n{content[:1000]}\n\n"
                
                st.session_state.repo_summary = repo_summary
                
                st.write("Initializing Agents...")
                orchestrator = Orchestrator()
                
                # Check multi-select
                do_gen = len(st.session_state.diag_selection) > 0
                st.session_state.analysis_results = orchestrator.run_debugging_session(
                    repo_summary, 
                    generate_diagrams=do_gen, 
                    diagram_types=st.session_state.diag_selection
                )
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                
                # Save results to Firebase
                if st.session_state.analysis_results and not any(msg.get("name") in ["System", "Error"] for msg in st.session_state.analysis_results):
                    save_analysis_result(repo_url, st.session_state.analysis_results)
            else:
                st.error("Failed to clone repository. Please check the URL.")
                status.update(label="Process Failed", state="error")

    # Display Suggestions
    if st.session_state.analysis_results:
        for msg in st.session_state.analysis_results:
            role = msg.get("name", "Agent")
            content = msg.get("content", "")
            if role == "System": st.warning(content)
            elif role == "Error": st.error(content)
            elif role == "Diagram_Generator": pass # Show in Visualizations tab
            else:
                with st.chat_message(role):
                    st.markdown(content)
    else:
        st.info("Enter a GitHub URL in the sidebar and click 'Analyze Codebase' to start.")

with tab2:
    st.header("💬 Chat with Repository")
    if st.session_state.repo_summary:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask something..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            orchestrator = Orchestrator()
            with st.spinner("Thinking..."):
                response_msg = orchestrator.chat_with_repo(st.session_state.repo_summary, prompt, st.session_state.messages)
            
            role = response_msg.get("name", "Agent")
            content = response_msg.get("content", "")
            if role == "Error": st.error(content)
            else:
                with st.chat_message(role): st.markdown(content)
                st.session_state.messages.append({"role": "assistant", "content": content})
    else:
        st.info("Run an analysis first to enable chat.")

with tab3:
    st.header("🎨 Visualizations & Diagrams")
    st.session_state.diag_selection = st.multiselect(
        "Select diagram types to generate:",
        DIAG_OPTIONS,
        default=st.session_state.diag_selection,
        help="Select multiple diagrams. These will be generated using the LLM."
    )
    
    if st.button("🎨 Generate Selected Diagrams"):
        if st.session_state.repo_summary:
            if st.session_state.diag_selection:
                with st.spinner("Generating diagrams... (this may take a minute)"):
                    orchestrator = Orchestrator()
                    new_diag_msg = orchestrator.generate_diagrams_only(st.session_state.repo_summary, st.session_state.diag_selection)
                    
                    if new_diag_msg.get("name") != "Error":
                        # Update analysis_results: remove old Diagram_Generator message if it exists
                        st.session_state.analysis_results = [msg for msg in st.session_state.analysis_results if msg.get("name") != "Diagram_Generator"]
                        st.session_state.analysis_results.append(new_diag_msg)
                        
                        # Sync with Firebase
                        save_analysis_result(repo_url, st.session_state.analysis_results)
                        st.success("Diagrams updated and saved successfully!")
                    else:
                        st.error(new_diag_msg.get("content"))
            else:
                st.warning("Please select at least one diagram type.")
        else:
            st.warning("Please run a full 'Analyze Codebase' from the sidebar first to provide repository context.")

    st.divider()
    found_diagrams = False
    if st.session_state.analysis_results:
        for msg in st.session_state.analysis_results:
            if msg.get("name") == "Diagram_Generator":
                found_diagrams = True
                content = msg.get("content", "")
                import re
                mermaid_blocks = re.findall(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
                if mermaid_blocks:
                    # Attempt to find headers before mermaid blocks to label them correctly
                    headers = re.findall(r"###?\s+(.*?)\n```mermaid", content)
                    for idx, block in enumerate(mermaid_blocks):
                        label = headers[idx] if idx < len(headers) else f"Diagram {idx+1}"
                        st.subheader(f"🖼️ {label}")
                        render_mermaid(block)
                else:
                    st.markdown(content)
    
    if not found_diagrams:
        st.info("No diagrams available. Ensure 'Architecture & Flow Diagrams' is selected above, then run an analysis.")

    with tab4:
        st.header("Recent Analysis History")
        history = get_analysis_history()
        if history:
            for item in history:
                repo_url = item.get('repo_url', 'Unknown')
                # Extract 'owner/repo' from 'https://github.com/owner/repo'
                parts = repo_url.rstrip('/').split('/')
                repo_display = "/".join(parts[-2:]) if len(parts) >= 2 else repo_url
                with st.expander(f"📁 {repo_display}"):
                    st.caption(f"Full URL: {repo_url}")
                    st.caption(f"Analyzed on: {item.get('timestamp')}")
                    for msg in item['results']:
                        role = msg.get('name', 'Agent')
                        content = msg.get('content', '')
                        if role == "Diagram_Generator":
                            with st.expander("🖼️ View Diagrams", expanded=False):
                                import re
                                mermaid_blocks = re.findall(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
                                if mermaid_blocks:
                                    headers = re.findall(r"###?\s+(.*?)\n```mermaid", content)
                                    for idx, block in enumerate(mermaid_blocks):
                                        label = headers[idx] if idx < len(headers) else f"Diagram {idx+1}"
                                        st.subheader(f"🖼️ {label}")
                                        render_mermaid(block)
                                else:
                                    st.markdown(content)
                        else:
                            st.markdown(f"**{role}**: {content}")
        else:
            st.info("No history found or Firebase not connected.")
