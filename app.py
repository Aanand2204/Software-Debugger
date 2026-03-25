import streamlit as st
from src.config import logger
from src.database.db_manager import init_firebase
from src.ui.state import initialize_session_state
from src.ui.components.sidebar import render_sidebar
from src.ui.tabs.analysis_tab import render_analysis_tab
from src.ui.tabs.patch_tab import render_patch_tab
from src.ui.tabs.chat_tab import render_chat_tab
from src.ui.tabs.visualizations_tab import render_visualizations_tab
from src.ui.tabs.history_tab import render_history_tab

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
Provide a GitHub repository URL or Local Directory path, and our multi-agent AI system will:
1. **Analyze** the codebase and architecture 📂
2. **Identify** potential bugs and vulnerabilities 🐞
3. **Generate** dynamic architectural visualizations 🎨
4. **Suggest & Test** patches in a secure sandbox 🛡️
""")

initialize_session_state()

process_button = render_sidebar()

tab1, tab_patch, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "🛡️ Patch & Test", "💬 Chat", "🎨 Visualizations", "📜 History"])

with tab1:
    render_analysis_tab(process_button)
    
with tab_patch:
    render_patch_tab()
    
with tab2:
    render_chat_tab()
    
with tab3:
    render_visualizations_tab()
    
with tab4:
    render_history_tab()
