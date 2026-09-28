# ActionFlow

**Plan • Orchestrate • Act**

> An agentic assistant that understands your goals, decomposes them into tasks, selects and executes tools, manages state, and requires confirmation before mutating actions — powered by Amazon Bedrock and a self-hosted MCP server over Streamable HTTP.

---

## Overview

ActionFlow is not a chatbot. It is an **agentic workflow engine** that:

1. **Understands** a natural-language goal
2. **Breaks** it into concrete tasks
3. **Decides** which tools are required
4. **Executes** those tools (weather, places, reminders, etc.)
5. **Maintains** conversation context and state across turns
6. **Asks for confirmation** before any state-changing action
7. **Continues** the conversation with full context after confirmation
8. **Returns** a clear, structured final result

## Problem

Traditional chatbots return text. They cannot plan, use tools, or take actions on the user's behalf. Users want assistants that **do things**, not just talk about them.

## Solution

ActionFlow implements the **Plan → Orchestrate → Act** pattern:

- A request interpreter parses user intent
- A task planner determines the required steps
- A tool selector picks from available MCP tools
- A tool executor runs each tool and collects results
- A context manager saves session state for follow-up queries
- A confirmation manager gates all mutating operations
- A response generator produces the final user-facing output

## Why Agentic

| Feature | Chatbot | ActionFlow |
|---------|---------|------------|
| Text responses | ✓ | ✓ |
| Multi-step planning | ✗ | ✓ |
| Tool discovery & execution | ✗ | ✓ |
| State management | ✗ | ✓ |
| Confirmation for mutations | ✗ | ✓ |
| Context persistence | ✗ | ✓ |
| Follow-up understanding | ✗ | ✓ |

## Key Features

- 🧠 **Agentic Workflow** — Multi-step task decomposition and execution
- 🔧 **7 MCP Tools** — Weather, places, calendar, context, planner, reminders
- 🛡️ **Confirmation Gates** — State-changing actions require explicit user approval
- 🔄 **Context Persistence** — Follow-up messages retain full session context
- 🌦️ **Real API Integration** — Open-Meteo weather, OpenStreetMap/Nominatim places
- 🎤 **Voice Input** — Web Speech API support with graceful fallback
- ⚡ **Streamable HTTP** — MCP 2025-11-25+ specification compliant transport
- 🤖 **Amazon Bedrock** — Real AWS AI reasoning layer with clean mock fallback

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                  │
│   Hero → Chat → Voice → Tool Cards → Confirmation      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │  Routes   │  │  Agent   │  │  MCP Server          │  │
│  │ /api/chat │  │ Workflow │  │ /mcp (Streamable HTTP│) │
│  │ /health   │  │ Orchestr │  │ 7 Tools Registered   │  │
│  │ /actions  │  │          │  └──────────────────────┘  │
│  └──────────┘  └──────────┘                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │  SQLite   │  │ Bedrock  │  │  External APIs       │  │
│  │  (State)  │  │ Provider │  │  Open-Meteo, OSM     │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Alexa+ Track

ActionFlow provides an **Alexa+ style simulated experience** backed by a self-hosted MCP server. The frontend is our own original design — it does not use official Amazon or Alexa branding, logos, or UI. The conversational UX is inspired by modern voice-first assistants.

## Self-Hosted MCP Server

A real MCP server is implemented using the **official MCP Python SDK v2.x** (`mcp>=2.0`). It exposes 7 tools:

| Tool | Type | Description |
|------|------|-------------|
| `get_weather` | Read | Weather conditions via Open-Meteo |
| `search_places` | Read | Nearby places via Nominatim/OSM |
| `get_calendar` | Read | Upcoming reminders from SQLite |
| `get_saved_context` | Read | Stored session context |
| `save_context` | Write | Save context key-value pairs |
| `generate_plan` | Read | Structured multi-step plan |
| `create_reminder` | **Mutating** | Requires confirmation before execution |

The MCP server is mounted at `/mcp` on the FastAPI application and uses the `MCPServer.streamable_http_app()` method from the SDK.

## Streamable HTTP

The MCP endpoint uses **Streamable HTTP transport** (not SSE-only), compatible with MCP specification **2025-11-25** or later. The Starlette ASGI app returned by `streamable_http_app()` is mounted directly into FastAPI.

## Amazon Bedrock

ActionFlow uses **Amazon Bedrock** as the AI reasoning layer via `boto3`. The provider abstraction:

- `LLMProvider` — Abstract base class
- `BedrockProvider` — Real AWS Bedrock `converse()` calls when credentials are configured
- `MockBedrockProvider` — Structured mock responses for local development

The `BEDROCK_MODEL_ID` environment variable controls which model is used.

## AWS Builder

