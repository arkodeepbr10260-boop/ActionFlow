import json
from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer
from app.tools.weather import get_weather as tool_get_weather
from app.tools.places import search_places as tool_search_places
from app.tools.calendar import get_calendar as tool_get_calendar
from app.tools.context_tool import get_saved_context as tool_get_saved_context, save_context as tool_save_context
from app.tools.planner import generate_plan as tool_generate_plan
from app.tools.reminder import create_reminder as tool_create_reminder

# Create official MCP Server instance
mcp_server = MCPServer(
    name="ActionFlow-MCP-Server",
    version="1.0.0",
    description="ActionFlow Self-Hosted MCP Server exposing agentic tools over Streamable HTTP"
)

@mcp_server.tool(name="get_weather", description="Get weather conditions and recommendation for a location")
async def mcp_get_weather(location: str, date: Optional[str] = None) -> str:
    res = await tool_get_weather(location, date)
    return json.dumps(res)

@mcp_server.tool(name="search_places", description="Search nearby places or activities for a query and location")
async def mcp_search_places(query: str, location: str) -> str:
    res = await tool_search_places(query, location)
    return json.dumps(res)

@mcp_server.tool(name="get_calendar", description="Retrieve upcoming calendar entries and reminders from database")
def mcp_get_calendar(session_id: Optional[str] = None) -> str:
    res = tool_get_calendar(session_id)
    return json.dumps(res)

@mcp_server.tool(name="get_saved_context", description="Retrieve stored conversation or user preference context")
def mcp_get_saved_context(session_id: str) -> str:
    res = tool_get_saved_context(session_id)
    return json.dumps(res)

@mcp_server.tool(name="save_context", description="Save context key-value pairs for session persistence")
def mcp_save_context(session_id: str, key: str, value: str) -> str:
    res = tool_save_context(session_id, key, value)
    return json.dumps(res)

@mcp_server.tool(name="generate_plan", description="Generate a structured multi-step plan based on tool results")
def mcp_generate_plan(user_goal: str, tool_results_json: str) -> str:
    try:
        results = json.loads(tool_results_json)
    except Exception:
        results = {}
    res = tool_generate_plan(user_goal, results)
    return json.dumps(res)

@mcp_server.tool(name="create_reminder", description="State-changing tool to prepare or execute a reminder (requires confirmation if unconfirmed)")
def mcp_create_reminder(session_id: str, title: str, datetime_str: str, confirmed: bool = False) -> str:
    res = tool_create_reminder(session_id, title, datetime_str, confirmed)
    return json.dumps(res)

# Streamable HTTP ASGI App
mcp_asgi_app = mcp_server.streamable_http_app()
