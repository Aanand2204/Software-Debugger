import os
import sys
from src.config import logger

class WorkspaceUtils:
    @staticmethod
    def list_files(directory, extensions=None, ignore_dirs=None):
        """Lists files in a directory, optionally filtered by extensions and ignoring specific directories."""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.html', '.css', '.md', '.json']
        if ignore_dirs is None:
            ignore_dirs = ['node_modules', '.git', '__pycache__', 'venv', '.vscode', 'out', 'build', 'dist', '.next', '.venv', 'env']
        
        file_list = []
        print(f"--- Crawling directory: {os.path.basename(directory)} ---", file=sys.stderr, flush=True)
        for root, dirs, files in os.walk(directory):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    file_list.append(full_path)
                    if len(file_list) >= 100: # Practical limit for summary
                        return file_list
        return file_list

    @staticmethod
    def read_file_content(file_path):
        """Reads the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    @staticmethod
    def get_workspace_summary(directory, max_files=15):
        """Generates a summary of the workspace content."""
        print("--- Building Workspace Summary ---", file=sys.stderr, flush=True)
        files = WorkspaceUtils.list_files(directory)
        summary = ""
        for file_path in files[:max_files]:
            content = WorkspaceUtils.read_file_content(file_path)
            if content:
                rel_path = os.path.relpath(file_path, directory)
                summary += f"--- Path: {rel_path} ---\n{content[:1500]}\n\n"
        return summary
