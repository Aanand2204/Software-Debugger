import time
from autogen import AssistantAgent, UserProxyAgent
from src.agents.agent_factory import AgentFactory
from src.config import logger

class Orchestrator:
    def __init__(self):
        self.factory = AgentFactory()

    def run_debugging_session(self, repo_summary, generate_diagrams=False, diagram_types=None):
        """Orchestrates the debugging process sequentially with aggressive delays to save quota."""
        try:
            # Initialize Agents
            parser = self.factory.create_code_parser_agent()
            detector = self.factory.create_bug_detection_agent()
            patcher = self.factory.create_patch_generator_agent()
            reviewer = self.factory.create_reviewer_agent()
            user_proxy = self.factory.create_user_proxy()

            all_messages = []

            # Phase 1: Parsing
            logger.info("Starting Parsing Phase...")
            time.sleep(5) 
            user_proxy.initiate_chat(parser, message=f"Parse this: {repo_summary}", silent=True, clear_history=False)
            all_messages.append({"name": "Code_Parser", "content": user_proxy.last_message(parser)["content"]})
            
            # Phase 2: Detection
            logger.info("Starting Detection Phase...")
            time.sleep(20)
            parsing_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(detector, message=f"Analyze these files for bugs:\n{parsing_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Bug_Detection", "content": user_proxy.last_message(detector)["content"]})

            # Phase 3: Patching
            logger.info("Starting Patching Phase...")
            time.sleep(20)
            detection_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(patcher, message=f"Suggest fixes for these bugs:\n{detection_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Patch_Generator", "content": user_proxy.last_message(patcher)["content"]})

            # Phase 4: Review
            logger.info("Starting Review Phase...")
            time.sleep(20)
            patch_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(reviewer, message=f"Review these patches:\n{patch_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Reviewer", "content": user_proxy.last_message(reviewer)["content"]})

            # Optional Phase 5: Diagram Generation
            if generate_diagrams and diagram_types:
                logger.info(f"Starting Diagram Generation Phase for: {diagram_types}...")
                time.sleep(20)
                diagram_gen = self.factory.create_diagram_generator_agent()
                types_str = ", ".join(diagram_types)
                prompt = f"Generate the following specific diagram types for this repo:\n{types_str}\n\nRepository Context:\n{repo_summary}"
                user_proxy.initiate_chat(diagram_gen, message=prompt, silent=True, clear_history=False)
                all_messages.append({"name": "Diagram_Generator", "content": user_proxy.last_message(diagram_gen)["content"]})

            return all_messages
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                logger.error("Quota Exceeded (429) across all configured keys.")
                return [{"name": "System", "content": "⚠️ **Quota Exceeded (429)**: The API rate limit has been reached for ALL configured keys. Please wait a few minutes and try again."}]
            logger.error(f"Error in debugging session: {e}")
            return [{"name": "Error", "content": f"An unexpected error occurred: {e}"}]

    def chat_with_repo(self, repo_summary, user_query, chat_history=[]):
        """Handles a conversational query about the repository."""
        try:
            chat_agent = self.factory.create_repo_chat_agent()
            user_proxy = self.factory.create_user_proxy()

            # Format history for AutoGen if needed, but for a single turn with context:
            prompt = f"Here is the repository context:\n{repo_summary}\n\nUser Question: {user_query}"
            
            user_proxy.initiate_chat(chat_agent, message=prompt, silent=True, clear_history=False)
            response = user_proxy.last_message(chat_agent)["content"]
            
            return {"name": "Repo_Chat_Agent", "content": response}
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            return {"name": "Error", "content": f"Chatbot error: {e}"}

    def generate_diagrams_only(self, repo_summary, diagram_types):
        """Generates specific diagrams without running the full debugging pipeline."""
        try:
            logger.info(f"Starting Independent Diagram Generation for: {diagram_types}...")
            diagram_gen = self.factory.create_diagram_generator_agent()
            user_proxy = self.factory.create_user_proxy()
            
            types_str = ", ".join(diagram_types)
            prompt = f"Generate the following specific diagram types for this repo:\n{types_str}\n\nRepository Context:\n{repo_summary}"
            
            user_proxy.initiate_chat(diagram_gen, message=prompt, silent=True, clear_history=False)
            response = user_proxy.last_message(diagram_gen)["content"]
            
            return {"name": "Diagram_Generator", "content": response}
        except Exception as e:
            logger.error(f"Error in independent diagram generation: {e}")
            return {"name": "Error", "content": f"Diagram generation error: {e}"}
