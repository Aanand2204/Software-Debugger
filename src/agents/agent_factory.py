from autogen import AssistantAgent, UserProxyAgent
from src.config import Config

class AgentFactory:
    def __init__(self):
        # Dynamically build the config list based on available keys
        config_list = []
        
        # Add Groq keys if available (Primary)
        groq_keys = Config.get_groq_keys()
        for key in groq_keys:
            config_list.append({
                "model": Config.GROQ_MODEL,
                "api_key": key,
                "base_url": "https://api.groq.com/openai/v1",
                "api_type": "openai"
            })
        
        # Add Gemini key (Fallback)
        if Config.GOOGLE_API_KEY:
            config_list.append({
                "model": Config.MODEL,
                "api_key": Config.GOOGLE_API_KEY,
                "api_type": "google"
            })

        self.llm_config = {
            "config_list": config_list,
            "temperature": 0.2,
            "cache_seed": None, # Disable caching to ensure fresh results for diagram selection
        }

    def create_code_parser_agent(self):
        return AssistantAgent(
            name="Code_Parser",
            system_message="Analyze the codebase structure and identify key modules.",
            llm_config=self.llm_config,
        )

    def create_bug_detection_agent(self):
        return AssistantAgent(
            name="Bug_Detection",
            system_message="Identify potential logical errors or security vulnerabilities.",
            llm_config=self.llm_config,
        )

    def create_patch_generator_agent(self):
        return AssistantAgent(
            name="Patch_Generator",
            system_message="Suggest concrete code patches or refactorings to fix identified bugs.",
            llm_config=self.llm_config,
        )

    def create_test_writer_agent(self):
        return AssistantAgent(
            name="Test_Writer",
            system_message="Generate unit tests or integration tests to verify the fixes.",
            llm_config=self.llm_config,
        )

    def create_reviewer_agent(self):
        return AssistantAgent(
            name="Reviewer",
            system_message="Review analysis, patches, and tests. Provide final approval.",
            llm_config=self.llm_config,
        )

    def create_diagram_generator_agent(self):
        return AssistantAgent(
            name="Diagram_Generator",
            system_message="""You are an expert at software architecture and system design.
            Based on the provided codebase summary, generate Mermaid diagrams for the requested types.
            
            STRICT RULES for Mermaid Syntax:
            1. ONLY use standard diagram types: 'graph TD' (for Flowcharts/System Design), 'classDiagram', 'sequenceDiagram', 'stateDiagram-v2', 'erDiagram', 'gantt', 'pie'.
            2. NEVER use 'architecture' as a type.
            3. ALWAYS wrap node labels in double quotes. Example: A["Component (v1.0)"]
            4. Node IDs must be simple alphanumeric strings (e.g., node1, app_core). NEVER use punctuation or spaces in IDs.
            5. For Flowcharts, always start with 'graph TD'.
            
            Deliverables:
            Provide a separate ```mermaid block for EVERY specific diagram type requested.
            Label each block with a clear Markdown header (e.g. ### Class Diagram).
            Be accurate and technical.""",
            llm_config=self.llm_config,
        )

    def create_repo_chat_agent(self):
        return AssistantAgent(
            name="Repo_Chat_Agent",
            system_message="""You are a helpful software engineering assistant. 
            You have access to a summary of the user's repository. 
            Answer their questions accurately based on the provided context. 
            If you don't know the answer, say so. Be concise and professional.""",
            llm_config=self.llm_config,
        )

    def create_user_proxy(self):
        return UserProxyAgent(
            name="User_Proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,  # Disable back-and-forth auto-replies
            is_termination_msg=lambda x: True, # Handle each turn as a single exchange
            code_execution_config=False,  # Disable code execution to save tokens/requests
        )
