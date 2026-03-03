import time
import sys
from autogen import AssistantAgent, UserProxyAgent
from src.agents.agent_factory import AgentFactory
from src.config import logger, Config

class Orchestrator:
    def __init__(self):
        self.factory = AgentFactory()

    def _validate_msg(self, user_proxy, agent):
        msg = user_proxy.last_message(agent)
        content = msg.get("content", "") if msg else ""
        if any(err in content.lower() for err in ["upstream request", "429", "rate limit", "quota exceeded", "api key invalid"]):
            return f"⚠️ **AI Agent Error ({agent.name})**: The AI provider returned an error: {content[:100]}..."
        return content

    def _run_step_with_rotation(self, agent_creator, user_proxy, message, phase_name, clear_history=True):
        """Runs an AI step with automatic key rotation on 429/quota errors."""
        max_attempts = len(self.factory.groq_keys) if self.factory.groq_keys else 1
        if Config.GOOGLE_API_KEY:
            max_attempts += 1

        for attempt in range(max_attempts):
            try:
                agent = agent_creator()
                if clear_history:
                    user_proxy.clear_history(agent)
                
                masked_key = self.factory.get_masked_key()
                print(f"--- Phase: {phase_name} | Attempt: {attempt+1}/{max_attempts} | Active Key: {masked_key} ---", file=sys.stderr, flush=True)
                
                user_proxy.initiate_chat(agent, message=message, silent=True, clear_history=False)
                result = self._validate_msg(user_proxy, agent)
                
                if "⚠️" in result:
                    if any(err in result.lower() for err in ["429", "quota", "rate limit"]):
                        if self.factory.rotate_key():
                            next_key = self.factory.get_masked_key()
                            print(f"--- ⚠️ Rate limit hit. Cooling down & Rotating to: {next_key} ---", file=sys.stderr, flush=True)
                            time.sleep(3)
                            continue
                return result, False
            except Exception as e:
                err_msg = str(e)
                if any(err in err_msg.lower() for err in ["429", "quota", "rate limit"]):
                    if self.factory.rotate_key():
                        next_key = self.factory.get_masked_key()
                        print(f"--- ⚠️ Rate limit exception. Cooling down & Rotating to: {next_key} ---", file=sys.stderr, flush=True)
                        time.sleep(3)
                        continue
                return f"⚠️ API Error: {err_msg}", True
        return "⚠️ Quota exhausted across all configured keys.", True

    def run_debugging_session(self, repo_summary, generate_diagrams=False, diagram_types=None):
        """Orchestrates the debugging process with isolated context tracking."""
        try:
            user_proxy = self.factory.create_user_proxy()
            all_results = {}

            # Phase 1: Parsing
            print("--- PHASE 1: Parsing Codebase Structure ---", file=sys.stderr, flush=True)
            msg, is_err = self._run_step_with_rotation(self.factory.create_code_parser_agent, user_proxy, f"Context:\n{repo_summary}\n\nTask: Parse this structure.", "Code Parsing")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["parsing"] = msg
            
            # Phase 2: Detection
            print("--- PHASE 2: Detecting Bugs & Vulnerabilities ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{repo_summary}\n\nProject Structure:\n{all_results['parsing']}\n\nTask: Locate bugs/vulnerabilities."
            msg, is_err = self._run_step_with_rotation(self.factory.create_bug_detection_agent, user_proxy, prompt, "Bug Detection")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["detection"] = msg

            # Phase 3: Patching
            print("--- PHASE 3: Generating Fix Suggestions ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{repo_summary}\n\nIdentified Issues:\n{all_results['detection']}\n\nTask: Suggest code patches."
            msg, is_err = self._run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, prompt, "Patch Generation")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["patching"] = msg

            # Phase 4: Review
            print("--- PHASE 4: Final AI Review ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{repo_summary}\n\nProposed Patches:\n{all_results['patching']}\n\nTask: Perform final review."
            msg, is_err = self._run_step_with_rotation(self.factory.create_reviewer_agent, user_proxy, prompt, "Final Review")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["review"] = msg

            # Format final list for UI
            final_messages = [
                {"name": "Code_Parser", "content": all_results["parsing"]},
                {"name": "Bug_Detection", "content": all_results["detection"]},
                {"name": "Patch_Generator", "content": all_results["patching"]},
                {"name": "Reviewer", "content": all_results["review"]}
            ]

            # Optional Phase 5: Diagram Generation
            if generate_diagrams and diagram_types:
                print(f"--- PHASE 5: Generating {len(diagram_types)} Diagrams ---", file=sys.stderr, flush=True)
                diagram_contents = []
                for d_type in diagram_types:
                    print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                    prompt = f"Context:\n{repo_summary}\n\nTask: Generate exactly ONE high-quality Mermaid diagram of type: {d_type}."
                    diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                    if is_err: return [{"name": "Error", "content": diag}]
                    diagram_contents.append(diag)
                
                final_messages.append({"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)})

            print("--- Analysis Session Completed Successfully ---", file=sys.stderr, flush=True)
            return final_messages
        except Exception as e:
            logger.error(f"Error in debugging session: {e}")
            return [{"name": "Error", "content": f"An unexpected error occurred: {e}"}]

    def chat_with_repo(self, repo_summary, user_query, chat_history=[]):
        """Handles a conversational query with isolated context."""
        try:
            user_proxy = self.factory.create_user_proxy()
            prompt = f"Context:\n{repo_summary}\n\nUser Question: {user_query}"
            msg, is_err = self._run_step_with_rotation(self.factory.create_repo_chat_agent, user_proxy, prompt, "Repo Chat")
            return {"name": "Repo_Chat_Agent", "content": msg}
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            return {"name": "Error", "content": f"Chatbot error: {e}"}

    def generate_diagrams_only(self, repo_summary, diagram_types):
        """Generates specific diagrams independently with isolated context."""
        try:
            user_proxy = self.factory.create_user_proxy()
            diagram_contents = []
            for d_type in diagram_types:
                print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                prompt = f"Context:\n{repo_summary}\n\nTask: Generate exactly ONE high-quality Mermaid diagram of type: {d_type}."
                diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                if is_err: return {"name": "Error", "content": diag}
                diagram_contents.append(diag)
            
            return {"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)}
        except Exception as e:
            logger.error(f"Error in diagram generation: {e}")
            return {"name": "Error", "content": f"Diagram generation error: {e}"}
