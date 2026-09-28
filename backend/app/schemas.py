from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session ID for context tracking")
    message: str = Field(..., description="User prompt or goal")

class WorkflowEvent(BaseModel):
    event: str = Field(..., description="Concise workflow status update")
    timestamp: str = Field(..., description="ISO timestamp")
    details: Optional[Dict[str, Any]] = None

class PendingAction(BaseModel):
    action_id: str
    session_id: str
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    status: str  # 'pending', 'confirmed', 'cancelled', 'executed'

class ActionConfirmRequest(BaseModel):
    confirmed: bool = True

class ActionResponse(BaseModel):
    success: bool
    message: str
    action_id: str
    data: Optional[Dict[str, Any]] = None

class ToolResult(BaseModel):
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    status: str

class ChatResponse(BaseModel):
    session_id: str
    message: str
    workflow_events: List[WorkflowEvent] = []
    tool_results: List[ToolResult] = []
    pending_action: Optional[PendingAction] = None
    plan: Optional[Dict[str, Any]] = None
    final_result: Optional[str] = None
    context_used: Optional[str] = None
    retry_info: Optional[str] = None

class ReminderItem(BaseModel):
    id: str
    session_id: str
    title: str
    datetime_str: str
    status: str
    created_at: str

class ContextResponse(BaseModel):
    session_id: str
    context: Dict[str, Any]

class BedrockWorkflowTask(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class BedrockWorkflowPlan(BaseModel):
    goal: str
    tasks: List[BedrockWorkflowTask] = Field(default_factory=list)
    requires_confirmation: bool = False
