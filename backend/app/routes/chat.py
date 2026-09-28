import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas import ChatRequest, ChatResponse
from app.agent.workflow import AgentOrchestrator

router = APIRouter()
orchestrator = AgentOrchestrator()

@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    try:
        result = await orchestrator.execute_workflow(request.session_id, request.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    async def event_generator():
        try:
            # Execute workflow
            result = await orchestrator.execute_workflow(request.session_id, request.message)
            
            # Stream status events first for real-time progress feel
            for event in result.get("workflow_events", []):
                yield f"data: {json.dumps({'type': 'event', 'data': event})}\n\n"
                await asyncio.sleep(0.15)
                
            # Stream final payload
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
