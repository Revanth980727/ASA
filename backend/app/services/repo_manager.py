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

def create_fix_branch(workspace_path: str, task_id: str) -> str:
    """
    Creates a new git branch for the fix.

    Args:
        workspace_path: Path to the git repository
        task_id: Task ID to include in branch name

    Returns:
        The branch name created (e.g., "asa/fix-{task_id}")
    """
    branch_name = f"asa/fix-{task_id}"

    try:
        # Create and checkout new branch
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Created and checked out branch: {branch_name}")
        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Failed to create branch: {e.stderr}")
        raise Exception(f"Failed to create branch: {e.stderr}")

def commit_changes(workspace_path: str, task_id: str, message: str = None) -> None:
    """
    Stages all changes and commits them.

    Args:
        workspace_path: Path to the git repository
        task_id: Task ID for the commit message
        message: Optional custom commit message
    """
    commit_msg = message or f"ASA fix for task {task_id}"

    try:
        # Stage all changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True
        )

        # Commit changes
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Committed changes: {commit_msg}")
    except subprocess.CalledProcessError as e:
        # Check if there are no changes to commit
        if "nothing to commit" in e.stderr or "nothing to commit" in e.stdout:
            print("No changes to commit")
            return
        print(f"Failed to commit changes: {e.stderr}")
        raise Exception(f"Failed to commit changes: {e.stderr}")

def push_branch(workspace_path: str, branch_name: str, remote: str = "origin") -> None:
    """
    Pushes the branch to remote repository.

    Args:
        workspace_path: Path to the git repository
        branch_name: Name of the branch to push
        remote: Remote name (default: "origin")
    """
    try:
        subprocess.run(
            ['git', 'push', '-u', remote, branch_name],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Pushed branch {branch_name} to {remote}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to push branch: {e.stderr}")
        raise Exception(f"Failed to push branch: {e.stderr}")

def create_pr_branch_local(workspace_path: str, task_id: str, push_to_remote: bool = False) -> str:
    """
    Complete workflow: create branch, commit changes, and optionally push.

    Args:
        workspace_path: Path to the git repository
        task_id: Task ID
        push_to_remote: Whether to push to remote (default: False for v0.1)

    Returns:
        The branch name created
    """
    # Create branch
    branch_name = create_fix_branch(workspace_path, task_id)

    # Commit changes
    commit_changes(workspace_path, task_id)

    # Optionally push to remote
    if push_to_remote:
        try:
            push_branch(workspace_path, branch_name)
        except Exception as e:
            # Don't fail the whole process if push fails (might not have remote access)
            print(f"Warning: Could not push to remote: {e}")

    return branch_name