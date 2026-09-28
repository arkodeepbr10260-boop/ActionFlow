from fastapi import APIRouter
from app.config import settings
from app.agent.llm_provider import get_llm_provider

router = APIRouter()

@router.get("/health")
def health_check():
    llm = get_llm_provider()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "mcp_endpoint": "/mcp",
        "mcp_status": "active (Streamable HTTP)",
        "bedrock_mode": "live" if llm.is_live() else "mock/development",
        "bedrock_model_id": settings.BEDROCK_MODEL_ID
    }
