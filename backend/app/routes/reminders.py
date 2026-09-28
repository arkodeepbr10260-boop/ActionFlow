from typing import Optional, List
from fastapi import APIRouter
from app.db import get_all_reminders
from app.schemas import ReminderItem

router = APIRouter()

@router.get("/api/reminders", response_model=List[ReminderItem])
def list_reminders(session_id: Optional[str] = None):
    reminders = get_all_reminders(session_id)
    return reminders
