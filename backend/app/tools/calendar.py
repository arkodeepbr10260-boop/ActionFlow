from typing import List, Dict, Any, Optional
from app.db import get_all_reminders

def get_calendar(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return upcoming entries/reminders from SQLite database.
    """
    reminders = get_all_reminders(session_id)
    events = []
    for r in reminders:
        events.append({
            "id": r["id"],
            "title": r["title"],
            "datetime_str": r["datetime_str"],
            "status": r["status"],
            "type": "reminder"
        })
    return events
