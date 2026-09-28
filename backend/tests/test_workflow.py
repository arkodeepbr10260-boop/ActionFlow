import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

client = TestClient(app)

def test_full_chat_workflow():
    """Test the complete agentic workflow from chat to plan generation."""
    init_db()
    response = client.post("/api/chat", json={
        "session_id": "test_wf_session",
        "message": "Plan my evening after college. Check the weather, find a nearby activity, and remind me at 6 PM."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_wf_session"
    assert len(data["workflow_events"]) > 0
    assert len(data["tool_results"]) > 0
    assert data["plan"] is not None
    assert data["pending_action"] is not None
    # pending_action should be in pending status
    assert data["pending_action"]["status"] == "pending"

def test_context_persistence():
    """Test that context is saved and retrievable after a workflow run."""
    init_db()
    # Run an initial workflow
    client.post("/api/chat", json={
        "session_id": "test_ctx_session",
        "message": "Plan my evening after college."
    })
    # Check context
    ctx_response = client.get("/api/context/test_ctx_session")
    assert ctx_response.status_code == 200
    ctx_data = ctx_response.json()
    assert "last_goal" in ctx_data["context"]

def test_followup_context():
    """Test follow-up messages use saved context."""
    init_db()
    # Initial request
    client.post("/api/chat", json={
        "session_id": "test_followup_sess",
        "message": "Plan my evening after college."
    })
    # Follow-up
    response = client.post("/api/chat", json={
        "session_id": "test_followup_sess",
        "message": "What about tomorrow?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["message"]  # Should have a response
    assert data["plan"] is not None

def test_conversation_history():
    """Test that conversation history is persisted."""
    init_db()
    client.post("/api/chat", json={
        "session_id": "test_history_sess",
        "message": "Hello"
    })
    response = client.get("/api/conversations/test_history_sess")
    assert response.status_code == 200
    msgs = response.json()["messages"]
    assert len(msgs) >= 2  # user message + assistant response

def test_duplicate_confirmation_protection():
    """Test that confirming or cancelling an action twice fails gracefully."""
    init_db()
    # Create a workflow that produces a pending action
    chat_res = client.post("/api/chat", json={
        "session_id": "test_dup_sess",
        "message": "Plan my evening after college and remind me at 6 PM."
    })
    data = chat_res.json()
    action_id = data["pending_action"]["action_id"]
    
    # First confirm should succeed
    confirm_res = client.post(f"/api/actions/{action_id}/confirm")
    assert confirm_res.status_code == 200
    
    # Second confirm should fail (already confirmed)
    confirm_res2 = client.post(f"/api/actions/{action_id}/confirm")
    assert confirm_res2.status_code == 400

def test_cancel_action():
    """Test cancelling a pending action."""
    init_db()
    chat_res = client.post("/api/chat", json={
        "session_id": "test_cancel_sess",
        "message": "Plan my evening after college and remind me."
    })
    data = chat_res.json()
    action_id = data["pending_action"]["action_id"]
    
    cancel_res = client.post(f"/api/actions/{action_id}/cancel")
    assert cancel_res.status_code == 200
    
    # Trying to confirm after cancel should fail
    confirm_res = client.post(f"/api/actions/{action_id}/confirm")
    assert confirm_res.status_code == 400

def test_invalid_action_id():
    """Test handling of invalid action IDs."""
    init_db()
    response = client.post("/api/actions/nonexistent_id/confirm")
    assert response.status_code == 400

def test_reminders_endpoint():
    """Test GET /api/reminders returns list."""
    init_db()
    response = client.get("/api/reminders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_chat_empty_message():
    """Test that empty messages are rejected."""
    response = client.post("/api/chat", json={
        "session_id": "test_empty",
        "message": ""
    })
    assert response.status_code == 400
