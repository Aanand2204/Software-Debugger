import time
from autogen import AssistantAgent, UserProxyAgent
from src.agents.agent_factory import AgentFactory
from src.config import logger

class Orchestrator:
    def __init__(self):
        self.factory = AgentFactory()

    def run_debugging_session(self, repo_summary):
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
            user_proxy.initiate_chat(parser, message=f"Parse this: {repo_summary}", silent=True, clear_history=False)
            all_messages.append({"name": "Code_Parser", "content": user_proxy.last_message(parser)["content"]})
            
            # Throttle delay (Aggressive for Free Tier)
            logger.info("Waiting for quota reset (40s)...")
            time.sleep(40)

            # Phase 2: Detection
            logger.info("Starting Detection Phase...")
            parsing_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(detector, message=f"Analyze these files for bugs:\n{parsing_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Bug_Detection", "content": user_proxy.last_message(detector)["content"]})

            # Throttle delay
            logger.info("Waiting for quota reset (40s)...")
            time.sleep(40)

            # Phase 3: Patching
            logger.info("Starting Patching Phase...")
            detection_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(patcher, message=f"Suggest fixes for these bugs:\n{detection_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Patch_Generator", "content": user_proxy.last_message(patcher)["content"]})

            # Throttle delay
            logger.info("Waiting for quota reset (40s)...")
            time.sleep(40)

            # Phase 4: Review
            logger.info("Starting Review Phase...")
            patch_result = all_messages[-1]["content"]
            user_proxy.initiate_chat(reviewer, message=f"Review these patches:\n{patch_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Reviewer", "content": user_proxy.last_message(reviewer)["content"]})

            return all_messages
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                logger.error("Quota Exceeded (429). Please wait a minute and try again.")
                return [{"name": "System", "content": "⚠️ **Quota Exceeded (429)**: The Gemini API free tier limit has been reached. Please wait even longer (e.g. 2 minutes) and try again."}]
            logger.error(f"Error in debugging session: {e}")
            return [{"name": "Error", "content": f"An unexpected error occurred: {e}"}]
