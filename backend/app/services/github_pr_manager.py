"""
GitHub PR Manager - Create pull requests with templates and test results.

Features:
- GitHub API integration
- PR templates with test results
- Automated changelog generation
- Label and reviewer assignment
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from github import Github, GithubException
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.services.run_report import generate_pr_body_for_task


class GitHubPRManager:
    """Manage GitHub pull requests via API."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub PR Manager.

        Args:
            github_token: GitHub personal access token
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable.")

        self.github = Github(self.github_token)

    def create_pull_request(
        self,
        repo_url: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a pull request.

        Args:
            repo_url: Repository URL (e.g., https://github.com/user/repo)
            head_branch: Source branch (your changes)
            base_branch: Target branch (e.g., main)
            title: PR title
            body: PR description (markdown)
            labels: Optional list of label names
            assignees: Optional list of GitHub usernames to assign
            reviewers: Optional list of GitHub usernames to request review from

        Returns:
            Dictionary with PR information:
            {
                "number": PR number,
                "url": PR URL,
                "html_url": PR HTML URL,
                "state": "open",
                "created_at": timestamp
            }
        """
        # Parse repo from URL
        owner, repo_name = self._parse_repo_url(repo_url)

        # Get repository
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
        except GithubException as e:
            raise ValueError(f"Failed to access repository {owner}/{repo_name}: {e}")

        # Create PR
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )

            print(f"✓ Created PR #{pr.number}: {pr.html_url}")

            # Add labels
            if labels:
                pr.add_to_labels(*labels)
                print(f"✓ Added labels: {', '.join(labels)}")

            # Add assignees
            if assignees:
                pr.add_to_assignees(*assignees)
                print(f"✓ Assigned to: {', '.join(assignees)}")

            # Request reviewers
            if reviewers:
                pr.create_review_request(reviewers=reviewers)
                print(f"✓ Requested review from: {', '.join(reviewers)}")

            return {
                "number": pr.number,
                "url": pr.url,
                "html_url": pr.html_url,
                "state": pr.state,
                "created_at": pr.created_at.isoformat()
            }

        except GithubException as e:
            raise ValueError(f"Failed to create PR: {e}")

    def create_fix_pr(
        self,
        repo_url: str,
        head_branch: str,
        base_branch: str,
        task_id: str,
        db: Session,
        bug_description: Optional[str] = None,
        fix_summary: Optional[str] = None,
        test_results_before: Optional[str] = None,
        test_results_after: Optional[str] = None,
        patches_applied: Optional[List[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a PR for a bug fix with comprehensive template from RunReport.

        Args:
            repo_url: Repository URL
            head_branch: Source branch
            base_branch: Target branch
            task_id: Task ID for RunReport generation
            db: Database session
            bug_description: Original bug description (legacy, falls back if no task)
            fix_summary: Summary of the fix (legacy)
            test_results_before: Test output before fix (legacy)
            test_results_after: Test output after fix (legacy)
            patches_applied: List of patches applied (legacy)
            confidence_score: AI confidence score (legacy)

        Returns:
            PR information dictionary
        """
        # Generate PR body using RunReport (uses the comprehensive template)
        try:
            body = generate_pr_body_for_task(task_id, db)
            # Extract title from bug_description in task
            from app.models import Task
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.bug_description:
                title = self._generate_pr_title(task.bug_description)
            else:
                title = self._generate_pr_title(bug_description or "Automated bug fix")
        except Exception as e:
            # Fallback to legacy method if RunReport fails
            print(f"⚠️ RunReport generation failed, using legacy method: {e}")
            title = self._generate_pr_title(bug_description or "Automated bug fix")
            body = self._generate_pr_body(
                bug_description=bug_description or "Bug fix",
                fix_summary=fix_summary or "Automated fix",
                test_results_before=test_results_before,
                test_results_after=test_results_after,
                patches_applied=patches_applied,
                confidence_score=confidence_score
            )

        return self.create_pull_request(
            repo_url=repo_url,
            head_branch=head_branch,
            base_branch=base_branch,
            title=title,
            body=body,
            labels=["bug", "automated-fix", "asa-bot"]
        )

    def _generate_pr_title(self, bug_description: str) -> str:
        """Generate PR title from bug description."""
        # Truncate and clean
        title = bug_description.strip()
        if len(title) > 72:
            title = title[:69] + "..."

        return f"🤖 Fix: {title}"

    def _generate_pr_body(
        self,
        bug_description: str,
        fix_summary: str,
        test_results_before: Optional[str],
        test_results_after: Optional[str],
        patches_applied: Optional[List[Dict[str, Any]]],
        confidence_score: Optional[float]
    ) -> str:
        """Generate comprehensive PR description."""
        sections = []

        # Header
        sections.append("## 🤖 Automated Fix by ASA")
        sections.append("")
        sections.append("This pull request was automatically generated by the ASA (Automated Software Agent) system.")
        sections.append("")

        # Bug description
        sections.append("## 🐛 Bug Description")
        sections.append("")
        sections.append(bug_description)
        sections.append("")

        # Fix summary
        sections.append("## 🔧 Fix Summary")
        sections.append("")
        sections.append(fix_summary)
        sections.append("")

        # Patches applied
        if patches_applied:
            sections.append("## 📝 Changes Made")
            sections.append("")
            for i, patch in enumerate(patches_applied, 1):
                sections.append(f"### {i}. {patch.get('description', 'Code patch')}")
                sections.append(f"- **File**: `{patch.get('file_path', 'unknown')}`")
                sections.append(f"- **Lines**: {patch.get('start_line', '?')}-{patch.get('end_line', '?')}")
                sections.append(f"- **Type**: {patch.get('patch_type', 'replace')}")
                sections.append("")

        # Confidence score
        if confidence_score is not None:
            sections.append("## 📊 Confidence Score")
            sections.append("")
            confidence_pct = confidence_score * 100
            confidence_bar = "█" * int(confidence_pct / 10)
            sections.append(f"**{confidence_pct:.1f}%** `{confidence_bar}`")
            sections.append("")

        # Test results
        sections.append("## ✅ Test Results")
        sections.append("")

        if test_results_before:
            sections.append("### Before Fix")
            sections.append("```")
            sections.append(test_results_before[-500:])  # Last 500 chars
            sections.append("```")
            sections.append("")

        if test_results_after:
            sections.append("### After Fix")
            sections.append("```")
            sections.append(test_results_after[-500:])
            sections.append("```")
            sections.append("")

        # Checklist
        sections.append("## ✓ Review Checklist")
        sections.append("")
        sections.append("- [ ] Code changes are minimal and focused")
        sections.append("- [ ] All tests pass")
        sections.append("- [ ] No unintended side effects")
        sections.append("- [ ] Code follows project style guidelines")
        sections.append("- [ ] Documentation updated (if needed)")
        sections.append("")

        # Footer
        sections.append("---")
        sections.append("")
        sections.append("🤖 *Generated by [ASA](https://github.com/your-org/asa) - Automated Software Agent*")
        sections.append(f"📅 *Created on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*")

        return "\n".join(sections)

    def _parse_repo_url(self, repo_url: str) -> tuple:
        """
        Parse repository owner and name from URL.

        Args:
            repo_url: Repository URL

        Returns:
            Tuple of (owner, repo_name)
        """
        # Handle various URL formats:
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git

        if repo_url.startswith('git@'):
            # SSH format
            parts = repo_url.replace('git@github.com:', '').replace('.git', '').split('/')
        else:
            # HTTPS format
            parsed = urlparse(repo_url)
            parts = parsed.path.strip('/').replace('.git', '').split('/')

        if len(parts) != 2:
            raise ValueError(f"Invalid repository URL: {repo_url}")

        owner, repo_name = parts
        return owner, repo_name

    def add_comment(self, repo_url: str, pr_number: int, comment: str) -> None:
        """
        Add a comment to a pull request.

        Args:
            repo_url: Repository URL
            pr_number: PR number
            comment: Comment text (markdown)
        """
        owner, repo_name = self._parse_repo_url(repo_url)
        repo = self.github.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(comment)
        print(f"✓ Added comment to PR #{pr_number}")

    def update_pr_status(
        self,
        repo_url: str,
        pr_number: int,
        status: str,
        message: str
    ) -> None:
        """
        Update PR with status message.

        Args:
            repo_url: Repository URL
            pr_number: PR number
            status: Status emoji/label (e.g., "✅", "❌", "⚠️")
            message: Status message
        """
        comment = f"{status} **Update**: {message}"
        self.add_comment(repo_url, pr_number, comment)


def create_automated_pr(
    repo_url: str,
    branch_name: str,
    task_id: str,
    db: Session,
    bug_description: Optional[str] = None,
    patch_set: Optional[Any] = None,
    test_results_before: Optional[str] = None,
    test_results_after: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function: Create PR with all ASA context using RunReport.

    Args:
        repo_url: Repository URL
        branch_name: Branch with fixes
        task_id: ASA task ID (required for RunReport)
        db: Database session (required for RunReport)
        bug_description: Bug description (legacy, optional)
        patch_set: PatchSet object with fixes (legacy, optional)
        test_results_before: Test output before fix (legacy, optional)
        test_results_after: Test output after fix (legacy, optional)
        github_token: Optional GitHub token

    Returns:
        PR information dictionary
    """
    manager = GitHubPRManager(github_token=github_token)

    # Extract patch information if provided (legacy)
    patches_info = None
    if patch_set and hasattr(patch_set, 'patches'):
        patches_info = [
            {
                "file_path": p.file_path,
                "start_line": p.start_line,
                "end_line": p.end_line,
                "patch_type": p.patch_type.value,
                "description": p.description
            }
            for p in patch_set.patches
        ]

    # Create PR using RunReport
    pr_info = manager.create_fix_pr(
        repo_url=repo_url,
        head_branch=branch_name,
        base_branch="main",  # TODO: Make configurable
        task_id=task_id,
        db=db,
        bug_description=bug_description,
        fix_summary=patch_set.rationale if patch_set and hasattr(patch_set, 'rationale') else None,
        test_results_before=test_results_before,
        test_results_after=test_results_after,
        patches_applied=patches_info,
        confidence_score=patch_set.confidence if patch_set and hasattr(patch_set, 'confidence') else None
    )

    return pr_info
