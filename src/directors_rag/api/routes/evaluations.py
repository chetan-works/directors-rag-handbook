"""End-to-end evaluation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from directors_rag.api.dependencies import evaluation_harness
from directors_rag.api.security import require_api_key
from directors_rag.domain.models import EvalRunResponse, RagMode

router = APIRouter(
    prefix="/api/v1/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/run", response_model=EvalRunResponse)
async def run_evaluation(mode: RagMode = RagMode.SELF_RAG) -> EvalRunResponse:
    """Execute the checked-in golden dataset against one RAG strategy."""
    return await evaluation_harness().run(mode)
