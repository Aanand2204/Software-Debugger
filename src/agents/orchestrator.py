import time
import sys
import re
import subprocess
import os
import ast
from autogen import AssistantAgent, UserProxyAgent
from src.agents.agent_factory import AgentFactory
from src.config import logger, Config
from src.utils.diagram_renderer import render_json_diagram

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
                # Determine model name from agent config
                model_name = "N/A"
                if hasattr(agent, "llm_config") and agent.llm_config.get("config_list"):
                    model_name = agent.llm_config["config_list"][0].get("model", "unknown")
                
                print(f"--- Phase: {phase_name} | Key: {masked_key} | Model: {model_name} ---", file=sys.stderr, flush=True)
                
                # Forced Pacing to prevent RPM (Requests Per Minute) spikes
                time.sleep(1.5) 
                
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

            # Quota Safety: Cap summary size
            safe_summary = self.factory.truncate_context(repo_summary)

            # Phase 1: Parsing
            print("--- PHASE 1: Parsing Codebase Structure ---", file=sys.stderr, flush=True)
            msg, is_err = self._run_step_with_rotation(self.factory.create_code_parser_agent, user_proxy, f"Context:\n{safe_summary}\n\nTask: Parse this structure.", "Code Parsing")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["parsing"] = msg
            
            # Phase 2: Detection
            print("--- PHASE 2: Detecting Bugs & Vulnerabilities ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{safe_summary}\n\nProject Structure:\n{all_results['parsing']}\n\nTask: Locate bugs/vulnerabilities."
            msg, is_err = self._run_step_with_rotation(self.factory.create_bug_detection_agent, user_proxy, prompt, "Bug Detection")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["detection"] = msg

            # Phase 3: Patching
            print("--- PHASE 3: Generating Fix Suggestions ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{safe_summary}\n\nIdentified Issues:\n{all_results['detection']}\n\nTask: Suggest code patches."
            msg, is_err = self._run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, prompt, "Patch Generation")
            if is_err: return [{"name": "Error", "content": msg}]
            all_results["patching"] = msg

            # Phase 4: Review
            print("--- PHASE 4: Final AI Review ---", file=sys.stderr, flush=True)
            time.sleep(1)
            prompt = f"Repository Summary:\n{safe_summary}\n\nProposed Patches:\n{all_results['patching']}\n\nTask: Perform final review."
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
                    time.sleep(2) # Extra delay
                    prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE high-quality Architectural SVG Blueprint of type: {d_type}."
                    diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                    if is_err: return [{"name": "Error", "content": diag}]
                    # Programmatically render JSON to professional SVG
                    rendered_diag = render_json_diagram(diag)
                    diagram_contents.append(rendered_diag)
                
                final_messages.append({"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)})

            print("--- Analysis Session Completed Successfully ---", file=sys.stderr, flush=True)
            return final_messages
        except Exception as e:
            logger.error(f"Error in debugging session: {e}")
            return [{"name": "Error", "content": f"An unexpected error occurred: {e}"}]

    def chat_with_repo(self, repo_summary, user_query, chat_history=[]):
        """Handles a conversational query with isolated context."""
        try:
            safe_summary = self.factory.truncate_context(repo_summary)
            user_proxy = self.factory.create_user_proxy()
            prompt = f"Context:\n{safe_summary}\n\nUser Question: {user_query}"
            msg, is_err = self._run_step_with_rotation(self.factory.create_repo_chat_agent, user_proxy, prompt, "Repo Chat")
            return {"name": "Repo_Chat_Agent", "content": msg}
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            return {"name": "Error", "content": f"Chatbot error: {e}"}

    def parse_patches(self, patch_generator_output):
        """Extracts file paths and code patches from the agent output."""
        patches = []
        # Look for #### [FILE] path/to/file.py followed by ```python ... ```
        pattern = r"#### \[FILE\]\s*(.*?)\s*\n.*?```python\n(.*?)\n```"
        matches = re.finditer(pattern, patch_generator_output, re.DOTALL)
        for match in matches:
            patches.append({
                "path": match.group(1).strip(),
                "patch_code": match.group(2).strip()
            })
        return patches

    def apply_patches_to_dir(self, patches, base_dir):
        """Applies a list of patches to files in the specified directory using the Patch Applier agent."""
        import os
        results = []
        user_proxy = self.factory.create_user_proxy()
        
        for p in patches:
            rel_path = p["path"]
            full_path = os.path.join(base_dir, rel_path)
            
            if not os.path.exists(full_path):
                results.append({"path": rel_path, "status": "Error: File not found"})
                continue
                
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
                
                prompt = f"ORIGINAL CONTENT:\n```python\n{original_content}\n```\n\nPROPOSED PATCH:\n```python\n{p['patch_code']}\n```\n\nTask: Merge them into a complete file."
                
                msg, is_err = self._run_step_with_rotation(self.factory.create_patch_applier_agent, user_proxy, prompt, f"Applying Patch to {rel_path}")
                
                if is_err:
                    results.append({"path": rel_path, "status": f"Error: {msg}"})
                    continue
                
                # Extract code from response
                code_match = re.search(r"```python\n(.*?)\n```", msg, re.DOTALL)
                new_content = code_match.group(1).strip() if code_match else msg.strip()
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # Validate Syntax
                syntax_ok, syntax_err = self.validate_syntax(new_content, rel_path)
                
                results.append({
                    "path": rel_path, 
                    "status": "Success", 
                    "new_content": new_content, 
                    "old_content": original_content,
                    "syntax_ok": syntax_ok,
                    "syntax_error": syntax_err
                })
            except Exception as e:
                results.append({"path": rel_path, "status": f"Error: {str(e)}"})
        
        return results

    def validate_syntax(self, code, path):
        """Checks if the code is syntactically correct (Python only for now)."""
        if not path.endswith(".py"):
            return True, None
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)

    def generate_diagrams_only(self, repo_summary, diagram_types):
        """Generates specific diagrams independently with isolated context."""
        try:
            safe_summary = self.factory.truncate_context(repo_summary)
            user_proxy = self.factory.create_user_proxy()
            diagram_contents = []
            for d_type in diagram_types:
                print(f"--- Sketching {d_type} Diagram... ---", file=sys.stderr, flush=True)
                time.sleep(2)
                prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE high-quality Architectural SVG Blueprint of type: {d_type}."
                diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
                if is_err: return {"name": "Error", "content": diag}
                # Programmatically render JSON to professional SVG
                rendered_diag = render_json_diagram(diag)
                diagram_contents.append(rendered_diag)
            
            return {"name": "Diagram_Generator", "content": "\n\n".join(diagram_contents)}
        except Exception as e:
            logger.error(f"Error in diagram generation: {e}")
            return {"name": "Error", "content": f"Diagram generation error: {e}"}
    def execute_command(self, cwd, command, timeout=30):
        """Executes a shell command synchronously and returns output."""
        try:
            process = subprocess.run(
                command, 
                cwd=cwd, 
                shell=True, 
                text=True, 
                capture_output=True, 
                timeout=timeout
            )
            output = f"--- STDOUT ---\n{process.stdout}\n\n--- STDERR ---\n{process.stderr}"
            return output, process.returncode == 0
        except subprocess.TimeoutExpired:
            return f"⚠️ Error: Command timed out after {timeout} seconds.", False
        except Exception as e:
            return f"⚠️ Exception: {str(e)}", False

    def spawn_command(self, cwd, command):
        """Spawns a shell command and returns the Popen process object."""
        try:
            # We use bufsize=1 (line buffered) and universal_newlines=True to read output in real-time
            process = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            return process
        except Exception as e:
            logger.error(f"Failed to spawn command: {e}")
            return None

    def kill_process(self, process):
        """Forcefully kills a process and its children."""
        if not process: return
        try:
            import psutil
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except ImportError:
            # Fallback if psutil is not available
            process.kill()
        except Exception:
            pass

    def suggest_entry_point(self, dir_path):
        """Scans the directory for common entry points to suggest a test command."""
        common_files = ["app.py", "main.py", "run.py", "index.py", "manage.py"]
        # Quote executable path in case it contains spaces
        python_exe = f'"{sys.executable}"'
        
        for f in common_files:
            if os.path.exists(os.path.join(dir_path, f)):
                return f"{python_exe} {f}"
        
        # Check for tests directory
        if os.path.exists(os.path.join(dir_path, "tests")):
            return f"{python_exe} -m pytest"
            
        return f"{python_exe} --version" # Default fallback
