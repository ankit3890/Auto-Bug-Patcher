"""
AutoBug AI — Job Service
==========================
Celery tasks for running the LangGraph pipeline asynchronously,
with SSE event emission and Redis state checkpointing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, cast

import redis as sync_redis
from celery import shared_task

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis pub/sub channel naming
# ---------------------------------------------------------------------------

def _sse_channel(issue_id: str) -> str:
    return f"autobug:sse:{issue_id}"


def _job_state_key(job_id: str) -> str:
    return f"autobug:job:{job_id}:state"


# ---------------------------------------------------------------------------
# SSE Event Publisher
# ---------------------------------------------------------------------------

class SSEPublisher:
    """Publishes pipeline progress events to Redis pub/sub."""

    def __init__(self, issue_id: str, job_id: str) -> None:
        self.issue_id = issue_id
        self.job_id = job_id
        self._redis = sync_redis.from_url(settings.redis_url, decode_responses=True)

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an SSE event."""
        payload = json.dumps({
            "event": event_type,
            "job_id": self.job_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        })
        self._redis.publish(_sse_channel(self.issue_id), payload)

    def emit_agent_start(self, agent_name: str, step: int, total: int) -> None:
        self.emit("agent_start", {
            "agent": agent_name,
            "step": step,
            "total": total,
            "progress": int(step / total * 100),
        })

    def emit_agent_complete(self, agent_name: str, step: int, total: int, output_summary: str = "") -> None:
        self.emit("agent_complete", {
            "agent": agent_name,
            "step": step,
            "total": total,
            "progress": int(step / total * 100),
            "summary": output_summary,
        })

    def emit_pipeline_complete(self, result: dict[str, Any]) -> None:
        self.emit("pipeline_complete", {"result": result})

    def emit_pipeline_error(self, error: str, agent: str = "") -> None:
        self.emit("pipeline_error", {"error": error, "failed_agent": agent})


# ---------------------------------------------------------------------------
# Celery Task
# ---------------------------------------------------------------------------

@shared_task(name="autobug.run_pipeline", bind=True, max_retries=1, queue="autobug")
def run_autobug_pipeline(self, issue_id: str, job_id: str) -> dict[str, Any]:
    """
    Main Celery task: run the full AutoBug AI pipeline for a given issue.
    Updates job status in DB and publishes SSE events throughout.
    """
    return asyncio.run(_run_pipeline_async(issue_id, job_id, self))


