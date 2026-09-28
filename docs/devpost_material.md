# Devpost Project Submission Material: ActionFlow

## 1. Project Overview
- **Project Name:** ActionFlow
- **Tagline:** Plan • Orchestrate • Act
- **Primary Hackathon Track:** Alexa+
- **Mini-Challenge:** AWS Builder
- **GitHub Repository:** [https://github.com/arkodeepbr10260-boop/ActionFlow](https://github.com/arkodeepbr10260-boop/ActionFlow)

---

## 2. Elevator Pitch
**ActionFlow** transforms everyday conversational voice/chat prompts into structured, multi-step actions. Going beyond basic question-answering assistants, ActionFlow inspects contextual memories, queries real-time MCP (Model Context Protocol) tools, synthesizes verifiable action plans, and orchestrates mutating changes (such as creating calendar reminders and scheduling events) through explicit user confirmation gates. Powered natively by Amazon Bedrock (Anthropic Claude 3.5 Sonnet / Haiku) with fallback support, ActionFlow demonstrates the future of production-grade agentic AI assistants.

---

## 3. Key Features & Architecture
- **Plan • Orchestrate • Act Pattern:** Multi-turn autonomous agent reasoning separating research/discovery from mutating state actions.
- **Model Context Protocol (MCP) Server (2025-11-25+ Spec):** Fully compliant MCP server exposed over Streamable HTTP (`/mcp`) offering 7 production tools:
  - `get_weather`: Live / mock weather conditions.
  - `search_places`: Points of interest, restaurants, and activity spots.
  - `get_calendar`: Read schedule and upcoming agenda.
  - `get_saved_context`: Retrieve persistent user preferences, past routines, and memory.
  - `save_context`: Save long-term memory across sessions.
  - `generate_plan`: Synthesize structured chronological action steps with risk classifications.
  - `create_reminder`: Mutating reminder and schedule creation.
- **Human-in-the-Loop Confirmation Gate:** Mutating or side-effect tools (e.g. reminders, updates) are staged as `PENDING_CONFIRMATION` with unique IDs, allowing the user to inspect, approve, or cancel before execution.
- **AWS Bedrock Integration:** Real AWS Bedrock runtime client utilizing the `converse` API with zero faking; switches gracefully to an offline mock orchestrator if AWS credentials are not set.
- **Full-Stack Experience:**
  - Modern, responsive Dark Navy/Slate UI built with Next.js 16 (App Router) and Tailwind CSS.
  - Web Speech API integration for instant voice prompt dictation.
  - Live execution event timeline (visualizing tool runs, arguments, and latency).
  - SQLite persistent database storing sessions, messages, context, reminders, and tool audits.

---

## 4. How It Works (The 3-Step Demo Workflow)
1. **User Prompt:**
   > *"Plan my evening after college. Check the weather, find a nearby activity, and remind me at 6 PM."*
2. **Autonomous Tool Orchestration:**
   - Agent checks past saved context and weather forecast.
   - Discovers nearby cafes or activities fitting the forecast.
   - Synthesizes a structured plan.
3. **Safe Execution:**
   - Detects mutating intent (`create_reminder`).
   - Surfaces an interactive confirmation card to the user.
   - Upon confirmation, writes the reminder to SQLite database and notifies the user.

---

## 5. Built With
- **AWS Bedrock** (`boto3`, Claude 3.5 Sonnet / Haiku via AWS Converse API)
- **FastAPI & Uvicorn** (Python 3.11+ asynchronous backend)
- **Model Context Protocol (MCP)** (`mcp` SDK v2 via Streamable HTTP)
- **SQLite & Pydantic v2** (Local state persistence and validation)
- **Next.js & React 19** (TypeScript, Tailwind CSS, Lucide icons, Web Speech API)
