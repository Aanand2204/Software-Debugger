import sys
import time
from src.agents.agent_factory import AgentFactory
from src.config import logger
from src.agents.managers.agent_runner import AgentRunner
from src.agents.managers.guard_manager import GuardManager
from src.agents.managers.patch_manager import PatchManager
from src.agents.managers.command_manager import CommandManager

class Orchestrator:
    def __init__(self):
        self.factory = AgentFactory()
        self.runner = AgentRunner(self.factory)
        self.guard_manager = GuardManager()
        self.patch_manager = PatchManager(self.runner, self.factory, self.guard_manager)
        
    def _validate_msg(self, user_proxy, agent):
        return self.runner.validate_msg(user_proxy, agent)

    def _run_step_with_rotation(self, agent_creator, user_proxy, message, phase_name, clear_history=True):
        return self.runner.run_step_with_rotation(agent_creator, user_proxy, message, phase_name, clear_history)

    def _check_for_hallucinated_imports(self, patch_text, workspace_files):
        return self.guard_manager.check_for_hallucinated_imports(patch_text, workspace_files)

    def _strip_hallucinated_imports(self, content, hallucinations):
        return self.guard_manager.strip_hallucinated_imports(content, hallucinations)

    def parse_patches(self, patch_generator_output):
        return self.patch_manager.parse_patches(patch_generator_output)

    def apply_patches_to_dir(self, patches, base_dir, workspace_files=None):
        return self.patch_manager.apply_patches_to_dir(patches, base_dir, workspace_files)

    def validate_syntax(self, code, path):
        return self.patch_manager.validate_syntax(code, path)

    def execute_command(self, cwd, command, timeout=30):
        return CommandManager.execute_command(cwd, command, timeout)

    def spawn_command(self, cwd, command):
        return CommandManager.spawn_command(cwd, command)

    def kill_process(self, process):
        CommandManager.kill_process(process)

    def suggest_entry_point(self, dir_path):
        return CommandManager.suggest_entry_point(dir_path)

    # Core Orchestration Logic Kept Below:
    def run_debugging_session(self, repo_summary, generate_diagrams=False, diagram_types=None, workspace_files=None):
        """Orchestrates the debugging process with isolated context tracking."""
        try:
            user_proxy = self.factory.create_user_proxy()
            all_results = {}

            # Quota Safety: Cap summary size
            safe_summary = self.factory.truncate_context(repo_summary)

            # Phase 1: Parsing
            print("--- PHASE 1: Parsing Codebase Structure ---", file=sys.stderr, flush=True)
            msg, is_err = self.runner.run_step_with_rotation(self.factory.create_code_parser_agent, user_proxy, f"Context:\n{safe_summary}\n\nTask: Parse this structure.", "Code Parsing")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["parsing"] = msg
            
            # Phase 2: Detection
            print("--- PHASE 2: Detecting Bugs & Vulnerabilities ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{safe_summary}\n\nProject Structure:\n{all_results['parsing']}\n\nTask: Locate bugs/vulnerabilities."
            msg, is_err = self.runner.run_step_with_rotation(self.factory.create_bug_detection_agent, user_proxy, prompt, "Bug Detection")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["detection"] = msg

            # Phase 3: Patching
            print("--- PHASE 3: Generating Fix Suggestions ---", file=sys.stderr, flush=True)
            time.sleep(1)
            file_list_str = "\n".join([f"- {f}" for f in workspace_files]) if workspace_files else "None provided."
            prompt = f"Repository Summary:\n{safe_summary}\n\nWorkspace File List (Available modules):\n{file_list_str}\n\nIdentified Issues:\n{all_results['detection']}\n\nTask: Suggest code patches."
            
            msg, is_err = self.run_patch_generation_cycle(prompt, workspace_files, user_proxy)
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["patching"] = msg

            # Phase 4: Review
            print("--- PHASE 4: Final AI Review ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{safe_summary}\n\nProposed Patches:\n{all_results['patching']}\n\nTask: Perform final review."
            msg, is_err = self.runner.run_step_with_rotation(self.factory.create_reviewer_agent, user_proxy, prompt, "Final Review")
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
                    time.sleep(2) # Extra delay
                    prompt_details = "Focus on the step-by-step sequential flow of execution and data logic." if "Flow" in d_type or "Activity" in d_type else "Focus on static structural relationships, entities, and components." if "Class" in d_type or "ER" in d_type or "System" in d_type else "Focus on actors, interactions, and chronological message passing." if "Sequence" in d_type or "Use Case" in d_type else ""
                    schema_req = "\nOUTPUT EXACTLY THIS JSON FORMAT:\n```json\n{\"nodes\": [{\"id\": \"1\", \"label\": \"UI/Client\", \"layer\": 0}, {\"id\": \"2\", \"label\": \"API/Server\", \"layer\": 1}], \"edges\": [{\"from\": \"1\", \"to\": \"2\"}]}\n```\nNote: 'layer' must be 0 (UI/External), 1 (API/Gateway), 2 (Services), or 3 (Database)."
                    prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE structural JSON architecture blueprint tailored specifically for a {d_type}.\n{prompt_details}\nDO NOT just output a generic system architecture. DO NOT GENERATE SVG DIRECTLY.{schema_req}"
                    diag, is_err = self.runner.run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                    if is_err: return [{"name": "Error", "content": diag}]
                    # Programmatically render JSON to professional SVG
                    import src.utils.diagram_renderer as d_rend
                    import importlib
                    importlib.reload(d_rend)
                    rendered_diag = d_rend.render_json_diagram(diag)
                    diagram_contents.append(rendered_diag)
                
                final_messages.append({"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)})

            print("--- Analysis Session Completed Successfully ---", file=sys.stderr, flush=True)
            return final_messages
        except Exception as e:
            logger.error(f"Error in debugging session: {e}")
            return [{"name": "Error", "content": f"An unexpected error occurred: {e}"}]

    def run_patch_generation_cycle(self, prompt, workspace_files, user_proxy):
        """Generates patches and performs nuclear anti-hallucination re-checks."""
        msg, is_err = self.runner.run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, prompt, "Patch Generation")
        if is_err: return msg, True
        
        # Anti-Hallucination check 1
        hallucinations = self.guard_manager.check_for_hallucinated_imports(msg, workspace_files)
        if hallucinations:
            print(f"--- 🛡️ Nuclear Guard Phase 1: Detected hallucinations: {hallucinations} ---", file=sys.stderr, flush=True)
            # Hard Re-check with "Nuclear" Scolding
            re_prompt = f"🔥 NUCLEAR ERROR: Your patch suggested these NON-EXISTENT modules: {hallucinations}.\n\nSTRICT REQUIREMENT: NO NEW IMPORTS. ONLY USE WHAT IS IN THE PROJECT.\n\nRE-GENERATE NOW WITHOUT THESE MODULES.\n\nOriginal Attempt:\n{msg}"
            msg, is_err = self.runner.run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, re_prompt, "Patch Re-generation (Nuclear)")
            if is_err: return msg, True
            
            # Anti-Hallucination check 2 (post re-generation)
            hallucinations = self.guard_manager.check_for_hallucinated_imports(msg, workspace_files)
            if hallucinations:
                print(f"--- 🛡️ Nuclear Guard Phase 2: AI persistent! Stripping: {hallucinations} ---", file=sys.stderr, flush=True)
                # Hard Strip as final safety
                msg = self.guard_manager.strip_hallucinated_imports(msg, hallucinations)
            
        return msg, False

    def chat_with_repo(self, repo_summary, user_query, chat_history=[]):
        """Handles a conversational query with isolated context."""
        try:
            safe_summary = self.factory.truncate_context(repo_summary)
            user_proxy = self.factory.create_user_proxy()
            prompt = f"Context:\n{safe_summary}\n\nUser Question: {user_query}"
            msg, is_err = self.runner.run_step_with_rotation(self.factory.create_repo_chat_agent, user_proxy, prompt, "Repo Chat")
            return {"name": "Repo_Chat_Agent", "content": msg}
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            return {"name": "Error", "content": f"Chatbot error: {e}"}

    def generate_diagrams_only(self, repo_summary, diagram_types):
        """Generates specific diagrams independently with isolated context."""
        try:
            safe_summary = self.factory.truncate_context(repo_summary)
            user_proxy = self.factory.create_user_proxy()
            diagram_contents = []
            for d_type in diagram_types:
                print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                time.sleep(2)
                prompt_details = "Focus on the step-by-step sequential flow of execution and data logic." if "Flow" in d_type or "Activity" in d_type else "Focus on static structural relationships, entities, and components." if "Class" in d_type or "ER" in d_type or "System" in d_type else "Focus on actors, interactions, and chronological message passing." if "Sequence" in d_type or "Use Case" in d_type else ""
                schema_req = "\nOUTPUT EXACTLY THIS JSON FORMAT:\n```json\n{\"nodes\": [{\"id\": \"1\", \"label\": \"UI/Client\", \"layer\": 0}, {\"id\": \"2\", \"label\": \"API/Server\", \"layer\": 1}], \"edges\": [{\"from\": \"1\", \"to\": \"2\"}]}\n```\nNote: 'layer' must be 0 (UI/External), 1 (API/Gateway), 2 (Services), or 3 (Database)."
                prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE structural JSON architecture blueprint tailored specifically for a {d_type}.\n{prompt_details}\nDO NOT just output a generic system architecture. DO NOT GENERATE SVG DIRECTLY.{schema_req}"
                diag, is_err = self.runner.run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                if is_err: return {"name": "Error", "content": diag}
                # Programmatically render JSON to professional SVG
                import src.utils.diagram_renderer as d_rend
                import importlib
                importlib.reload(d_rend)
                rendered_diag = d_rend.render_json_diagram(diag)
                diagram_contents.append(rendered_diag)
            
            return {"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)}
        except Exception as e:
            logger.error(f"Error in diagram generation: {e}")
            return {"name": "Error", "content": f"Diagram generation error: {e}"}
