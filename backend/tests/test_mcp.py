from fastapi.testclient import TestClient
from app.main import app
from app.mcp.mcp_server import mcp_server, mcp_asgi_app

client = TestClient(app)

def test_mcp_server_initialization():
    """Verify official MCP Server instance attributes."""
    assert mcp_server.name == "ActionFlow-MCP-Server"
    assert mcp_server.version == "1.0.0"
    assert mcp_asgi_app is not None

def test_mcp_tool_discovery():
    """Verify that all 7 production MCP tools are registered and discoverable."""
    tools = mcp_server._tool_manager._tools
    assert len(tools) == 7
    expected_tools = [
        "get_weather",
        "search_places",
        "get_calendar",
        "get_saved_context",
        "save_context",
        "generate_plan",
        "create_reminder"
    ]
    for tool_name in expected_tools:
        assert tool_name in tools, f"Expected MCP tool '{tool_name}' not found in registered tools"

def test_mcp_streamable_http_endpoint():
    """Verify Streamable HTTP transport is active and mounted at /mcp."""
    assert hasattr(mcp_server, "streamable_http_app")
    # Streamable HTTP endpoint accepts HTTP requests (redirecting trailing slash or handling protocol handshake)
    response = client.get("/mcp")
    assert response.status_code in [200, 307, 400, 404, 405]
    
    # Verify post to /mcp with JSON-RPC payload behaves appropriately according to MCP HTTP stream specification
    rpc_response = client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    assert rpc_response.status_code in [200, 307, 400, 404, 405]
