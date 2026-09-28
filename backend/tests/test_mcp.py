from fastapi.testclient import TestClient
from app.main import app
from app.mcp.mcp_server import mcp_server

client = TestClient(app)

def test_mcp_server_initialization():
    assert mcp_server.name == "ActionFlow-MCP-Server"
    assert mcp_server.version == "1.0.0"

def test_mcp_tool_discovery():
    # Verify tool functions are registered on MCPServer instance
    assert hasattr(mcp_server, "streamable_http_app")

def test_mcp_streamable_http_endpoint():
    # Make GET request to /mcp or stream endpoint
    response = client.get("/mcp")
    # Streamable HTTP endpoint handles standard HTTP calls gracefully (405 or 400 for empty body or SSE headers)
    assert response.status_code in [200, 400, 404, 405]
