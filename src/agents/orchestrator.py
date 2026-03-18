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

    def run_debugging_session(self, repo_summary, generate_diagrams=False, diagram_types=None, workspace_files=None):
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
            file_list_str = "\n".join([f"- {f}" for f in workspace_files]) if workspace_files else "None provided."
            prompt = f"Repository Summary:\n{safe_summary}\n\nWorkspace File List (Available modules):\n{file_list_str}\n\nIdentified Issues:\n{all_results['detection']}\n\nTask: Suggest code patches."
            
            msg, is_err = self.run_patch_generation_cycle(prompt, workspace_files, user_proxy)
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
                    prompt_details = "Focus on the step-by-step sequential flow of execution and data logic." if "Flow" in d_type or "Activity" in d_type else "Focus on static structural relationships, entities, and components." if "Class" in d_type or "ER" in d_type or "System" in d_type else "Focus on actors, interactions, and chronological message passing." if "Sequence" in d_type or "Use Case" in d_type else ""
                    schema_req = "\nOUTPUT EXACTLY THIS JSON FORMAT:\n```json\n{\"nodes\": [{\"id\": \"1\", \"label\": \"UI/Client\", \"layer\": 0}, {\"id\": \"2\", \"label\": \"API/Server\", \"layer\": 1}], \"edges\": [{\"from\": \"1\", \"to\": \"2\"}]}\n```\nNote: 'layer' must be 0 (UI/External), 1 (API/Gateway), 2 (Services), or 3 (Database)."
                    prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE structural JSON architecture blueprint tailored specifically for a {d_type}.\n{prompt_details}\nDO NOT just output a generic system architecture. DO NOT GENERATE SVG DIRECTLY.{schema_req}"
                    diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
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
        msg, is_err = self._run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, prompt, "Patch Generation")
        if is_err: return msg, True
        
        # Anti-Hallucination check 1
        hallucinations = self._check_for_hallucinated_imports(msg, workspace_files)
        if hallucinations:
            print(f"--- 🛡️ Nuclear Guard Phase 1: Detected hallucinations: {hallucinations} ---", file=sys.stderr, flush=True)
            # Hard Re-check with "Nuclear" Scolding
            re_prompt = f"🔥 NUCLEAR ERROR: Your patch suggested these NON-EXISTENT modules: {hallucinations}.\n\nSTRICT REQUIREMENT: NO NEW IMPORTS. ONLY USE WHAT IS IN THE PROJECT.\n\nRE-GENERATE NOW WITHOUT THESE MODULES.\n\nOriginal Attempt:\n{msg}"
            msg, is_err = self._run_step_with_rotation(self.factory.create_patch_generator_agent, user_proxy, re_prompt, "Patch Re-generation (Nuclear)")
            if is_err: return msg, True
            
            # Anti-Hallucination check 2 (post re-generation)
            hallucinations = self._check_for_hallucinated_imports(msg, workspace_files)
            if hallucinations:
                print(f"--- 🛡️ Nuclear Guard Phase 2: AI persistent! Stripping: {hallucinations} ---", file=sys.stderr, flush=True)
                # Hard Strip as final safety
                msg = self._strip_hallucinated_imports(msg, hallucinations)
            
        return msg, False

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
        """Extracts file paths and code patches from the agent output with robust path normalization."""
        patches = []
        # Look for #### [FILE] path/to/file.py followed by ```python ... ```
        pattern = r"#### \[FILE\]\s*(.*?)\s*\n.*?```python\n(.*?)\n```"
        matches = re.finditer(pattern, patch_generator_output, re.DOTALL)
        for match in matches:
            # Normalize path and strip leading slashes to prevent os.path.join from breaking on Windows
            rel_path = os.path.normpath(match.group(1).strip()).lstrip("/\\")
            patches.append({
                "path": rel_path,
                "patch_code": match.group(2).strip()
            })
        return patches

    def apply_patches_to_dir(self, patches, base_dir, workspace_files=None):
        """Applies a list of patches to files in the specified directory, creating new files if needed."""
        import os
        results = []
        user_proxy = self.factory.create_user_proxy()
        
        for p in patches:
            rel_path = p["path"]
            full_path = os.path.join(base_dir, rel_path)
            
            # Ensure parent directory exists (critical for new files)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            try:
                original_content = ""
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        original_content = f.read()
                
                # If file is new, we just use the patch code directly or ask applier to form it
                if not original_content:
                    prompt = f"Task: Create a new file at {rel_path} with the following content:\n```python\n{p['patch_code']}\n```"
                else:
                    prompt = f"ORIGINAL CONTENT:\n```python\n{original_content}\n```\n\nPROPOSED PATCH:\n```python\n{p['patch_code']}\n```\n\nTask: Merge them into a complete file."
                
                msg, is_err = self._run_step_with_rotation(self.factory.create_patch_applier_agent, user_proxy, prompt, f"Applying Patch to {rel_path}")
                
                if is_err:
                    results.append({"path": rel_path, "status": f"Error: {msg}"})
                    continue
                
                # Extract code from response
                code_match = re.search(r"```python\n(.*?)\n```", msg, re.DOTALL)
                new_content = code_match.group(1).strip() if code_match else msg.strip()
                
                # 🔥 NUCLEAR GUARD: Post-merge hallucination check
                # Patch Applier might introduce imports from its own training data
                hallucinations = self._check_for_hallucinated_imports(new_content, [rel_path] + (workspace_files or []))
                if hallucinations:
                    logger.warning(f"🛡️ Nuclear Guard: Stripping persistent hallucinations in merge: {hallucinations}")
                    new_content = self._strip_hallucinated_imports(new_content, hallucinations)
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # Validate Syntax
                syntax_ok, syntax_err = self.validate_syntax(new_content, rel_path)
                
                if not syntax_ok:
                    results.append({"path": rel_path, "status": f"Syntax Error: {syntax_err}"})
                else:
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
                prompt_details = "Focus on the step-by-step sequential flow of execution and data logic." if "Flow" in d_type or "Activity" in d_type else "Focus on static structural relationships, entities, and components." if "Class" in d_type or "ER" in d_type or "System" in d_type else "Focus on actors, interactions, and chronological message passing." if "Sequence" in d_type or "Use Case" in d_type else ""
                schema_req = "\nOUTPUT EXACTLY THIS JSON FORMAT:\n```json\n{\"nodes\": [{\"id\": \"1\", \"label\": \"UI/Client\", \"layer\": 0}, {\"id\": \"2\", \"label\": \"API/Server\", \"layer\": 1}], \"edges\": [{\"from\": \"1\", \"to\": \"2\"}]}\n```\nNote: 'layer' must be 0 (UI/External), 1 (API/Gateway), 2 (Services), or 3 (Database)."
                prompt = f"Context:\n{safe_summary}\n\nTask: Generate exactly ONE structural JSON architecture blueprint tailored specifically for a {d_type}.\n{prompt_details}\nDO NOT just output a generic system architecture. DO NOT GENERATE SVG DIRECTLY.{schema_req}"
                diag, is_err = self._run_step_with_rotation(self.factory.create_diagram_generator_agent, user_proxy, prompt, f"{d_type} Diagram")
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
    def execute_command(self, cwd, command, timeout=30):
        """Executes a shell command with a robust timeout that kills the entire process group on Windows."""
        try:
            # On Windows, we need CREATE_NEW_PROCESS_GROUP to kill children reliably
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            process = subprocess.Popen(
                command, 
                cwd=cwd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=creationflags
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                output = f"--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}"
                return output, process.returncode == 0
            except subprocess.TimeoutExpired:
                # Forcefully kill the process tree on Windows
                if os.name == 'nt':
                    # Taskkill /T kills children, /F is force
                    subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
                else:
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                # Try to get whatever was produced before timeout
                stdout, stderr = process.communicate()
                output = f"⚠️ Error: Command timed out after {timeout} seconds.\n\n--- PARTIAL STDOUT ---\n{stdout}\n\n--- PARTIAL STDERR ---\n{stderr}"
                return output, False
        except FileNotFoundError:
            return f"⚠️ Error: Command not found. Is it installed and in your PATH?\nWorking Dir: {cwd}\nCommand: {command}", False
        except Exception as e:
            return f"⚠️ Exception: {str(e)}", False

    def spawn_command(self, cwd, command):
        """Spawns a shell command and returns the Popen process object."""
        try:
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            process = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )
            return process
        except Exception as e:
            logger.error(f"Failed to spawn command: {e}")
            return None

    def kill_process(self, process):
        """Forcefully kills a process and its children using taskkill on Windows."""
        if not process: return
        try:
            if os.name == 'nt':
                subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
            else:
                import signal
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            try: process.kill()
            except: pass

    def suggest_entry_point(self, dir_path):
        """Scans the directory for common entry points to suggest a test command."""
        common_files = ["app.py", "main.py", "run.py", "index.py", "manage.py"]
        search_dirs = [".", "src", "app", "bin"]
        
        # Quote executable path in case it contains spaces
        python_exe = f'"{sys.executable}"'
        
        for d in search_dirs:
            full_d = os.path.join(dir_path, d)
            if not os.path.exists(full_d): continue
            
            for f in common_files:
                target = os.path.join(d, f)
                if os.path.exists(os.path.join(dir_path, target)):
                    return f"{python_exe} {target}"
        
        # Check for tests directory
        if os.path.exists(os.path.join(dir_path, "tests")):
            return f"{python_exe} -m pytest"
            
        return f"{python_exe} --version" # Default fallback
    def _check_for_hallucinated_imports(self, patch_text, workspace_files):
        """Strictly validates imports against stdlib, whitelist, and workspace using AST."""
        debug_path = r"d:\Software_Debugger\DEBUG_GUARD.txt"
        with open(debug_path, "a") as dbg:
            dbg.write(f"\n--- Checking Patch (len={len(patch_text)}) ---\n")
            
        detected = []
        
        # 1. Extract all imports using AST (Much more robust than regex)
        found_imports = []
        try:
            tree = ast.parse(patch_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        found_imports.append(node.module)
        except SyntaxError:
            found_imports = re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)", patch_text, re.MULTILINE)
        
        with open(debug_path, "a") as dbg:
            dbg.write(f"Found Imports: {found_imports}\n")
        
        # 2. Build set of available local modules
        available_modules = set()
        if workspace_files:
            for f in workspace_files:
                if f.endswith(".py"):
                    clean_f = f.replace("/", ".").replace("\\", ".")
                    parts = clean_f.replace(".py", "").split(".")
                    for i in range(1, len(parts) + 1):
                        available_modules.add(".".join(parts[:i]))
        
        std_libs = {
            "os", "sys", "time", "re", "json", "math", "datetime", "subprocess", "threading", 
            "queue", "shutil", "ast", "logging", "collections", "itertools", "functools", 
            "pathlib", "random", "typing", "base64", "hashlib", "io", "inspect", "socket",
            "struct", "tempfile", "traceback", "uuid", "warnings", "xml", "csv", "pickle"
        }
        
        whitelist = {
            "streamlit", "pandas", "numpy", "requests", "PIL", "cv2", "flask", "django", 
            "fastapi", "sqlalchemy", "pydantic", "dotenv", "yaml", "matplotlib", "seaborn",
            "plotly", "scipy", "sklearn", "autogen", "openai", "google", "groq", "dotenv"
        }
        
        for full_imp in found_imports:
            base_imp = full_imp.split(".")[0]
            
            # --- ABSOLUTE BLACKLIST ---
            hallucinated_blacklist = ["ai_copilot", "file_processor", "copilot_utils", "magic_fixer", "auto_patcher"]
            if base_imp in hallucinated_blacklist or "copilot" in base_imp.lower():
                detected.append(full_imp)
                continue

            if base_imp in std_libs or base_imp in whitelist:
                continue
                
            if base_imp in available_modules or full_imp in available_modules:
                continue
            
            detected.append(full_imp)
        
        with open(debug_path, "a") as dbg:
            dbg.write(f"Detected Hallucinations: {detected}\n")
            
        return list(set(detected))

    def _strip_hallucinated_imports(self, content, hallucinations):
        """Forcefully removes lines containing hallucinated imports."""
        debug_path = r"d:\Software_Debugger\DEBUG_GUARD.txt"
        
        # --- EVEN MORE AGGRESSIVE STRIP ---
        # We also check for 'ai_copilot' directly in case detection missed it
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            is_hallucination = False
            
            # 1. Check against the passed list
            if ("import " in line or "from " in line) and any(h in line for h in (hallucinations or [])):
                is_hallucination = True
            
            # 2. Hardcoded fallback check
            hallucinated_blacklist = ["ai_copilot", "file_processor", "copilot_utils", "magic_fixer", "auto_patcher"]
            if ("import " in line or "from " in line) and (any(b in line for b in hallucinated_blacklist) or "copilot" in line.lower()):
                is_hallucination = True
                
            if is_hallucination:
                with open(debug_path, "a") as dbg:
                    dbg.write(f"STRIPPING: {line}\n")
                continue
            new_lines.append(line)
        return "\n".join(new_lines)
