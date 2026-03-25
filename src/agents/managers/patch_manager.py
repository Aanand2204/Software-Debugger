import os
import re
import ast
from src.config import logger

class PatchManager:
    def __init__(self, runner, factory, guard_manager):
        self.runner = runner
        self.factory = factory
        self.guard_manager = guard_manager

    def parse_patches(self, patch_generator_output):
        """Extracts file paths and code patches from the agent output with robust path normalization."""
        patches = []
        pattern = r"#### \[FILE\]\s*(.*?)\s*\n.*?```python\n(.*?)\n```"
        matches = re.finditer(pattern, patch_generator_output, re.DOTALL)
        for match in matches:
            rel_path = os.path.normpath(match.group(1).strip()).lstrip("/\\")
            patches.append({
                "path": rel_path,
                "patch_code": match.group(2).strip()
            })
        return patches

    def apply_patches_to_dir(self, patches, base_dir, workspace_files=None):
        """Applies a list of patches to files in the specified directory, creating new files if needed."""
        results = []
        user_proxy = self.factory.create_user_proxy()
        
        for p in patches:
            rel_path = p["path"]
            full_path = os.path.join(base_dir, rel_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            try:
                original_content = ""
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        original_content = f.read()
                
                if not original_content:
                    prompt = f"Task: Create a new file at {rel_path} with the following content:\n```python\n{p['patch_code']}\n```"
                else:
                    prompt = f"ORIGINAL CONTENT:\n```python\n{original_content}\n```\n\nPROPOSED PATCH:\n```python\n{p['patch_code']}\n```\n\nTask: Merge them into a complete file."
                
                msg, is_err = self.runner.run_step_with_rotation(self.factory.create_patch_applier_agent, user_proxy, prompt, f"Applying Patch to {rel_path}")
                
                if is_err:
                    results.append({"path": rel_path, "status": f"Error: {msg}"})
                    continue
                
                code_match = re.search(r"```python\n(.*?)\n```", msg, re.DOTALL)
                new_content = code_match.group(1).strip() if code_match else msg.strip()
                
                hallucinations = self.guard_manager.check_for_hallucinated_imports(new_content, [rel_path] + (workspace_files or []))
                if hallucinations:
                    logger.warning(f"🛡️ Nuclear Guard: Stripping persistent hallucinations in merge: {hallucinations}")
                    new_content = self.guard_manager.strip_hallucinated_imports(new_content, hallucinations)
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
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
