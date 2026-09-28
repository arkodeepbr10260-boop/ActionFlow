import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Sessions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """)
        
        # Conversations summary
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        
        # Saved Context
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS context (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(session_id, key)
        )
        """)
        
        # Reminders
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            datetime_str TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        )
        """)
        
        # Pending Actions (State-changing tool confirmation)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_actions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
        """)
        
        # Tool Runs log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_runs (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            inputs TEXT NOT NULL,
            outputs TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        
        conn.commit()

# Session DB Helpers
def get_or_create_session(session_id: str) -> str:
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO sessions (session_id, created_at, updated_at) VALUES (?, ?, ?)",
                           (session_id, now, now))
            cursor.execute("INSERT INTO conversations (id, session_id, title, created_at) VALUES (?, ?, ?, ?)",
                           (str(uuid.uuid4()), session_id, "New Goal", now))
            conn.commit()
        else:
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            conn.commit()
    return session_id

def save_message(session_id: str, sender: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    get_or_create_session(session_id)
    msg_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    meta_json = json.dumps(metadata) if metadata else None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, session_id, sender, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, sender, content, now, meta_json)
        )
        # Update conversation title if first user message
        if sender == "user":
            cursor.execute("SELECT title FROM conversations WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row and row["title"] == "New Goal":
                short_title = content[:30] + ("..." if len(content) > 30 else "")
                cursor.execute("UPDATE conversations SET title = ? WHERE session_id = ?", (short_title, session_id))
        conn.commit()
        
    return {
        "id": msg_id,
        "session_id": session_id,
        "sender": sender,
        "content": content,
        "timestamp": now,
        "metadata": metadata
    }

def get_messages(session_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        rows = cursor.fetchall()
        messages = []
        for r in rows:
            messages.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "sender": r["sender"],
                "content": r["content"],
                "timestamp": r["timestamp"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else None
            })
        return messages

def save_context_item(session_id: str, key: str, value: Any) -> Dict[str, Any]:
    get_or_create_session(session_id)
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO context (id, session_id, key, value, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """, (item_id, session_id, key, val_str, now))
        conn.commit()
        
    return {"key": key, "value": value, "session_id": session_id, "updated_at": now}

def get_all_context(session_id: str) -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM context WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            val = r["value"]
            try:
                result[r["key"]] = json.loads(val)
            except Exception:
                result[r["key"]] = val
        return result

def create_pending_action_db(session_id: str, tool_name: str, arguments: Dict[str, Any], description: str) -> Dict[str, Any]:
    get_or_create_session(session_id)
    action_id = f"act_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    args_json = json.dumps(arguments)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pending_actions (id, session_id, tool_name, arguments, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (action_id, session_id, tool_name, args_json, description, now))
        conn.commit()
        
    return {
        "action_id": action_id,
        "session_id": session_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "description": description,
        "status": "pending",
        "created_at": now
    }

def get_pending_action(action_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_actions WHERE id = ?", (action_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "session_id": r["session_id"],
            "tool_name": r["tool_name"],
            "arguments": json.loads(r["arguments"]),
            "description": r["description"],
            "status": r["status"],
            "created_at": r["created_at"]
        }

def update_pending_action_status(action_id: str, status: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_actions SET status = ? WHERE id = ?", (status, action_id))
        conn.commit()
        return cursor.rowcount > 0

def add_reminder_db(session_id: str, title: str, datetime_str: str) -> Dict[str, Any]:
    get_or_create_session(session_id)
    rem_id = f"rem_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reminders (id, session_id, title, datetime_str, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (rem_id, session_id, title, datetime_str, now))
        conn.commit()
        
    return {
        "id": rem_id,
        "session_id": session_id,
        "title": title,
        "datetime_str": datetime_str,
        "status": "active",
        "created_at": now
    }

def get_all_reminders(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute("SELECT * FROM reminders WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
        else:
            cursor.execute("SELECT * FROM reminders ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def log_tool_run(session_id: str, tool_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any], status: str) -> Dict[str, Any]:
    get_or_create_session(session_id)
    run_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tool_runs (id, session_id, tool_name, inputs, outputs, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, session_id, tool_name, json.dumps(inputs), json.dumps(outputs), status, now))
        conn.commit()
        
    return {
        "id": run_id,
        "session_id": session_id,
        "tool_name": tool_name,
        "inputs": inputs,
        "outputs": outputs,
        "status": status,
        "created_at": now
    }
