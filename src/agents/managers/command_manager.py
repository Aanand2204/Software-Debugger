import os
import sys
import subprocess
from src.config import logger

class CommandManager:
    @staticmethod
    def execute_command(cwd, command, timeout=30):
        """Executes a shell command with a robust timeout that kills the entire process group on Windows."""
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
                creationflags=creationflags
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                output = f"--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}"
                return output, process.returncode == 0
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
                else:
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
                stdout, stderr = process.communicate()
                output = f"⚠️ Error: Command timed out after {timeout} seconds.\n\n--- PARTIAL STDOUT ---\n{stdout}\n\n--- PARTIAL STDERR ---\n{stderr}"
                return output, False
        except FileNotFoundError:
            return f"⚠️ Error: Command not found. Is it installed and in your PATH?\nWorking Dir: {cwd}\nCommand: {command}", False
        except Exception as e:
            return f"⚠️ Exception: {str(e)}", False

    @staticmethod
    def spawn_command(cwd, command):
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

    @staticmethod
    def kill_process(process):
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

    @staticmethod
    def suggest_entry_point(dir_path):
        """Scans the directory for common entry points to suggest a test command."""
        common_files = ["app.py", "main.py", "run.py", "index.py", "manage.py"]
        search_dirs = [".", "src", "app", "bin"]
        
        python_exe = f'"{sys.executable}"'
        
        for d in search_dirs:
            full_d = os.path.join(dir_path, d)
            if not os.path.exists(full_d): continue
            
            for f in common_files:
                target = os.path.join(d, f)
                if os.path.exists(os.path.join(dir_path, target)):
                    return f"{python_exe} {target}"
        
        if os.path.exists(os.path.join(dir_path, "tests")):
            return f"{python_exe} -m pytest"
            
        return f"{python_exe} --version"
