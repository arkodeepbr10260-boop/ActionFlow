from fastapi import APIRouter
from app.db import get_messages, get_all_context
from app.schemas import ContextResponse

router = APIRouter()

@router.get("/api/conversations/{session_id}")
def get_conversation_history(session_id: str):
    messages = get_messages(session_id)
    return {"session_id": session_id, "messages": messages}

@router.get("/api/context/{session_id}", response_model=ContextResponse)
def get_session_context(session_id: str):
    ctx = get_all_context(session_id)
    return {"session_id": session_id, "context": ctx}