- Real `boto3` Bedrock Runtime client initialization
- Real `converse()` API call with configurable model
- Clean separation between live and mock modes
- Environment variable driven configuration

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| AI | Amazon Bedrock, boto3 |
| MCP | Official MCP Python SDK v2.x, Streamable HTTP |
| Database | SQLite |
| Weather | Open-Meteo API |
| Places | OpenStreetMap Nominatim |
| Voice | Web Speech API |

## Project Structure

```
ActionFlow/
├── frontend/                 # Next.js TypeScript app
│   └── src/app/
│       ├── globals.css       # Design system
│       ├── layout.tsx        # Root layout + SEO
│       └── page.tsx          # Full chat UI
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint + MCP mount
│   │   ├── config.py         # Environment configuration
│   │   ├── db.py             # SQLite database layer
│   │   ├── schemas.py        # Pydantic models
│   │   ├── agent/
│   │   │   ├── llm_provider.py  # Bedrock + Mock providers
│   │   │   └── workflow.py      # Agent orchestrator
│   │   ├── mcp/
│   │   │   └── mcp_server.py    # MCP Server + 7 tools
│   │   ├── tools/
│   │   │   ├── weather.py       # Open-Meteo integration
│   │   │   ├── places.py        # Nominatim integration
│   │   │   ├── calendar.py      # Calendar/reminders
│   │   │   ├── context_tool.py  # Context persistence
│   │   │   ├── planner.py       # Plan generation
│   │   │   └── reminder.py      # Reminder (confirmation-gated)
│   │   └── routes/
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── actions.py
│   │       ├── context.py
│   │       └── reminders.py
│   ├── tests/
│   │   ├── test_health.py
│   │   ├── test_tools.py
│   │   ├── test_mcp.py
│   │   └── test_workflow.py
│   └── requirements.txt
├── docs/
│   └── devpost_material.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Environment Variables

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key for Bedrock | For live mode |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | For live mode |
| `AWS_REGION` | AWS region (default: us-east-1) | For live mode |
| `BEDROCK_MODEL_ID` | Bedrock model ID | For live mode |
| `FRONTEND_ORIGIN` | Frontend URL for CORS | No (default: http://localhost:3000) |

### Development Mode (No AWS Credentials)

Leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` empty. The system automatically falls back to `MockBedrockProvider`, which returns structured responses enabling full UI and workflow testing.

### Live Mode (With AWS Credentials)

Set valid AWS credentials. The system uses `BedrockProvider` with real `converse()` API calls.

## Running Locally

### Start Backend

```bash
cd backend
venv\Scripts\activate    # or source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

## Testing

### Backend Tests

```bash
cd <project-root>
backend\venv\Scripts\python -m pytest backend\tests\ -v
```

**16 tests** covering:
- `/health` endpoint
- `get_weather` tool
- `search_places` tool
- `create_reminder` confirmation flow
- Context persistence
- MCP server initialization
- MCP tool discovery
- Streamable HTTP MCP transport
- Agent orchestration (full workflow)
- Duplicate confirmation protection
- Action cancellation
- Invalid action ID handling
- Conversation history
- Follow-up context
- Empty message validation
- Reminders endpoint

### Frontend Type Check

```bash
cd frontend
npx next build
```

## Demo Workflow

### Primary Demo

**User Input:**
> "Plan my evening after college. Check the weather, find a nearby activity, and remind me at 6 PM."

**Expected Steps:**
1. ✅ Understanding request
2. ✅ Planning tasks
3. ✅ Checking weather → Weather card with conditions
4. ✅ Searching nearby places → Places card with recommendations
5. ✅ Preparing plan → Structured plan card
6. ✅ Waiting for confirmation → Confirmation card appears
7. User clicks **Confirm**
8. ✅ Reminder saved → Success message
9. ✅ Conversation continues with saved context

### Follow-up Test

**User Input:**
> "What about tomorrow?"

The system uses stored context (location, activity preferences, last goal) to generate an updated plan for the next day.

## Screenshots

*Run the application and visit http://localhost:3000 to see the live interface.*

## Limitations

- Voice input depends on browser Web Speech API support (Chrome recommended)
- Mock mode returns deterministic structured responses (not generative AI)
- Open-Meteo and Nominatim have rate limits for free usage
- SQLite is single-file; not suited for concurrent production workloads
- Reminders are stored but no push notification mechanism is implemented

## Future Scope

- Real Alexa+ skill integration via ASK SDK
- Push notification delivery for reminders
- Multi-modal input (image, file upload)
- Expanded tool ecosystem (email, calendar sync, maps)
- User authentication and multi-user sessions
- PostgreSQL for production database
- WebSocket-based real-time streaming

## License

MIT — see [LICENSE](LICENSE)
