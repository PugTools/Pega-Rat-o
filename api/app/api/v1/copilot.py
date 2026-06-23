from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.modules.auth.auth_service import get_current_user
from app.modules.copilot.rag_service import CopilotRAGService


router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("/chat")
def chat(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = CopilotRAGService()
    result = service.answer(payload.question)
    result["requested_by"] = current_user["email"]
    return result
