"""Curated source catalog and administrative ingestion routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from directors_rag.api.dependencies import ingestion_service, source_catalog
from directors_rag.api.security import require_api_key
from directors_rag.domain.models import IngestionResult, SourceDefinition

router = APIRouter(
    prefix="/api/v1/sources",
    tags=["sources"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[SourceDefinition])
async def list_sources() -> list[SourceDefinition]:
    """List reviewed source metadata; this never triggers a network fetch."""
    return source_catalog().all()


@router.post("/{source_id}/ingest", response_model=IngestionResult)
async def ingest_source(source_id: str) -> IngestionResult:
    """Fetch and index one exact source URL from the checked-in manifest."""
    try:
        source = source_catalog().get(source_id)
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if not source.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source is disabled")
    return await ingestion_service().ingest(source)


@router.post("/ingest-enabled/all", response_model=list[IngestionResult])
async def ingest_all_enabled_sources() -> list[IngestionResult]:
    """Index enabled sources sequentially to be respectful to OER publishers."""
    results = []
    for source in source_catalog().enabled():
        results.append(await ingestion_service().ingest(source))
    return results
