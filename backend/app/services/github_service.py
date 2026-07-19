"""
AutoBug AI — GitHub Service
==============================
GitHub REST API client for branch management, PR creation, and issue linking.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """Wrapper around PyGitHub for AutoBug operations."""

    def __init__(self, token: str | None = None) -> None:
        from github import Github
        self._gh = Github(token or settings.github_token)

    def get_repo(self, full_name: str):
        return self._gh.get_repo(full_name)

    def get_open_issues(self, full_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch open issues from a GitHub repo."""
        repo = self.get_repo(full_name)
        return [
            {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "url": issue.html_url,
                "labels": [lbl.name for lbl in issue.labels],
                "created_at": issue.created_at.isoformat(),
            }
            for issue in repo.get_issues(state="open")[:limit]
        ]

    def create_pr(
        self,
        full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> dict[str, Any]:
        """Open a pull request."""
        repo = self.get_repo(full_name)
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
        )
        return {"url": pr.html_url, "number": pr.number}

    def comment_on_issue(self, full_name: str, issue_number: int, comment: str) -> None:
        """Post a comment on a GitHub issue."""
        repo = self.get_repo(full_name)
        issue = repo.get_issue(issue_number)
        issue.create_comment(comment)

    def get_file_content(self, full_name: str, path: str, ref: str = "main") -> str:
        """Get raw file content from GitHub."""
        repo = self.get_repo(full_name)
        content = repo.get_contents(path, ref=ref)
        return content.decoded_content.decode("utf-8", errors="ignore")

    def get_repo_info(self, full_name: str) -> dict[str, Any]:
        """Get basic repo metadata."""
        repo = self.get_repo(full_name)
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "default_branch": repo.default_branch,
            "languages": dict(repo.get_languages()),
            "stars": repo.stargazers_count,
            "open_issues_count": repo.open_issues_count,
            "url": repo.html_url,
        }
