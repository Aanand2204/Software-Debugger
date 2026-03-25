import streamlit as st
import os

DIAG_OPTIONS = ["Flowchart", "Master Flow Chart", "System Design", "Use Case Diagram", "Class Diagram", "Sequence Diagram", "Activity Diagram", "State Diagram", "ER Diagram"]

def initialize_session_state():
    """Initializes all required Streamlit session state variables."""
    # State for Repository Selection
    if "repo_url" not in st.session_state:
        st.session_state.repo_url = ""
    if "local_repo_path" not in st.session_state:
        st.session_state.local_repo_path = ""
        
    # State for Chat & Analysis
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "repo_summary" not in st.session_state:
        st.session_state.repo_summary = None
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = []
    if "initial_analysis_requested" not in st.session_state:
        st.session_state.initial_analysis_requested = False
        
    # State for Workspace & Patching
    if "cloned_repo_path" not in st.session_state:
        st.session_state.cloned_repo_path = None
    if "workspace_files" not in st.session_state:
        st.session_state.workspace_files = []
    if "pending_patches" not in st.session_state:
        st.session_state.pending_patches = []
    if "patch_status" not in st.session_state:
        st.session_state.patch_status = {}
    if "patch_stage" not in st.session_state:
        st.session_state.patch_stage = "SUGGESTED"
    if "patches_reviewed" not in st.session_state:
        st.session_state.patches_reviewed = False
        
    # State for Code Execution Verification
    if "current_process" not in st.session_state:
        st.session_state.current_process = None
    if "exec_output" not in st.session_state:
        st.session_state.exec_output = ""
    if "last_exec_output" not in st.session_state:
        st.session_state.last_exec_output = None
    if "exec_start_time" not in st.session_state:
        st.session_state.exec_start_time = 0
    if "test_command" not in st.session_state:
        st.session_state.test_command = ""
        
    # State for Refinement Cycle
    if "rectify_mode" not in st.session_state:
        st.session_state.rectify_mode = False
    if "rectification_feedback" not in st.session_state:
        st.session_state.rectification_feedback = ""
    if "is_finally_done" not in st.session_state:
        st.session_state.is_finally_done = False
    if "needs_more_work" not in st.session_state:
        st.session_state.needs_more_work = False

    # State for Diagrams
    if "diag_selection" not in st.session_state:
        st.session_state.diag_selection = []
    elif not isinstance(st.session_state.diag_selection, list):
        st.session_state.diag_selection = []
    else:
        st.session_state.diag_selection = [opt for opt in st.session_state.diag_selection if opt in DIAG_OPTIONS]
