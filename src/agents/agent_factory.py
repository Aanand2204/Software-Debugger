from autogen import AssistantAgent, UserProxyAgent
from src.config import Config

class AgentFactory:
    def __init__(self):
        # Specific config for Autogen 0.2.x Gemini support
        self.llm_config = {
            "config_list": [
                {
                    "model": Config.MODEL,
                    "api_key": Config.GOOGLE_API_KEY,
                    "api_type": "google"
                }
            ],
            "temperature": 0.2,
            "max_retries": 3,
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

    def create_user_proxy(self):
        return UserProxyAgent(
            name="User_Proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,  # Disable back-and-forth auto-replies
            is_termination_msg=lambda x: True, # Handle each turn as a single exchange
            code_execution_config=False,  # Disable code execution to save tokens/requests
        )
