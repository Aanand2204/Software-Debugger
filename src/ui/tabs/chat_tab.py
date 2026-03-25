import streamlit as st
from src.agents.orchestrator import Orchestrator
from src.ui.components.diagrams import display_content_with_diagrams

def render_chat_tab():
    st.header("💬 Chat with Repository")
    if st.session_state.repo_summary:
        for m_idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                display_content_with_diagrams(message["content"], key_prefix=f"chat_{m_idx}")

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
                with st.chat_message(role): display_content_with_diagrams(content, key_prefix="chat_current")
                st.session_state.messages.append({"role": "assistant", "content": content})
    else:
        st.info("Run an analysis first to enable chat.")
