import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.mcp.mcp_server import mcp_server, mcp_asgi_app
from app.mcp.client import get_mcp_client
from app.db import init_db

client = TestClient(app)

def test_mcp_server_initialization():
    """Verify official MCP Server instance attributes and Streamable HTTP ASGI app."""
    assert mcp_server.name == "ActionFlow-MCP-Server"
    assert mcp_server.version == "1.0.0"
    assert mcp_asgi_app is not None
    assert hasattr(mcp_server, "streamable_http_app")

@pytest.mark.asyncio
async def test_mcp_client_tool_discovery():
    """Verify official MCP SDK tool discovery lists all 7 production tools."""
    mcp_client = get_mcp_client()
    tools = await mcp_client.list_available_tools()
    assert len(tools) == 7
    discovered_names = {t["name"] for t in tools}
    expected_tools = {
        "get_weather",
        "search_places",
        "get_calendar",
        "get_saved_context",
        "save_context",
        "generate_plan",
        "create_reminder"
    }
    assert discovered_names == expected_tools

@pytest.mark.asyncio
async def test_mcp_client_read_only_tool_invocation():
    """Verify at least one read-only tool can be invoked through MCP client layer."""
    mcp_client = get_mcp_client()
    # Invoke get_weather through official MCP client layer
    result = await mcp_client.invoke_tool("get_weather", {"location": "Campus Town", "date": "Today"})
    assert result["success"] is True
    data = result["data"]
    assert "temperature" in data
    assert "weather_condition" in data

@pytest.mark.asyncio
async def test_mcp_create_reminder_confirmation_gating():
    """Verify create_reminder through MCP requires explicit confirmation when unconfirmed."""
    init_db()
    mcp_client = get_mcp_client()
    result = await mcp_client.invoke_tool("create_reminder", {
        "session_id": "test_mcp_gate_sess",
        "title": "Study Group Reminder",
        "datetime_str": "6:00 PM",
        "confirmed": False
    })
    assert result["success"] is True
    data = result["data"]
    assert data["status"] == "pending_confirmation"
    assert "pending_action" in data
    assert data["pending_action"]["status"] == "pending"
    assert data["pending_action"]["tool_name"] == "create_reminder"

def test_mcp_streamable_http_transport_mounted():
    """Verify Streamable HTTP transport is active and mounted at /mcp without crashing."""
    # Ensure route is registered in FastAPI
    matching_routes = [r for r in app.routes if getattr(r, "path", "") == "/mcp"]
    assert len(matching_routes) > 0
    # Mount serves request gracefully (307 redirect to trailing slash or 400/405 protocol handshake)
    response = client.get("/mcp", follow_redirects=False)
    assert response.status_code in [200, 307]
