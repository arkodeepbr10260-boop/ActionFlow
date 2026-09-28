import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db import (
    save_message, save_context_item, get_all_context,
    get_messages, log_tool_run, get_pending_action,
    update_pending_action_status
)
from app.agent.llm_provider import get_llm_provider
from app.mcp.client import get_mcp_client
from app.schemas import BedrockWorkflowPlan, BedrockWorkflowTask
from app.tools.reminder import create_reminder

class AgentOrchestrator:
    def __init__(self):
        self.llm = get_llm_provider()
        self.mcp = get_mcp_client()

    async def execute_workflow(self, session_id: str, message: str) -> Dict[str, Any]:
        # 1. Save user message & load session context
        save_message(session_id, "user", message)
        existing_context = get_all_context(session_id)
        msg_history = get_messages(session_id)

        events: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        
        def emit_event(name: str, details: Optional[Dict[str, Any]] = None):
            events.append({
                "event": name,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            })

        # Step 1: Request Interpreter via LLM
        emit_event("Understanding request")
        
        # Detect non-sensitive user preferences from message
        message_lower = message.lower()
        if "quiet" in message_lower:
            save_context_item(session_id, "preferred_activity_type", "quiet spots")
            existing_context["preferred_activity_type"] = "quiet spots"
        elif "outdoor" in message_lower:
            save_context_item(session_id, "preferred_activity_type", "outdoor parks and cafes")
            existing_context["preferred_activity_type"] = "outdoor parks and cafes"
        elif "coffee" in message_lower or "cafe" in message_lower:
            save_context_item(session_id, "preferred_activity_type", "coffee shops")
            existing_context["preferred_activity_type"] = "coffee shops"

        context_used_text = None
        if existing_context.get("preferred_activity_type"):
            context_used_text = f"Using saved preference: {existing_context['preferred_activity_type']}"

        system_prompt = (
            "You are ActionFlow's intelligent agentic orchestrator. Inspect the user goal, message history, "
            "and saved persistent context. Decide the structured task sequence using the registered MCP tools:\n"
            "- get_weather(location: string, date: string)\n"
            "- search_places(query: string, location: string)\n"
            "- generate_plan(user_goal: string)\n"
            "- create_reminder(title: string, datetime_str: string)\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "goal": "summarized user goal",\n'
            '  "tasks": [\n'
            '    {"tool": "get_weather", "arguments": {"location": "string", "date": "string"}},\n'
            '    {"tool": "search_places", "arguments": {"query": "string", "location": "string"}},\n'
            '    {"tool": "generate_plan", "arguments": {"user_goal": "string"}},\n'
            '    {"tool": "create_reminder", "arguments": {"title": "string", "datetime_str": "string"}}\n'
            "  ],\n"
            '  "requires_confirmation": boolean\n'
            "}\n"
            "Do not include explanation, markdown code blocks, or chain-of-thought."
        )

        user_prompt = f"Goal: {message}\nContext: {json.dumps(existing_context)}"
        
        # Invoke LLM (BedrockProvider when live, MockBedrockProvider otherwise)
        workflow_plan: Optional[BedrockWorkflowPlan] = None
        try:
            llm_output = self.llm.generate(user_prompt, system_prompt=system_prompt)
            cleaned = llm_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            workflow_plan = BedrockWorkflowPlan(**data)
        except Exception:
            # Deterministic adaptive fallback
            if "tomorrow" in message_lower and existing_context.get("last_goal"):
                loc = existing_context.get("location", "Campus Town")
                act = existing_context.get("preferred_activity_type") or existing_context.get("activity_query", "nearby lounge or coffee shop")
                workflow_plan = BedrockWorkflowPlan(
                    goal=message,
                    tasks=[
                        BedrockWorkflowTask(tool="get_weather", arguments={"location": loc, "date": "Tomorrow"}),
                        BedrockWorkflowTask(tool="search_places", arguments={"query": act, "location": loc}),
                        BedrockWorkflowTask(tool="generate_plan", arguments={"user_goal": message})
                    ],
                    requires_confirmation=False
                )
            else:
                act = existing_context.get("preferred_activity_type", "nearby lounge or coffee shop")
                workflow_plan = BedrockWorkflowPlan(
                    goal=message,
                    tasks=[
                        BedrockWorkflowTask(tool="get_weather", arguments={"location": "Campus Town", "date": "Today"}),
                        BedrockWorkflowTask(tool="search_places", arguments={"query": act, "location": "Campus Town"}),
                        BedrockWorkflowTask(tool="generate_plan", arguments={"user_goal": message}),
                        BedrockWorkflowTask(tool="create_reminder", arguments={"title": "Evening Activity: Campus Lounge", "datetime_str": "6:00 PM"})
                    ],
                    requires_confirmation=("remind" in message_lower or "reminder" in message_lower or "6" in message_lower)
                )

        emit_event("Planning")

        # Bounded adaptive agent loop (maximum 8 iterations)
        MAX_ITERATIONS = 8
        task_queue: List[BedrockWorkflowTask] = list(workflow_plan.tasks)
        iteration = 0
        retry_counts: Dict[str, int] = {}
        collected_results: Dict[str, Any] = {}
        pending_action_data = None
        weather_res: Dict[str, Any] = {"weather_condition": "Clear", "temperature": "22°C"}
        places_res: List[Dict[str, Any]] = []
        plan_res: Dict[str, Any] = {}
        location_used = "Campus Town"
        activity_used = existing_context.get("preferred_activity_type", "nearby spots")
        target_date = "Today"
        retry_notes: List[str] = []

        while task_queue and iteration < MAX_ITERATIONS:
            iteration += 1
            current_task = task_queue.pop(0)
            t_name = current_task.tool
            t_args = dict(current_task.arguments)

            emit_event("Calling tool", {"tool": t_name, "iteration": iteration})

            # Native execution through MCP Client Service layer
            if t_name == "create_reminder":
                # State-changing tool must be staged unconfirmed
                t_args["session_id"] = session_id
                t_args["confirmed"] = False
                if not t_args.get("title"):
                    t_args["title"] = f"Evening Activity: {plan_res.get('recommended_place', {}).get('name', 'Planned Activity')}"
                if not t_args.get("datetime_str"):
                    t_args["datetime_str"] = "6:00 PM"

                emit_event("Waiting for confirmation")
                mcp_resp = await self.mcp.invoke_tool(t_name, t_args)
                tool_data = mcp_resp.get("data", {})
                pending_action_data = tool_data.get("pending_action")
                log_tool_run(session_id, t_name, t_args, tool_data, "pending_confirmation")
                tool_results.append({
                    "tool_name": t_name,
                    "inputs": t_args,
                    "outputs": tool_data,
                    "status": "pending_confirmation"
                })
                emit_event("Tool completed", {"tool": t_name})
                continue

            elif t_name == "generate_plan":
                t_args["tool_results_json"] = json.dumps(collected_results)
                if "user_goal" not in t_args:
                    t_args["user_goal"] = message

            # Execute tool through MCP
            mcp_resp = await self.mcp.invoke_tool(t_name, t_args)
            emit_event("Tool completed", {"tool": t_name})
            emit_event("Evaluating result", {"tool": t_name})

            tool_succeeded = mcp_resp.get("success", False)
            tool_data = mcp_resp.get("data", {})

            # Adaptive recovery: if place search returns empty or tool failed, retry with broadened query
            if t_name == "search_places":
                places = tool_data if isinstance(tool_data, list) else tool_data.get("places", [])
                if (not tool_succeeded or len(places) == 0) and retry_counts.get("search_places", 0) < 2:
                    retry_counts["search_places"] = retry_counts.get("search_places", 0) + 1
                    broadened_query = "cafe or park"
                    retry_notes.append(f"Place search broadened to '{broadened_query}'")
                    task_queue.insert(0, BedrockWorkflowTask(
                        tool="search_places",
                        arguments={"query": broadened_query, "location": t_args.get("location", location_used)}
                    ))
                    emit_event("Choosing next step", {"action": "retry_place_search_broadened"})
                    continue

                places_res = places if isinstance(places, list) else []
                collected_results["places"] = places_res
                activity_used = t_args.get("query", activity_used)
                location_used = t_args.get("location", location_used)
                log_tool_run(session_id, t_name, t_args, {"places": places_res}, "success")
                tool_results.append({
                    "tool_name": t_name,
                    "inputs": t_args,
                    "outputs": {"places": places_res},
                    "status": "success"
                })

            elif t_name == "get_weather":
                if not tool_succeeded and retry_counts.get("get_weather", 0) < 2:
                    retry_counts["get_weather"] = retry_counts.get("get_weather", 0) + 1
                    retry_notes.append("Weather retry executed")
                    task_queue.insert(0, BedrockWorkflowTask(
                        tool="get_weather",
                        arguments={"location": t_args.get("location", "Campus Town"), "date": t_args.get("date", "Today")}
                    ))
                    emit_event("Choosing next step", {"action": "retry_weather"})
                    continue

                weather_res = tool_data if isinstance(tool_data, dict) else {"weather_condition": "Clear", "temperature": "22°C"}
                collected_results["weather"] = weather_res
                location_used = t_args.get("location", location_used)
                target_date = t_args.get("date", target_date)
                log_tool_run(session_id, t_name, t_args, weather_res, "success")
                tool_results.append({
                    "tool_name": t_name,
                    "inputs": t_args,
                    "outputs": weather_res,
                    "status": "success"
                })

            elif t_name == "generate_plan":
                plan_res = tool_data if isinstance(tool_data, dict) else {}
                log_tool_run(session_id, t_name, t_args, plan_res, "success")
                tool_results.append({
                    "tool_name": t_name,
                    "inputs": t_args,
                    "outputs": plan_res,
                    "status": "success"
                })

            elif t_name in ["get_saved_context", "save_context", "get_calendar"]:
                log_tool_run(session_id, t_name, t_args, tool_data, "success")
                tool_results.append({
                    "tool_name": t_name,
                    "inputs": t_args,
                    "outputs": tool_data,
                    "status": "success"
                })

            emit_event("Choosing next step")

        # Save persistent context & preferences
        save_context_item(session_id, "last_goal", message)
        save_context_item(session_id, "location", location_used)
        save_context_item(session_id, "activity_query", activity_used)
        if plan_res:
            save_context_item(session_id, "last_plan", plan_res)

        emit_event("Workflow complete")

        # Response formulation (no hidden reasoning/chain-of-thought exposed)
        if pending_action_data:
            rec_name = plan_res.get("recommended_place", {}).get("name", "the recommended place")
            rec_cat = plan_res.get("recommended_place", {}).get("category", "Activity")
            w_cond = weather_res.get("weather_condition", "Pleasant")
            w_temp = weather_res.get("temperature", "22°C")
            dt_str = pending_action_data["arguments"].get("datetime_str", "6:00 PM")
            response_text = (
                f"I've planned your evening after college! The weather will be {w_cond} ({w_temp}). "
                f"I recommend visiting **{rec_name}** ({rec_cat}). "
                f"I have prepared a reminder for {dt_str}. Please confirm to set the reminder."
            )
        else:
            rec_name = plan_res.get("recommended_place", {}).get("name", "the recommended spot")
            w_cond = weather_res.get("weather_condition", "Pleasant")
            w_temp = weather_res.get("temperature", "22°C")
            response_text = (
                f"Here is your updated plan for {target_date}: The weather in {location_used} is expected to be {w_cond} ({w_temp}). "
                f"Great option: **{rec_name}**!"
            )

        # Save assistant message
        save_message(session_id, "assistant", response_text, metadata={"plan": plan_res, "pending_action": pending_action_data})

        return {
            "session_id": session_id,
            "message": response_text,
            "workflow_events": events,
            "tool_results": tool_results,
            "pending_action": pending_action_data,
            "plan": plan_res,
            "final_result": response_text,
            "context_used": context_used_text,
            "retry_info": "; ".join(retry_notes) if retry_notes else None
        }

    async def confirm_action(self, action_id: str) -> Dict[str, Any]:
        pending = get_pending_action(action_id)
        if not pending:
            return {"success": False, "message": "Pending action not found or invalid action ID.", "action_id": action_id}
        
        if pending["status"] != "pending":
            return {"success": False, "message": f"Action has already been {pending['status']}.", "action_id": action_id}
        
        # Execute action
        session_id = pending["session_id"]
        tool_name = pending["tool_name"]
        args = pending["arguments"]
        
        if tool_name == "create_reminder":
            res = create_reminder(session_id, args["title"], args["datetime_str"], confirmed=True)
            update_pending_action_status(action_id, "confirmed")
            log_tool_run(session_id, "create_reminder", args, res, "executed")
            
            # Post success message to conversation
            msg = f"Reminder confirmed and saved! Title: '{args['title']}' for {args['datetime_str']}."
            save_message(session_id, "assistant", msg, metadata={"reminder": res.get("reminder")})
            
            return {
                "success": True,
                "message": msg,
                "action_id": action_id,
                "data": res.get("reminder")
            }
        
        return {"success": False, "message": f"Unsupported tool execution: {tool_name}", "action_id": action_id}

    async def cancel_action(self, action_id: str) -> Dict[str, Any]:
        pending = get_pending_action(action_id)
        if not pending:
            return {"success": False, "message": "Pending action not found.", "action_id": action_id}
        
        if pending["status"] != "pending":
            return {"success": False, "message": f"Action has already been {pending['status']}.", "action_id": action_id}

        update_pending_action_status(action_id, "cancelled")
        session_id = pending["session_id"]
        msg = f"Action '{pending['description']}' was cancelled."
        save_message(session_id, "assistant", msg)

        return {
            "success": True,
            "message": msg,
            "action_id": action_id,
            "data": None
        }