async def _run_pipeline_async(issue_id: str, job_id: str, task: Any) -> dict[str, Any]:
    """Async pipeline runner — runs in a new event loop inside Celery worker."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.agents.graph import get_compiled_graph
    from app.agents.state import AutoBugState
    from app.models.issue import Issue, IssueStatus
    from app.models.job import Job, JobStatus
    from app.models.patch import Patch, PatchStatus

    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    publisher = SSEPublisher(issue_id, job_id)
    TOTAL_STEPS = 22

    async with Session() as db:
        # Load issue with repository loaded eagerly to prevent MissingGreenlet lazy-loading error
        stmt = select(Issue).options(selectinload(Issue.repository)).where(Issue.id == issue_id)
        issue = (await db.execute(stmt)).scalar_one_or_none()
        if not issue:
            logger.error("Issue %s not found", issue_id)
            return {"error": "Issue not found"}

        job = await db.get(Job, job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return {"error": "Job not found"}

        # Mark job as running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        await db.commit()

        # Build initial state
        initial_state: AutoBugState = {
            "repo_url": issue.repository.github_url if issue.repository else "",
            "issue_text": issue.description,
            "issue_id": issue_id,
            "job_id": job_id,
            "repo_id": issue.repository_id,
            "steps_completed": [],
        }

        try:
            graph = get_compiled_graph()
            step_count = 0

            AGENT_ORDER = [
                "repository_agent",
                "environment_agent",
                "environment_validator_agent",
                "issue_agent",
                "planner_agent",
                "retrieval_agent",
                "build_agent",
                "reproduction_agent",
                "localization_agent",
                "root_cause_agent",
                "patch_agent",
                "static_analysis_agent",
                "test_generator_agent",
                "test_runner_agent",
                "reviewer_agent",
                "risk_agent",
                "performance_agent",
                "decision_engine",
                "git_agent",
                "pr_agent",
                "consistency_checker",
                "report_agent",
            ]

            # Wrap with progress tracking
            async def _step_callback(agent_name: str, state_update: dict[str, Any]) -> None:
                nonlocal step_count
                step_count += 1
                
                summary = ""
                if agent_name == "repository_agent":
                    summary = "Cloned repository files"
                elif agent_name == "environment_agent":
                    summary = "Detected runtime requirements"
                elif agent_name == "environment_validator_agent":
                    env_res = state_update.get("environment_result") or {}
                    summary = "Verified sandbox tools" if env_res.get("ready") else "Failed environment validation"
                elif agent_name == "issue_agent":
                    summary = f"Parsed error type: {state_update.get('issue_structured', {}).get('error_type', 'Unknown')}"
                elif agent_name == "planner_agent":
                    summary = "Generated search queries"
                elif agent_name == "retrieval_agent":
                    summary = f"Retrieved {len(state_update.get('retrieved_chunks', []))} RAG context chunks"
                elif agent_name == "localization_agent":
                    summary = f"Localized fault to: {', '.join(state_update.get('fault_files', []))}"
                elif agent_name == "root_cause_agent":
                    summary = state_update.get("root_cause", {}).get("summary", "")
                elif agent_name == "patch_agent":
                    summary = state_update.get("patch", {}).get("patch_summary", "")
                elif agent_name == "static_analysis_agent":
                    sa_res = state_update.get("static_analysis_result") or {}
                    summary = "Passed static validation" if sa_res.get("passed") else "Failed static validation"
                elif agent_name == "test_generator_agent":
                    summary = "Generated test files"
                elif agent_name == "test_validator_agent":
                    val_res = state_update.get("test_validation_result") or {}
                    summary = "Regression tests valid" if val_res.get("valid") else "Regression tests invalid"
                elif agent_name == "test_runner_agent":
                    tr = state_update.get("test_result") or {}
                    summary = "Tests passed" if tr.get("passed") else "Tests failed"
                elif agent_name == "reviewer_agent":
                    rev = state_update.get("reviewer_feedback") or {}
                    summary = f"Approved score: {rev.get('overall_score', 0)}/10"
                elif agent_name == "risk_agent":
                    risk_res = state_update.get("risk_analysis") or {}
                    summary = f"Regression risk: {int(risk_res.get('regression_risk', 0.0) * 100)}%"
                elif agent_name == "performance_agent":
                    summary = "Estimated latency and computational complexity"
                elif agent_name == "decision_engine":
                    dec_res = state_update.get("decision") or {}
                    summary = f"Decision: {dec_res.get('decision', 'Needs Review')}"
                elif agent_name == "git_agent":
                    summary = "Committed fix branch"
                elif agent_name == "pr_agent":
                    summary = f"Created PR: {state_update.get('pr_url', 'Skipped')}"
                elif agent_name == "consistency_checker":
                    summary = "Validated pipeline constraints"
                
                publisher.emit_agent_complete(agent_name, step_count, TOTAL_STEPS, summary)
                
                # Update job in DB
                async with Session() as s:
                    j = await s.get(Job, job_id)
                    if j:
                        j.current_agent = None
                        j.completed_agents = [*(j.completed_agents or []), agent_name]
                        j.progress_percent = step_count / TOTAL_STEPS * 100
                        await s.commit()

            # Run graph and stream updates in real-time
            final_state: dict[str, Any] = dict(initial_state)
            
            # Emit starting event for the entry node
            publisher.emit_agent_start("repository_agent", 1, TOTAL_STEPS)
            
            async for output in graph.astream(initial_state, stream_mode="updates"):
                if not output:
                    continue
                # Get completed node name and state updates
                agent_name = list(output.keys())[0]
                state_update = cast(dict[str, Any], output[agent_name])
                final_state = {**final_state, **state_update}
                
                # Process the completed step
                await _step_callback(agent_name, state_update)
                
                # Emit start event for the next scheduled agent
                try:
                    curr_idx = AGENT_ORDER.index(agent_name)
                    if curr_idx + 1 < len(AGENT_ORDER):
                        next_agent = AGENT_ORDER[curr_idx + 1]
                        publisher.emit_agent_start(next_agent, step_count + 1, TOTAL_STEPS)
                except ValueError:
                    pass

            # Process results
            root_cause = cast(dict[str, Any], final_state.get("root_cause") or {})
            patch_data = cast(dict[str, Any], final_state.get("patch") or {})
            test_result = cast(dict[str, Any], final_state.get("test_result") or {})
            steps_done = cast(list[str], final_state.get("steps_completed") or [])
            generated_tests = cast(dict[str, Any], final_state.get("generated_tests") or {})

            # Save patch to DB
            if patch_data.get("unified_diff"):
                patch = Patch(
                    issue_id=issue_id,
                    unified_diff=patch_data.get("unified_diff"),
                    modified_files=patch_data.get("modified_files"),
                    patch_summary=patch_data.get("patch_summary"),
                    root_cause=root_cause.get("summary"),
                    fault_location=(
                        f"{root_cause.get('fault_file')}:{root_cause.get('fault_line', '')}"
                        if root_cause.get("fault_file") else None
                    ),
                    confidence_score=root_cause.get("confidence"),
                    tests_passed=test_result.get("passed"),
                    test_results=test_result,
                    reviewer_feedback=str(final_state.get("reviewer_feedback") or {}),
                    regression_test=generated_tests.get("test_code"),
                    regression_test_file=generated_tests.get("test_file"),
                    status=PatchStatus.VALIDATED if test_result.get("passed") else PatchStatus.GENERATED,
                )
                db.add(patch)

            # Update job as completed
            job = await db.get(Job, job_id)
            if job is None:
                raise RuntimeError(f"Job {job_id} disappeared before completion update")
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.progress_percent = 100.0
            job.completed_agents = steps_done
            job.current_agent = None
            job.root_cause_summary = root_cause.get("summary")
            job.confidence_score = root_cause.get("confidence")
            
            # Determine failure classification
            failure_class = final_state.get("failure_classification")
            if not failure_class:
                test_val = final_state.get("test_validation_result") or {}
                failure_class = test_val.get("failure_classification")
            if not failure_class:
                failed_agent = final_state.get("failed_agent")
                if failed_agent == "environment_validator_agent":
                    failure_class = "ENVIRONMENT"
                elif failed_agent == "build_agent":
                    failure_class = "BUILD"
                elif failed_agent == "test_runner_agent":
                    test_res = final_state.get("test_result") or {}
                    out = (test_res.get("stdout") or "") + (test_res.get("stderr") or "")
                    if "ModuleNotFoundError" in out or "ImportError" in out:
                        failure_class = "TEST_COLLECTION"
                    else:
                        failure_class = "TEST_FAILURE"
                elif failed_agent == "consistency_checker":
                    failure_class = "VALIDATION"
                elif failed_agent:
                    failure_class = "PIPELINE"
                else:
                    failure_class = "APPLICATION"
            job.failure_classification = failure_class

            job.agent_outputs = {
                "root_cause": root_cause,
                "pr_url": final_state.get("pr_url"),
                "report": final_state.get("report", "")[:10000],
            }
            if issue is not None:
                issue.status = IssueStatus.COMPLETED
            await db.commit()

            publisher.emit_pipeline_complete({
                "steps": steps_done,
                "pr_url": final_state.get("pr_url"),
                "root_cause": root_cause.get("summary"),
            })

            return {"status": "completed", "issue_id": issue_id, "job_id": job_id}

        except Exception as exc:
            logger.error("Pipeline failed for issue %s: %s", issue_id, exc, exc_info=True)
            job = await db.get(Job, job_id)
            if job:
                from app.models.job import JobStatus
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.now(UTC)
                job.failure_classification = "PIPELINE"
                if issue is not None:
                    issue.status = IssueStatus.FAILED
            await db.commit()

            publisher.emit_pipeline_error(str(exc))
            return {"status": "failed", "error": str(exc)}

        finally:
            try:
                from app.sandbox.manager import SandboxManager
                manager = SandboxManager()
                await manager.cleanup_job_sandbox(job_id)
            except Exception as e:
                logger.warning("Failed to clean up persistent sandbox container for job %s: %s", job_id, e)

    await engine.dispose()
    return {"status": "failed", "error": "Pipeline exited without a terminal result"}
