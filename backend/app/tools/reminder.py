from typing import Dict, Any
from app.db import create_pending_action_db, add_reminder_db

def create_reminder(session_id: str, title: str, datetime_str: str, confirmed: bool = False) -> Dict[str, Any]:
    """
    Create a reminder. If confirmed=False, generates a pending action requiring confirmation.
    If confirmed=True, executes and stores reminder in database.
    """
    if not confirmed:
        description = f"Set reminder '{title}' for {datetime_str}"
        pending_action = create_pending_action_db(
            session_id=session_id,
            tool_name="create_reminder",
            arguments={"title": title, "datetime_str": datetime_str},
            description=description
        )
        return {
            "status": "pending_confirmation",
            "pending_action": pending_action,
            "message": f"Confirmation required to set reminder: '{title}' at {datetime_str}"
        }
    else:
        reminder = add_reminder_db(
            session_id=session_id,
            title=title,
            datetime_str=datetime_str
        )
        return {
            "status": "executed",
            "reminder": reminder,
            "message": f"Reminder '{title}' created for {datetime_str}!"
        }
