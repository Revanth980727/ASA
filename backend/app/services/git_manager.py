"""
Git Manager - Enhanced git operations with authentication and GitPython.

Features:
- Authenticated cloning (HTTPS with token, SSH)
- Branch management
- Commit operations
- Push to remote
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
import git
from git import Repo, GitCommandError


class GitAuthenticationError(Exception):
    """Raised when git authentication fails."""
    pass


class GitManager:
    """Enhanced git operations with authentication support."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        git_username: Optional[str] = None,
        git_email: Optional[str] = None
    ):
        """
        Initialize Git Manager.

        Args:
            github_token: GitHub personal access token (for HTTPS auth)
            git_username: Git username for commits (default: "ASA Bot")
            git_email: Git email for commits (default: "asa@bot.com")
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.git_username = git_username or os.getenv("GIT_USERNAME", "ASA Bot")
        self.git_email = git_email or os.getenv("GIT_EMAIL", "asa@bot.com")

    def clone_repo(
        self,
        repo_url: str,
        workspace_path: str,
        branch: str = "main",
        depth: Optional[int] = None
    ) -> Repo:
        """
        Clone a git repository with authentication.

        Args:
            repo_url: Repository URL (HTTPS or SSH)
            workspace_path: Local path to clone to
            branch: Branch to checkout (default: main)
            depth: Clone depth for shallow clone (None = full clone)

        Returns:
            GitPython Repo object

        Raises:
            GitAuthenticationError: If authentication fails
            GitCommandError: If clone fails
        """
        # Add token to HTTPS URLs if available
        authenticated_url = self._add_auth_to_url(repo_url)

        workspace = Path(workspace_path)
        workspace.parent.mkdir(parents=True, exist_ok=True)

        print(f"Cloning {repo_url} (branch: {branch}) to {workspace_path}")

        try:
            clone_kwargs = {
                'branch': branch,
            }

            if depth:
                clone_kwargs['depth'] = depth

            repo = Repo.clone_from(
                authenticated_url,
                workspace_path,
                **clone_kwargs
            )

            print(f"✓ Successfully cloned repository")
            return repo

        except GitCommandError as e:
            if "Authentication failed" in str(e) or "authorization failed" in str(e).lower():
                raise GitAuthenticationError(
                    f"Git authentication failed. Ensure GITHUB_TOKEN is set correctly. Error: {e}"
                )
            raise

    def _add_auth_to_url(self, repo_url: str) -> str:
        """Add authentication token to HTTPS URL."""
        if not self.github_token:
            return repo_url

        # Only modify HTTPS URLs
        if not repo_url.startswith('https://'):
            return repo_url

        # Parse URL
        parsed = urlparse(repo_url)

        # Add token to netloc
        if '@' not in parsed.netloc:
            # Format: https://{token}@github.com/user/repo.git
            authenticated_netloc = f"{self.github_token}@{parsed.netloc}"
            authenticated_url = urlunparse((
                parsed.scheme,
                authenticated_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return authenticated_url

        return repo_url

    def create_branch(
        self,
        repo_path: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> None:
        """
        Create and checkout a new branch.

        Args:
            repo_path: Path to git repository
            branch_name: Name of new branch
            base_branch: Branch to create from (None = current branch)
        """
        repo = Repo(repo_path)

        # Checkout base branch if specified
        if base_branch and base_branch != repo.active_branch.name:
            repo.git.checkout(base_branch)

        # Create and checkout new branch
        repo.git.checkout('-b', branch_name)
        print(f"✓ Created and checked out branch: {branch_name}")

    def commit_changes(
        self,
        repo_path: str,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> str:
        """
        Stage all changes and create a commit.

        Args:
            repo_path: Path to git repository
            message: Commit message
            author_name: Override default author name
            author_email: Override default author email

        Returns:
            Commit SHA
        """
        repo = Repo(repo_path)

        # Stage all changes
        repo.git.add('.')

        # Check if there are changes to commit
        if not repo.is_dirty() and not repo.untracked_files:
            print("No changes to commit")
            return ""

        # Configure user if not already set
        with repo.config_writer() as config:
            config.set_value('user', 'name', author_name or self.git_username)
            config.set_value('user', 'email', author_email or self.git_email)

        # Create commit
        commit = repo.index.commit(message)
        print(f"✓ Created commit: {commit.hexsha[:8]}")
        return commit.hexsha

    def push_branch(
        self,
        repo_path: str,
        branch_name: Optional[str] = None,
        remote: str = 'origin',
        force: bool = False
    ) -> None:
        """
        Push branch to remote.

        Args:
            repo_path: Path to git repository
            branch_name: Branch to push (None = current branch)
            remote: Remote name (default: origin)
            force: Force push
        """
        repo = Repo(repo_path)

        if branch_name:
            # Push specific branch
            refspec = f"{branch_name}:{branch_name}"
        else:
            # Push current branch
            refspec = repo.active_branch.name

        # Setup authenticated remote if token available
        if self.github_token and remote == 'origin':
            self._setup_authenticated_remote(repo)

        # Push
        push_kwargs = {}
        if force:
            push_kwargs['force'] = True

        try:
            repo.remotes[remote].push(refspec, **push_kwargs)
            print(f"✓ Pushed {refspec} to {remote}")
        except GitCommandError as e:
            if "authentication failed" in str(e).lower():
                raise GitAuthenticationError(
                    f"Push failed: Authentication error. Ensure GITHUB_TOKEN has push permissions. Error: {e}"
                )
            raise

    def _setup_authenticated_remote(self, repo: Repo) -> None:
        """Setup authenticated URL for origin remote."""
        if not self.github_token:
            return

        try:
            origin = repo.remotes.origin
            url = origin.url

            # Only modify HTTPS URLs
            if url.startswith('https://'):
                authenticated_url = self._add_auth_to_url(url)
                if authenticated_url != url:
                    origin.set_url(authenticated_url)
        except Exception as e:
            print(f"Warning: Could not setup authenticated remote: {e}")

    def get_repo_info(self, repo_path: str) -> dict:
        """
        Get repository information.

        Args:
            repo_path: Path to repository

        Returns:
            Dictionary with repo info
        """
        repo = Repo(repo_path)

        return {
            "active_branch": repo.active_branch.name,
            "is_dirty": repo.is_dirty(),
            "untracked_files": len(repo.untracked_files),
            "remote_url": repo.remotes.origin.url if repo.remotes else None,
            "commits_ahead": self._commits_ahead(repo),
            "last_commit": repo.head.commit.hexsha[:8] if repo.head.commit else None
        }

    def _commits_ahead(self, repo: Repo) -> int:
        """Get number of commits ahead of remote."""
        try:
            # Get tracking branch
            tracking = repo.active_branch.tracking_branch()
            if not tracking:
                return 0

            # Count commits ahead
            commits = list(repo.iter_commits(f'{tracking.name}..HEAD'))
            return len(commits)
        except Exception:
            return 0

    def get_diff_summary(self, repo_path: str) -> str:
        """
        Get a summary of changes in the working directory.

        Args:
            repo_path: Path to repository

        Returns:
            Human-readable diff summary
        """
        repo = Repo(repo_path)

        if not repo.is_dirty() and not repo.untracked_files:
            return "No changes"

        summary_parts = []

        # Modified files
        modified = [item.a_path for item in repo.index.diff(None)]
        if modified:
            summary_parts.append(f"Modified: {', '.join(modified)}")

        # Staged files
        staged = [item.a_path for item in repo.index.diff('HEAD')]
        if staged:
            summary_parts.append(f"Staged: {', '.join(staged)}")

        # Untracked files
        if repo.untracked_files:
            summary_parts.append(f"Untracked: {', '.join(repo.untracked_files[:5])}")
            if len(repo.untracked_files) > 5:
                summary_parts.append(f"... and {len(repo.untracked_files) - 5} more")

        return "\n".join(summary_parts)


def create_fix_branch_and_commit(
    repo_path: str,
    task_id: str,
    commit_message: str,
    github_token: Optional[str] = None
) -> Tuple[str, str]:
    """
    Convenience function: create branch, commit changes, and push.

    Args:
        repo_path: Path to repository
        task_id: Task ID for branch naming
        commit_message: Commit message
        github_token: Optional GitHub token

    Returns:
        Tuple of (branch_name, commit_sha)
    """
    manager = GitManager(github_token=github_token)

    # Create branch
    branch_name = f"asa/fix-{task_id}"
    manager.create_branch(repo_path, branch_name)

    # Commit changes
    commit_sha = manager.commit_changes(repo_path, commit_message)

    # Push to remote (if token available)
    if github_token:
        try:
            manager.push_branch(repo_path, branch_name)
        except GitAuthenticationError as e:
            print(f"Warning: Could not push to remote: {e}")
            print("Branch created locally only")

    return branch_name, commit_sha
