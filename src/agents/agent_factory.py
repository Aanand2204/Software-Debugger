from autogen import AssistantAgent, UserProxyAgent
from src.config import Config

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
            system_message="""Analyze the local workspace structure. 
            Identify key modules, entry points, and potential configuration mismatches. 
            Highlight if any expected directories (like 'src' or 'tests') are missing.
            BE CONCISE. Use Markdown headers for organization.""",
            llm_config=self.llm_config_light,
        )

    def create_bug_detection_agent(self):
        return AssistantAgent(
            name="Bug_Detection",
            system_message="""Identify potential logical errors, security vulnerabilities, or performance bottlenecks.
            DO NOT SUGGEST FIXES. Only identify and explain the 'how' and 'why' of the issue.
            FORMATTING RULES:
            1. Use '###' for finding headers.
            2. Triple backticks (```python) ONLY for highlighting the problematic code.
            3. NEVER wrap explanations in backticks.""",
            llm_config=self.llm_config,
        )

    def create_patch_generator_agent(self):
        return AssistantAgent(
            name="Patch_Generator",
            system_message="""Suggest concrete code patches or refactorings to fix detected bugs. 
            Provide exactly one primary fix per issue unless alternatives are critical.
            STRICT RULES:
            1. Use '###' for header.
            2. ALWAYS specify the target file path using the format: #### [FILE] path/to/file.py
            3. ALWAYS provide code fixes inside triple backticks (```python).
            4. Keep explanations brief and focused on the change.
            5. 🔥 MANDATORY ANTI-HALLUCINATION: NEVER introduce new imports.
            6. ONLY use standard libraries OR modules explicitly listed in the 'Workspace File List'.
            7. ⚠️ NUCLEAR GUARD ACTIVE: Any hallucinated imports (e.g. 'ai_copilot', 'file_processor', 'copilot_utils') will be AUTOMATICALLY STRIPPED from your code, likely breaking it. Do not attempt to use them.
            8. If a module is not in the list, IT DOES NOT EXIST. Do not use it. 
            9. NEVER use helper classes from non-existent modules like 'AICopilot'. 
            """,
            llm_config=self.llm_config,
        )

    def create_reviewer_agent(self):
        return AssistantAgent(
            name="Reviewer",
            system_message="""Review the proposed patches for safety, efficiency, and side effects.
            STRICT RULES:
            1. DO NOT REPEAT the bug description or the patch code. 
            2. ONLY provide a critical evaluation: Is it safe? Does it solve the root cause?
            3. Remove any filler text like 'I have reviewed' or 'This looks good'. 
            4. If approved, start with '✅ APPROVED'. If changes are needed, start with '❌ REJECTED'.
            5. Triple backticks are ONLY for specific code adjustments you recommend.""",
            llm_config=self.llm_config,
        )

    def create_patch_applier_agent(self):
        return AssistantAgent(
            name="Patch_Applier",
            system_message="""You are a precision code merging tool. 
            Your task is to take the ORIGINAL file content and a PATCH suggestion, and return the COMPLETE, UPDATED file content.
            STRICT RULES:
            1. ONLY return the updated code inside triple backticks (```python).
            2. DO NOT include any explanations, headers, or commentary.
            3. Preserve the original indentation and style exactly.
            4. Ensure the resulting code is syntactically correct and complete.
            5. 🔥 MANDATORY ANTI-HALLUCINATION: If the patch suggestion introduces a new import that wasn't in the original code AND isn't a standard library, STRIP IT OUT IMMEDIATELY.
            6. Do not 'guess' helper modules. If it's not in the original code, it shouldn't be added.
            7. 🛑 STOP: Modules like 'ai_copilot' are forbidden. Do not include them even if the user or previous agent mentioned them.
            """,
            llm_config=self.llm_config,
        )

    def create_diagram_generator_agent(self):
        return AssistantAgent(
            name="Diagram_Generator",
            system_message="""You are a world-class Systems Architect. 
            Define the system architecture in a structured JSON format for a professional blueprint.

            OUTPUT FORMAT (Strictly JSON inside a ```json block):
            {
              "nodes": [
                {"id": "node1", "label": "Example Client", "layer": 0},
                {"id": "node2", "label": "Example Service", "layer": 1},
                {"id": "node3", "label": "Example Logic", "layer": 2},
                {"id": "node4", "label": "Example DB", "layer": 3}
              ],
              "edges": [
                {"from": "node1", "to": "node2", "label": "action"},
                {"from": "node2", "to": "node3", "label": "flow"},
                {"from": "node3", "to": "node4", "label": "storage"}
              ]
            }

            STRICT RULES:
            1. ONLY provide the JSON block. 
            2. Use concise, professional labels. 
            3. MANDATORY: Assign each layer an integer (0=Top, 1=Middle, 2=Lower, 3=Bottom).
            4. 🛑 CRITICAL: DO NOT copy the example nodes! The example above is purely for syntax formatting. You must generate COMPLETELY UNIQUE nodes, edges, and topologies based entirely on the actual repository summary provided to you.
            5. Do not attempt coordinate math; the rendering engine will handle layout.
            6. Header (### Diagram Type) MUST be outside the code block.
""",
            llm_config=self.llm_config,
        )

    def create_repo_chat_agent(self):
        return AssistantAgent(
            name="Repo_Chat_Agent",
            system_message="""You are a helpful software engineering assistant integrated into VS Code.
            You have access to a summary of the user's local workspace. 
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
