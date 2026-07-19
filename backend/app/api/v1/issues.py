"""
AutoBug AI — Issues API (with SSE streaming)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.issue import Issue, IssueStatus
from app.models.job import Job, JobStatus
from app.schemas.issue import IssueCreate, IssueResponse
from app.schemas.job import JobResponse

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("", response_model=dict, status_code=201)
async def submit_issue(
    payload: IssueCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit a bug report and trigger the AutoBug pipeline."""
    issue = Issue(
        id=str(uuid.uuid4()),
        repository_id=payload.repository_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,  # type: ignore
        status=IssueStatus.PENDING,
        github_issue_url=payload.github_issue_url,
        github_issue_number=payload.github_issue_number,
    )
    db.add(issue)

    job = Job(
        id=str(uuid.uuid4()),
        issue_id=issue.id,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()

    # Dispatch Celery task
    try:
        from app.core.celery_app import celery_app  # Initialize Celery app context
        from app.services.job_service import run_autobug_pipeline
        celery_result = run_autobug_pipeline.apply_async(
            args=[issue.id, job.id],
            queue="autobug",
        )
        job.celery_task_id = celery_result.id
        issue.status = IssueStatus.ANALYZING
        await db.commit()
    except Exception as e:
        import logging
        import traceback
        logging.getLogger(__name__).warning(
            "Failed to dispatch Celery task to worker: %s. Falling back to FastAPI BackgroundTask...", e
        )
        
        async def run_pipeline_fallback(issue_id: str, job_id: str):
            from app.services.job_service import _run_pipeline_async
            
            class DummyTask:
                def update_state(self, *args, **kwargs):
                    pass
            try:
                await _run_pipeline_async(issue_id, job_id, DummyTask())
            except Exception as fb_e:
                logging.getLogger(__name__).error(
                    "Fallback pipeline execution failed: %s\n%s", fb_e, traceback.format_exc()
                )
                
        issue.status = IssueStatus.ANALYZING
        await db.commit()
        background_tasks.add_task(run_pipeline_fallback, issue.id, job.id)

    return {"issue_id": issue.id, "job_id": job.id, "status": "queued"}


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: str, db: AsyncSession = Depends(get_db)):
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    repository_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Issue).order_by(Issue.created_at.desc())
    if repository_id:
        q = q.where(Issue.repository_id == repository_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{issue_id}/job", response_model=JobResponse)
async def get_issue_job(issue_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).where(Job.issue_id == issue_id).order_by(Job.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No job found for this issue")
    return job


@router.get("/{issue_id}/stream")
async def stream_issue_progress(issue_id: str):
    """
    SSE endpoint — streams live agent progress events.
    Subscribe to the Redis pub/sub channel for this issue.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        channel = f"autobug:sse:{issue_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Send initial connected event
        yield f"data: {json.dumps({'event': 'connected', 'issue_id': issue_id})}\n\n"

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    yield f"data: {data}\n\n"

                    # Check if pipeline completed/errored
                    try:
                        parsed = json.loads(data)
                        if parsed.get("event") in ("pipeline_complete", "pipeline_error"):
                            break
                    except Exception:
                        pass

                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(issue_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an issue and all its pipeline executions."""
    from sqlalchemy import delete
    from app.models.job import Job
    from app.models.patch import Patch
    from app.models.pull_request import PullRequest

    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Delete related jobs, patches, and pull requests
    await db.execute(delete(PullRequest).where(PullRequest.issue_id == issue_id))
    await db.execute(delete(Patch).where(Patch.issue_id == issue_id))
    await db.execute(delete(Job).where(Job.issue_id == issue_id))

    await db.delete(issue)
    await db.commit()
    return Response(status_code=204)


@router.post("/{issue_id}/chat", response_model=dict)
async def chat_about_report(
    issue_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """Chat with AutoBug AI over the generated report and code patch."""
    import asyncio
    from app.models.patch import Patch
    
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Fetch latest job outputs and patch
    job_result = await db.execute(
        select(Job).where(Job.issue_id == issue_id).order_by(Job.created_at.desc())
    )
    job = job_result.scalar_one_or_none()

    patch_result = await db.execute(
        select(Patch).where(Patch.issue_id == issue_id).order_by(Patch.created_at.desc())
    )
    patch = patch_result.scalar_one_or_none()

    report = job.agent_outputs.get("report", "") if job and job.agent_outputs else ""
    diff = patch.unified_diff if patch else ""

    # Construct chat messages context
    system_prompt = (
        "You are AutoBug AI assistant. You help the user refine and understand the generated bug fix report and code patch.\n"
        "Here is the context about the bug and generated fix:\n\n"
        f"Bug Title: {issue.title}\n"
        f"Bug Description:\n{issue.description}\n\n"
        f"Generated Report:\n{report}\n\n"
        f"Current Unified Code Patch:\n{diff}\n\n"
        "Respond to the user's questions contextually and help them refine the fix. Keep the conversation constructive and focused on the bug and the patch code."
    )

    # Use the active configured LLM
    from app.agents.issue_agent import _get_llm
    try:
        llm = _get_llm("report_chat")
    except Exception:
        # Fallback to OpenAI if key retrieval fails
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    # Add history
    for msg in payload.get("history", []):
        messages.append({"role": "user" if msg["role"] == "user" else "assistant", "content": msg["content"]})

    # Add current message
    messages.append({"role": "user", "content": payload["message"]})

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm.invoke(messages)
        )
        content = response.content if hasattr(response, "content") else str(response)
        return {"response": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Chat invocation failed: {e}")
