import os
import subprocess
from pathlib import Path

def create_workspace(task_id: str, base_dir: str = "workspaces") -> str:
    """
    Creates the base directory if needed and a subdirectory for the task.
    Returns the absolute path to the task's workspace directory.
    """
    path = Path(base_dir) / task_id
    path.mkdir(parents=True, exist_ok=True)
    return str(path.absolute())

def clone_repo(repo_url: str, workspace_path: str, branch: str = "main") -> None:
    """
    Clones the repository into the specified workspace path.
    Uses subprocess for git operations with basic error handling.
    Logs simple messages.
    """
    print(f"Cloning started for {repo_url} into {workspace_path}")
    try:
        result = subprocess.run(
            ['git', 'clone', '-b', branch, repo_url, workspace_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("Cloning finished")
    except subprocess.CalledProcessError as e:
        print(f"Cloning failed: {e.stderr}")
        raise Exception(f"Failed to clone repo: {e.stderr}")