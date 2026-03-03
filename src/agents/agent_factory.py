from autogen import AssistantAgent, UserProxyAgent
from src.config import Config

class AgentFactory:
    def __init__(self):
        self.groq_keys = Config.get_groq_keys()
        self.current_groq_index = 0
        self.refresh_config()

    def refresh_config(self):
        """Builds/Refreshes the llm_config with current key prioritization."""
        config_list = []
        
        # Add Groq keys starting from the current index
        if self.groq_keys:
            # We cycle the list so the 'current' index is always tried first by AutoGen
            rotated_keys = self.groq_keys[self.current_groq_index:] + self.groq_keys[:self.current_groq_index]
            for key in rotated_keys:
                config_list.append({
                    "model": Config.GROQ_MODEL,
                    "api_key": key,
                    "base_url": "https://api.groq.com/openai/v1",
                    "api_type": "openai",
                    "max_retries": 0  # Force immediate exception to trigger orchestrator rotation
                })
        
        # Add Gemini key (Final Fallback)
        if Config.GOOGLE_API_KEY:
            config_list.append({
                "model": Config.MODEL,
                "api_key": Config.GOOGLE_API_KEY,
                "api_type": "google",
                "max_retries": 0
            })

        self.llm_config = {
            "config_list": config_list,
            "temperature": 0,
            "cache_seed": 42,
            "timeout": 60,
            "max_retries": 0
        }

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
            llm_config=self.llm_config,
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
            FORMATTING RULES:
            1. Use '###' for header.
            2. ALWAYS provide code fixes inside triple backticks (```python).
            3. Keep explanations brief and focused on the change.""",
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

    def create_diagram_generator_agent(self):
        return AssistantAgent(
            name="Diagram_Generator",
            system_message="""You are an expert software architect. Generate Mermaid diagrams based on the codebase summary.
            
            DIAGRAM TYPE MAPPING (STRICT):
            - "System Design" -> Use 'graph TD' (Flowchart)
            - "Class Diagram" -> Use 'classDiagram'
            - "Use Case Diagram" -> Use 'graph LR' (Flowchart)
            - "Sequence Diagram" -> Use 'sequenceDiagram'
            - "Activity Diagram" -> Use 'graph TD' (Flowchart)
            - "State Diagram" -> Use 'stateDiagram-v2'
            - "ER Diagram" -> Use 'erDiagram'
            
            STRICT SYNTAX RULES (BULLETPROOF):
            1. Provide a separate ```mermaid block for EVERY specific diagram type requested.
            2. ALWAYS include a Markdown header (e.g. ### Class Diagram) before each block.
            
            3. FOR ALL DIAGRAMS:
               - Node IDs must be SHORT, ALPHANUMERIC (e.g. A, B, C, Node1, Node2).
               - DO NOT use spaces, hyphens, or punctuation in IDs.
               - ALWAYS wrap labels in double quotes: NodeID["Label Text"].
               - Labels must contain ONLY A-Z, a-z, 0-9, and spaces.
               - CRITICAL: NO PARENTHESES () OR BRACKETS [] ALLOWED IN LABELS.
            
            4. FOR 'sequenceDiagram':
               - Use: ParticipantA->>ParticipantB: "Message Text"
               - NEVER use parentheses in messages.
            
            5. FOR 'erDiagram':
               - Use simple format: ENTITY1 ||--o{ ENTITY2 : "relation"
               - Keep attributes simple: ENTITY1 { string name }
            
            6. FOR 'stateDiagram-v2':
               - Use: [*] --> State1
               - State1 --> State2: "Event"
            
            7. NO MULTI-LINE LABELS: Labels must be a single string without line breaks.
            8. Ensure diagrams are valid for Mermaid v10.9.5.""",
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
