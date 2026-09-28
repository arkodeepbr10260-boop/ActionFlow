import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db import (
    save_message, save_context_item, get_all_context,
    get_messages, log_tool_run, get_pending_action,
    update_pending_action_status
)
from app.agent.llm_provider import get_llm_provider
from app.tools.weather import get_weather
from app.tools.places import search_places
from app.tools.planner import generate_plan
from app.tools.reminder import create_reminder

class AgentOrchestrator:
    def __init__(self):
        self.llm = get_llm_provider()

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

        # Step 1: Request Interpreter
        emit_event("Understanding request")
        
        # Step 2: Task Planner & Tool Selector
        emit_event("Planning tasks")
        
        # Determine intent / tools based on LLM & context
        message_lower = message.lower()
        
        # Follow-up context check (e.g., "What about tomorrow?")
        is_followup = False
        if "tomorrow" in message_lower and existing_context.get("last_goal"):
            is_followup = True
            location = existing_context.get("location", "Campus Town")
            activity = existing_context.get("activity_query", "nearby spots")
            target_date = "Tomorrow"
        else:
            location = "Campus Town"
            activity = "nearby lounge or coffee shop"
            target_date = "Today"

        collected_results: Dict[str, Any] = {}

        # Step 3: Tool Execution
        # Weather
        emit_event("Checking weather")
        weather_res = await get_weather(location, target_date)
        collected_results["weather"] = weather_res
        log_tool_run(session_id, "get_weather", {"location": location, "date": target_date}, weather_res, "success")
        tool_results.append({
            "tool_name": "get_weather",
            "inputs": {"location": location, "date": target_date},
            "outputs": weather_res,
            "status": "success"
        })

        # Places
        emit_event("Searching nearby places")
        places_res = await search_places(activity, location)
        collected_results["places"] = places_res
        log_tool_run(session_id, "search_places", {"query": activity, "location": location}, {"places": places_res}, "success")
        tool_results.append({
            "tool_name": "search_places",
            "inputs": {"query": activity, "location": location},
            "outputs": {"places": places_res},
            "status": "success"
        })

        # Plan generation
        emit_event("Preparing plan")
        plan_res = generate_plan(message, collected_results)
        log_tool_run(session_id, "generate_plan", {"goal": message}, plan_res, "success")
        tool_results.append({
            "tool_name": "generate_plan",
            "inputs": {"user_goal": message},
            "outputs": plan_res,
            "status": "success"
        })

        # Context update
        save_context_item(session_id, "last_goal", message)
        save_context_item(session_id, "location", location)
        save_context_item(session_id, "activity_query", activity)
        save_context_item(session_id, "last_plan", plan_res)

        pending_action_data = None
        
        # State-changing tool preparation (create_reminder)
        if "remind" in message_lower or "reminder" in message_lower or not is_followup:
            emit_event("Waiting for confirmation")
            time_str = "6:00 PM" if "6" in message_lower else "6:00 PM"
            rem_title = f"Evening Activity: {plan_res['recommended_place']['name']}"
            
            # Call create_reminder with confirmed=False
            rem_res = create_reminder(session_id, rem_title, time_str, confirmed=False)
            pending_action_data = rem_res.get("pending_action")
            
            log_tool_run(session_id, "create_reminder", {"title": rem_title, "datetime_str": time_str, "confirmed": False}, rem_res, "pending_confirmation")
            tool_results.append({
                "tool_name": "create_reminder",
                "inputs": {"title": rem_title, "datetime_str": time_str},
                "outputs": rem_res,
                "status": "pending_confirmation"
            })

        emit_event("Workflow complete")

        # Response text formulation (No chain of thought exposed)
        if pending_action_data:
            response_text = (
                f"I've planned your evening after college! The weather will be {weather_res['weather_condition']} ({weather_res['temperature']}). "
                f"I recommend visiting **{plan_res['recommended_place']['name']}** ({plan_res['recommended_place']['category']}). "
                f"I have prepared a reminder for {pending_action_data['arguments']['datetime_str']}. Please confirm to set the reminder."
            )
        else:
            response_text = (
                f"Here is your updated plan for {target_date}: The weather in {location} is expected to be {weather_res['weather_condition']} ({weather_res['temperature']}). "
                f"Great option: **{plan_res['recommended_place']['name']}**!"
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
            "final_result": response_text
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
