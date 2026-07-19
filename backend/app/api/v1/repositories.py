"""
AutoBug AI — Repositories API
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.repository import IndexStatus, Repository
from app.rag.indexer import RepositoryIndexer
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services.github_service import GitHubService

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201)
async def connect_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Connect a GitHub repository and trigger indexing."""
    # Parse full_name from URL
    parts = payload.github_url.rstrip("/").replace(".git", "").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    full_name = f"{parts[-2]}/{parts[-1]}"
    name = parts[-1]

    # Check if already connected
    result = await db.execute(
        select(Repository).where(Repository.github_url == payload.github_url)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Fetch GitHub metadata
    try:
        gh = GitHubService()
        info = gh.get_repo_info(full_name)
    except Exception:
        info = {}

    repo = Repository(
        id=str(uuid.uuid4()),
        github_url=payload.github_url,
        full_name=full_name,
        name=name,
        description=info.get("description"),
        default_branch=info.get("default_branch", payload.default_branch),
        languages=info.get("languages"),
        index_status=IndexStatus.PENDING,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    # Trigger indexing in background
    background_tasks.add_task(_index_repository, repo.id, payload.github_url, repo.default_branch)

    return repo


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: str, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repository).order_by(Repository.created_at.desc()))
    return result.scalars().all()


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(repo_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    import shutil
    import os
    from app.models.issue import Issue
    from app.models.job import Job
    from app.models.patch import Patch
    from app.models.pull_request import PullRequest

    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Clean up Qdrant collection
    try:
        indexer = RepositoryIndexer()
        collection_name = repo.qdrant_collection or f"autobug_repo_{repo_id}"
        indexer.delete_collection(collection_name)
    except Exception:
        pass

    # Clean up cloned repository directory on disk
    repo_dir = f"/tmp/autobug_repos/{repo_id}"
    if os.path.exists(repo_dir):
        try:
            shutil.rmtree(repo_dir)
        except Exception:
            pass

    # Fetch issue IDs to delete related jobs, patches, and pull requests
    issues_result = await db.execute(select(Issue).where(Issue.repository_id == repo_id))
    issues = issues_result.scalars().all()
    issue_ids = [issue.id for issue in issues]

    if issue_ids:
        # Delete pull requests
        await db.execute(delete(PullRequest).where(PullRequest.issue_id.in_(issue_ids)))
        # Delete patches
        await db.execute(delete(Patch).where(Patch.issue_id.in_(issue_ids)))
        # Delete jobs
        await db.execute(delete(Job).where(Job.issue_id.in_(issue_ids)))
        # Delete issues
        await db.execute(delete(Issue).where(Issue.id.in_(issue_ids)))

    await db.delete(repo)
    await db.commit()


@router.post("/{repo_id}/sync", response_model=dict)
async def sync_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-index the repository."""
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.index_status = IndexStatus.INDEXING
    await db.commit()

    background_tasks.add_task(_index_repository, repo.id, repo.github_url, repo.default_branch)
    return {"status": "indexing_started", "repo_id": repo_id}


async def _index_repository(repo_id: str, github_url: str, branch: str) -> None:
    """Background task to index a repository."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        try:
            indexer = RepositoryIndexer()
            stats = await indexer.index_repository(github_url, repo_id, branch)

            repo = await db.get(Repository, repo_id)
            if repo:
                repo.index_status = IndexStatus.INDEXED
                repo.file_count = stats["files_indexed"]
                repo.qdrant_collection = stats["collection"]
                repo.languages = stats["languages"]
                await db.commit()
        except Exception:
            repo = await db.get(Repository, repo_id)
            if repo:
                repo.index_status = IndexStatus.FAILED
                await db.commit()

    await engine.dispose()
