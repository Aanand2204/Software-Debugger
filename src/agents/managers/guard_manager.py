import ast
import re
from src.config import logger

class GuardManager:
    def check_for_hallucinated_imports(self, patch_text, workspace_files):
        """Strictly validates imports against stdlib, whitelist, and workspace using AST."""
        logger.debug(f"--- Checking Patch (len={len(patch_text)}) ---")
            
        detected = []
        
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
        
        logger.debug(f"Found Imports: {found_imports}")
        
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
            
            hallucinated_blacklist = ["ai_copilot", "file_processor", "copilot_utils", "magic_fixer", "auto_patcher"]
            if base_imp in hallucinated_blacklist or "copilot" in base_imp.lower():
                detected.append(full_imp)
                continue

            if base_imp in std_libs or base_imp in whitelist:
                continue
                
            if base_imp in available_modules or full_imp in available_modules:
                continue
            
            detected.append(full_imp)
        
        if detected:
            logger.warning(f"Detected Hallucinations: {detected}")
            
        return list(set(detected))

    def strip_hallucinated_imports(self, content, hallucinations):
        """Forcefully removes lines containing hallucinated imports."""
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            is_hallucination = False
            
            if ("import " in line or "from " in line) and any(h in line for h in (hallucinations or [])):
                is_hallucination = True
            
            hallucinated_blacklist = ["ai_copilot", "file_processor", "copilot_utils", "magic_fixer", "auto_patcher"]
            if ("import " in line or "from " in line) and (any(b in line for b in hallucinated_blacklist) or "copilot" in line.lower()):
                is_hallucination = True
                
            if is_hallucination:
                logger.debug(f"STRIPPING NULLIFIED IMPORT: {line}")
                continue
            new_lines.append(line)
        return "\n".join(new_lines)
