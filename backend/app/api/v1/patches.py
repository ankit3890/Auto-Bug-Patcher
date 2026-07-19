"""
AutoBug AI — Patches API
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.patch import Patch
from app.schemas.patch import PatchResponse

router = APIRouter(prefix="/patches", tags=["patches"])


@router.get("/{patch_id}", response_model=PatchResponse)
async def get_patch(patch_id: str, db: AsyncSession = Depends(get_db)):
    patch = await db.get(Patch, patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.get("", response_model=list[PatchResponse])
async def list_patches(issue_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Patch).order_by(Patch.created_at.desc())
    if issue_id:
        q = q.where(Patch.issue_id == issue_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/{patch_id}/validate")
async def validate_patch(patch_id: str, db: AsyncSession = Depends(get_db)):
    """Re-trigger validation for a patch."""
    patch = await db.get(Patch, patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return {"status": "validation_queued", "patch_id": patch_id}
