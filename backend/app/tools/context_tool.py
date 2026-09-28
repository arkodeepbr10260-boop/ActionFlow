from typing import Dict, Any
from app.db import get_all_context, save_context_item

def get_saved_context(session_id: str) -> Dict[str, Any]:
    """
    Return stored relevant session context.
    """
    return get_all_context(session_id)

def save_context(session_id: str, key: str, value: Any) -> Dict[str, Any]:
    """
    Save useful conversation/workflow context.
    """
    return save_context_item(session_id, key, value)
