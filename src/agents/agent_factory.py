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
            "temperature": 0,
            "cache_seed": 42, # Enable caching for deterministic diagram generation
        }

    def create_code_parser_agent(self):
        return AssistantAgent(
            name="Code_Parser",
            system_message="Analyze the local workspace structure and identify key modules. You are part of a VS Code extension.",
            llm_config=self.llm_config,
        )

    def create_bug_detection_agent(self):
        return AssistantAgent(
            name="Bug_Detection",
            system_message="""Identify potential logical errors or security vulnerabilities. 
            FORMATTING RULES:
            1. Use '###' for main finding headers.
            2. Use regular text for descriptions. 
            3. Use triple backticks with a language (e.g. ```python) ONLY for code snippets.
            4. NEVER wrap headings or descriptions in triple backticks.""",
            llm_config=self.llm_config,
        )

    def create_patch_generator_agent(self):
        return AssistantAgent(
            name="Patch_Generator",
            system_message="""Suggest concrete code patches or refactorings to fix identified bugs. 
            FORMATTING RULES:
            1. Use '###' for main patch headers.
            2. Use regular text for explanations. 
            3. ALWAYS provide code fixes inside triple backticks with the correct language (e.g. ```python).
            4. NEVER wrap headings, file paths, or reasoning in triple backticks. Keep them as plain text.""",
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
            system_message="""Review analysis, patches, and tests. Provide final approval.
            FORMATTING RULES:
            1. Be professional and concise. 
            2. Use Markdown headers for different categories of feedback.
            3. Triple backticks are ONLY for code snippets. Do not use them for emphasis or framing text.""",
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
            
            STRICT SYNTAX RULES (BULLETPROOF):
            1. Provide a separate ```mermaid block for EVERY specific diagram type requested.
            2. ALWAYS include a Markdown header (e.g. ### Class Diagram) before each block.
            
            3. FOR ALL DIAGRAMS:
               - Node IDs must be SHORT, ALPHANUMERIC (e.g. A, B, C, Node1, Node2).
               - DO NOT use spaces, hyphens, or punctuation in IDs.
               - ALWAYS wrap labels in double quotes: NodeID["Label Text"].
               - Labels must contain ONLY A-Z, a-z, 0-9, and spaces.
               - CRITICAL: NO PARENTHESES () OR BRACKETS [] ALLOWED IN LABELS, EVEN IN QUOTES.
            
            4. FOR Flowcharts (System Design / Use Case):
               - Use standard arrow: A["Auth"] --> B["DB"].
               - NEVER use single hyphens: - (invalid for connections).
               - Use ONLY --> for connections.
            
            5. FOR 'classDiagram':
               - Format: class ClassName { +type memberName }
               - Strictly use simple relationships: ClassA <|-- ClassB (Inheritance) or ClassA *-- ClassB (Composition).
            
            6. NO MULTI-LINE LABELS: Labels must be a single string without line breaks.
            7. Ensure diagrams are valid for Mermaid v10.9.5.""",
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
