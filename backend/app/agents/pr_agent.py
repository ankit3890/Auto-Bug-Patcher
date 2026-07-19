"""
AutoBug AI — PR Agent
=======================
Pushes the branch to GitHub and opens a Pull Request via GitHub API.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.core.config import settings

logger = logging.getLogger(__name__)


async def pr_agent(state: AutoBugState) -> AutoBugState:
    """Push branch and open GitHub PR."""
    logger.info("[PRAgent] Opening Pull Request")
    try:
        import asyncio

        from github import Github

        branch_name = state.get("branch_name", "")
        decision = state.get("decision") or {}
        repo_url = state.get("repo_url", "")
        root_cause = state.get("root_cause", {})
        state.get("patch", {})
        state.get("test_result", {})
        state.get("reviewer_feedback", {})
        state.get("report", "")
        repo_path = state.get("repo_path", "")

        if not decision.get("allow_pr", False):
            logger.warning("[PRAgent] Skipping PR: decision gate did not grant permission")
            return {**state, "pr_url": "", "pr_number": 0, "steps_skipped": [*(state.get("steps_skipped") or []), "pr_agent"]}

        if not branch_name or not state.get("commit_sha") or not settings.github_token:
            logger.warning("[PRAgent] Skipping PR: no branch or no GitHub token")
            return {
                **state,
                "pr_url": "",
                "pr_number": 0,
                "steps_completed": [*(state.get("steps_completed") or []), "pr_agent"],
            }

        # Push branch
        def _push() -> None:
            import git as gitpkg
            repo = gitpkg.Repo(repo_path)
            push_url = repo_url.replace("https://", f"https://x-access-token:{settings.github_token}@")
            repo.remotes.origin.set_url(push_url)
            repo.remotes.origin.push(branch_name)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _push)

        # Parse owner/repo from URL
        parts = repo_url.rstrip("/").replace(".git", "").split("/")
        full_name = f"{parts[-2]}/{parts[-1]}"

        # Open PR via PyGitHub
        def _open_pr():
            gh = Github(settings.github_token)
            gh_repo = gh.get_repo(full_name)
            title = f"fix: {root_cause.get('summary', 'AutoBug fix')}"
            body = _build_pr_body(state)
            pr = gh_repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=gh_repo.default_branch,
            )
            return pr.html_url, pr.number

        pr_url, pr_number = await loop.run_in_executor(None, _open_pr)
        logger.info("[PRAgent] Opened PR #%d: %s", pr_number, pr_url)

        return {
            **state,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "steps_completed": [*(state.get("steps_completed") or []), "pr_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[PRAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "pr_url": "",
            "pr_number": 0,
            "steps_completed": [*(state.get("steps_completed") or []), "pr_agent"],
        }


def _get_detailed_explanation(root_cause: dict) -> str:
    """Format detailed explanation, splitting Facts from Conclusions if present."""
    explanation = root_cause.get("detailed_explanation")
    if explanation:
        return explanation

    observed = root_cause.get("observed_behavior")
    inferred = root_cause.get("inferred_cause")
    if observed or inferred:
        parts = []
        if observed:
            parts.append(f"**Observed Behavior (Facts):**\n{observed}")
        if inferred:
            parts.append(f"**Inferred Cause (Conclusions):**\n{inferred}")
        return "\n\n".join(parts)

    return root_cause.get("summary", "No detailed explanation provided.")


def _build_pr_body(state: AutoBugState) -> str:
    """Generate the PR description markdown."""
    from app.core.confidence import calculate_confidence_matrix
    root_cause = state.get("root_cause") or {}
    patch = state.get("patch") or {}
    test_result = state.get("test_result") or {}
    reviewer = state.get("reviewer_feedback") or {}

    tests_passed = test_result.get("success") or test_result.get("passed", False)
    tests_status_str = "Passed" if tests_passed else "Failed"
    review_status_str = "Approved" if reviewer.get("approved") else "Needs Review"

    explanation = _get_detailed_explanation(root_cause)
    matrix = calculate_confidence_matrix(state)
    confidence = matrix["overall_release_confidence"] * 100

    return f"""## AutoBug AI — Automated Bug Fix

### Root Cause
{explanation}

**Confidence:** {confidence:.0f}%
**Location:** `{root_cause.get("fault_file", "unknown")}` line {root_cause.get("fault_line", "?")}

### Changes
{patch.get("patch_summary", "See diff above")}

### Validation
| Check | Status |
|-------|--------|
| Tests | {tests_status_str} |
| Code Review | {review_status_str} |
| Review Score | {reviewer.get("overall_score", "N/A")}/10 |

### Review Notes
{chr(10).join(f"- {c}" for c in reviewer.get("comments", [])[:5])}

---
*Generated automatically by [AutoBug AI](https://github.com/autobug)*
"""
