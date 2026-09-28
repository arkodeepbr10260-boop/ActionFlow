from fastapi import APIRouter, HTTPException
from app.schemas import ActionConfirmRequest, ActionResponse
from app.agent.workflow import AgentOrchestrator

router = APIRouter()
orchestrator = AgentOrchestrator()

@router.post("/api/actions/{action_id}/confirm", response_model=ActionResponse)
async def confirm_action_endpoint(action_id: str):
    res = await orchestrator.confirm_action(action_id)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.post("/api/actions/{action_id}/cancel", response_model=ActionResponse)
async def cancel_action_endpoint(action_id: str):
    res = await orchestrator.cancel_action(action_id)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res
