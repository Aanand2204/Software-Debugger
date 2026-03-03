import time
import sys
from autogen import AssistantAgent, UserProxyAgent
from src.agents.agent_factory import AgentFactory
from src.config import logger

class Orchestrator:
    def __init__(self):
        self.factory = AgentFactory()

    def _validate_msg(self, user_proxy, agent):
        msg = user_proxy.last_message(agent)
        content = msg.get("content", "") if msg else ""
        if any(err in content.lower() for err in ["upstream request", "429", "rate limit", "quota exceeded", "api key invalid"]):
            return f"⚠️ **AI Agent Error ({agent.name})**: The AI provider returned an error: {content[:100]}..."
        return content

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
            print("--- PHASE 1: Parsing Codebase Structure ---", file=sys.stderr, flush=True)
            time.sleep(1) 
            print("--- Analyzing project structure... ---", file=sys.stderr, flush=True)
            user_proxy.initiate_chat(parser, message=f"Parse this: {repo_summary}", silent=True, clear_history=False)
            all_messages.append({"name": "Code_Parser", "content": self._validate_msg(user_proxy, parser)})
            
            # Phase 2: Detection
            print("--- PHASE 2: Detecting Bugs & Vulnerabilities ---", file=sys.stderr, flush=True)
            time.sleep(2)
            parsing_result = all_messages[-1]["content"]
            print("--- Scanning for bugs and vulnerabilities... ---", file=sys.stderr, flush=True)
            user_proxy.initiate_chat(detector, message=f"Analyze these files for bugs:\n{parsing_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Bug_Detection", "content": self._validate_msg(user_proxy, detector)})

            # Phase 3: Patching
            print("--- PHASE 3: Generating Fix Suggestions ---", file=sys.stderr, flush=True)
            time.sleep(2)
            detection_result = all_messages[-1]["content"]
            print("--- Crafting solution patches... ---", file=sys.stderr, flush=True)
            user_proxy.initiate_chat(patcher, message=f"Suggest fixes for these bugs:\n{detection_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Patch_Generator", "content": self._validate_msg(user_proxy, patcher)})

            # Phase 4: Review
            print("--- PHASE 4: Final AI Review ---", file=sys.stderr, flush=True)
            time.sleep(2)
            patch_result = all_messages[-1]["content"]
            print("--- Performing final AI review... ---", file=sys.stderr, flush=True)
            user_proxy.initiate_chat(reviewer, message=f"Review these patches:\n{patch_result}", silent=True, clear_history=False)
            all_messages.append({"name": "Reviewer", "content": self._validate_msg(user_proxy, reviewer)})

            # Optional Phase 5: Diagram Generation (Sequential for Reliability)
            if generate_diagrams and diagram_types:
                print(f"--- PHASE 5: Sequential Generation of {len(diagram_types)} Diagrams ---", file=sys.stderr, flush=True)
                diagram_gen = self.factory.create_diagram_generator_agent()
                
                diagram_contents = []
                for d_type in diagram_types:
                    print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                    time.sleep(2) # Quota protection
                    
                    prompt = (
                        f"Generate exactly ONE high-quality Mermaid diagram of type: {d_type}.\n\n"
                        + "Repository Context:\n" + repo_summary
                        + "\n\nBULLETPROOF RULES: IDs must be alphanumeric. Wrap values in double quotes. "
                        + "One-line labels only. Output in ONE ```mermaid block with a header."
                    )
                    
                    user_proxy.initiate_chat(diagram_gen, message=prompt, silent=True, clear_history=False)
                    diagram_result = self._validate_msg(user_proxy, diagram_gen)
                    diagram_contents.append(diagram_result)
                
                # Combine all diagram results into one response
                combined_diagrams = "\n\n".join(diagram_contents)
                all_messages.append({"name": "Diagram_Generator", "content": combined_diagrams})

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
            
            msg = user_proxy.last_message(chat_agent)
            response = msg.get("content", "") if msg else ""
            if any(err in response.lower() for err in ["upstream request", "429", "rate limit", "quota exceeded"]):
                response = f"⚠️ **Chat Error**: The AI encountered an issue: {response[:100]}..."
            
            return {"name": "Repo_Chat_Agent", "content": response}
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            return {"name": "Error", "content": f"Chatbot error: {e}"}

    def generate_diagrams_only(self, repo_summary, diagram_types):
        """Generates specific diagrams independently with sequential stability."""
        try:
            print(f"--- Independent Generation of {len(diagram_types)} Diagrams ---", file=sys.stderr, flush=True)
            diagram_gen = self.factory.create_diagram_generator_agent()
            user_proxy = self.factory.create_user_proxy()
            
            diagram_contents = []
            for d_type in diagram_types:
                print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                time.sleep(2)
                
                prompt = (
                    f"Generate exactly ONE high-quality Mermaid diagram of type: {d_type}.\n\n"
                    + "Repository Context:\n" + repo_summary
                    + "\n\nBULLETPROOF RULES: IDs must be alphanumeric. Wrap values in double quotes. "
                    + "One-line labels only. Output in ONE ```mermaid block with a header."
                )
                
                user_proxy.initiate_chat(diagram_gen, message=prompt, silent=True, clear_history=False)
                diagram_result = self._validate_msg(user_proxy, diagram_gen)
                diagram_contents.append(diagram_result)
            
            combined = "\n\n".join(diagram_contents)
            return {"name": "Diagram_Generator", "content": combined}
        except Exception as e:
            logger.error(f"Error in independent diagram generation: {e}")
            return {"name": "Error", "content": f"Diagram generation error: {e}"}
