import os
import shutil
from git import Repo
from src.config import logger

class GitHubUtils:
    @staticmethod
    def clone_repository(repo_url, target_dir):
        """Clones a GitHub repository to a local directory."""
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            Repo.clone_from(repo_url, target_dir)
            logger.info(f"Repository cloned successfully to {target_dir}")
            return True
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False

    @staticmethod
    def list_files(directory, extensions=None):
        """Lists files in a directory, optionally filtered by extensions."""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.html', '.css']
        
        file_list = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_list.append(os.path.join(root, file))
        return file_list

    @staticmethod
    def read_file_content(file_path):
        """Reads the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
