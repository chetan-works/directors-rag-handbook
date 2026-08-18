"""Question-answering API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from directors_rag.api.dependencies import rag_service
from directors_rag.api.security import require_api_key
from directors_rag.domain.models import ChatRequest, ChatResponse

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Answer a question using the selected RAG strategy."""
    return await rag_service().ask(request)
