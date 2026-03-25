from autogen import AssistantAgent, UserProxyAgent
from src.config import Config
import src.agents.prompts as prompts

class AgentFactory:
    def __init__(self):
        self.groq_keys = Config.get_groq_keys()
        self.current_groq_index = 0
        self.refresh_config()

    def _build_config(self, model_name, gemini_first=False):
        """Helper to build a config list with optional Gemini prioritization."""
        groq_configs = []
        if self.groq_keys:
            rotated_keys = self.groq_keys[self.current_groq_index:] + self.groq_keys[:self.current_groq_index]
            for key in rotated_keys:
                groq_configs.append({
                    "model": model_name,
                    "api_key": key,
                    "base_url": "https://api.groq.com/openai/v1",
                    "api_type": "openai",
                    "max_retries": 0
                })
        
        gemini_configs = []
        if Config.GOOGLE_API_KEY:
            gemini_configs.append({
                "model": Config.MODEL,
                "api_key": Config.GOOGLE_API_KEY,
                "api_type": "google",
                "max_retries": 0
            })

        return gemini_configs + groq_configs if gemini_first else groq_configs + gemini_configs

    def refresh_config(self):
        """Builds/Refreshes both heavy and light llm_configs."""
        common_params = {
            "temperature": 0,
            "cache_seed": None,
            "timeout": 60,
            "max_retries": 0
        }
        
        # Heavy Analysis (Detection, Patching, Review) -> Gemini First (Better Quota)
        self.llm_config = {
            "config_list": self._build_config(Config.GROQ_MODEL, gemini_first=True),
            **common_params
        }
        
        # Structural/Fast (Parsing, Diagrams) -> Groq First (Better Speed)
        self.llm_config_light = {
            "config_list": self._build_config(Config.GROQ_MODEL_LIGHT, gemini_first=False),
            **common_params
        }

    @staticmethod
    def truncate_context(text, max_chars=4000):
        """Truncates massive context strings to prevent token overflow."""
        if not text: return ""
        if len(text) <= max_chars: return text
        return text[:max_chars] + "\n... [Context truncated for quota safety] ..."

    def get_masked_key(self):
        """Returns the current key with masking (e.g., gsk_...1234)."""
        if not self.groq_keys: return "N/A"
        key = self.groq_keys[self.current_groq_index]
        return f"{key[:8]}...{key[-4:]}"

    def rotate_key(self):
        """Switches to the next available Groq key. Returns True if rotated, False otherwise."""
        if len(self.groq_keys) > 1:
            self.current_groq_index = (self.current_groq_index + 1) % len(self.groq_keys)
            self.refresh_config()
            return True
        return False

    def create_code_parser_agent(self):
        return AssistantAgent(
            name="Code_Parser",
            system_message=prompts.CODE_PARSER_PROMPT,
            llm_config=self.llm_config_light,
        )

    def create_bug_detection_agent(self):
        return AssistantAgent(
            name="Bug_Detection",
            system_message=prompts.BUG_DETECTION_PROMPT,
            llm_config=self.llm_config,
        )

    def create_patch_generator_agent(self):
        return AssistantAgent(
            name="Patch_Generator",
            system_message=prompts.PATCH_GENERATOR_PROMPT,
            llm_config=self.llm_config,
        )

    def create_reviewer_agent(self):
        return AssistantAgent(
            name="Reviewer",
            system_message=prompts.REVIEWER_PROMPT,
            llm_config=self.llm_config,
        )

    def create_patch_applier_agent(self):
        return AssistantAgent(
            name="Patch_Applier",
            system_message=prompts.PATCH_APPLIER_PROMPT,
            llm_config=self.llm_config,
        )

    def create_diagram_generator_agent(self):
        return AssistantAgent(
            name="Diagram_Generator",
            system_message=prompts.DIAGRAM_GENERATOR_PROMPT,
            llm_config=self.llm_config,
        )

    def create_repo_chat_agent(self):
        return AssistantAgent(
            name="Repo_Chat_Agent",
            system_message=prompts.REPO_CHAT_PROMPT,
            llm_config=self.llm_config,
        )

    def create_user_proxy(self):
        return UserProxyAgent(
            name="User_Proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            is_termination_msg=lambda x: True,
            code_execution_config=False,
        )
