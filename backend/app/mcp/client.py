import json
import logging
from typing import Dict, Any, List, Optional
from mcp.server.mcpserver import MCPServer
from app.mcp.mcp_server import mcp_server

logger = logging.getLogger("actionflow.mcp_client")

class MCPClientService:
    """
    In-process MCP Client/Service layer that delegates tool calls directly
    through the official MCPServer tool registry and lifecycle interface.
    This ensures all tool invocations are genuinely MCP-native without introducing
    unnecessary HTTP network hops.
    """
    def __init__(self, server: MCPServer = mcp_server):
        self.server = server

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """Discover tools registered with the MCP server."""
        tools = await self.server.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": getattr(t, "input_schema", {})
            }
            for t in tools
        ]

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an MCP tool through the official call_tool interface,
        parsing returned CallToolResult content into structured data.
        """
        try:
            call_result = await self.server.call_tool(tool_name, arguments)
            if call_result.is_error:
                error_msg = call_result.content[0].text if call_result.content else "Unknown MCP tool execution error"
                return {"success": False, "error": error_msg}

            raw_text = call_result.content[0].text if call_result.content else "{}"
            try:
                parsed_data = json.loads(raw_text)
            except Exception:
                parsed_data = {"raw": raw_text}

            return {"success": True, "data": parsed_data}
        except Exception as e:
            logger.error(f"MCP tool invocation failed for {tool_name}: {e}")
            return {"success": False, "error": str(e)}

_mcp_client = MCPClientService()

def get_mcp_client() -> MCPClientService:
    return _mcp_client
