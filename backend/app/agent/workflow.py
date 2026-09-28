import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db import (
    save_message, save_context_item, get_all_context,
    get_messages, log_tool_run, get_pending_action,
    update_pending_action_status
)
from app.agent.llm_provider import get_llm_provider
from app.schemas import BedrockWorkflowPlan, BedrockWorkflowTask
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

        # Step 1: Request Interpreter via LLM
        emit_event("Understanding request")
        
        system_prompt = (
            "You are ActionFlow's intelligent orchestrator. Given a user goal and previous conversation context, "
            "determine the structured tasks needed. Respond ONLY with a valid JSON object matching this schema:\n"
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
            # Clean potential markdown wrapping
            cleaned = llm_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            workflow_plan = BedrockWorkflowPlan(**data)
        except Exception as e:
            # Safe fallback if LLM response is malformed or Bedrock call fails
            message_lower = message.lower()
            if "tomorrow" in message_lower and existing_context.get("last_goal"):
                loc = existing_context.get("location", "Campus Town")
                act = existing_context.get("activity_query", "nearby lounge or coffee shop")
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
                workflow_plan = BedrockWorkflowPlan(
                    goal=message,
                    tasks=[
                        BedrockWorkflowTask(tool="get_weather", arguments={"location": "Campus Town", "date": "Today"}),
                        BedrockWorkflowTask(tool="search_places", arguments={"query": "nearby lounge or coffee shop", "location": "Campus Town"}),
                        BedrockWorkflowTask(tool="generate_plan", arguments={"user_goal": message}),
                        BedrockWorkflowTask(tool="create_reminder", arguments={"title": "Evening Activity: Campus Lounge", "datetime_str": "6:00 PM"})
                    ],
                    requires_confirmation=("remind" in message_lower or "reminder" in message_lower or "6" in message_lower)
                )

        # Step 2: Task Planner & Tool Selector
        emit_event("Planning tasks", {"goal": workflow_plan.goal, "task_count": len(workflow_plan.tasks)})

        collected_results: Dict[str, Any] = {}
        pending_action_data = None
        weather_res: Dict[str, Any] = {"weather_condition": "Clear", "temperature": "22°C"}
        places_res: List[Dict[str, Any]] = []
        plan_res: Dict[str, Any] = {}
        location_used = "Campus Town"
        activity_used = "nearby spots"
        target_date = "Today"

        # Step 3: Execute tasks produced by Bedrock/planner
        for task in workflow_plan.tasks:
            t_name = task.tool
            t_args = task.arguments

            if t_name == "get_weather":
                emit_event("Checking weather")
                location_used = t_args.get("location", "Campus Town")
                target_date = t_args.get("date", "Today")
                weather_res = await get_weather(location_used, target_date)
                collected_results["weather"] = weather_res
                log_tool_run(session_id, "get_weather", t_args, weather_res, "success")
                tool_results.append({
                    "tool_name": "get_weather",
                    "inputs": t_args,
                    "outputs": weather_res,
                    "status": "success"
                })

            elif t_name == "search_places":
                emit_event("Searching nearby places")
                activity_used = t_args.get("query", "nearby spots")
                location_used = t_args.get("location", location_used)
                places_res = await search_places(activity_used, location_used)
                collected_results["places"] = places_res
                log_tool_run(session_id, "search_places", t_args, {"places": places_res}, "success")
                tool_results.append({
                    "tool_name": "search_places",
                    "inputs": t_args,
                    "outputs": {"places": places_res},
                    "status": "success"
                })

            elif t_name == "generate_plan":
                emit_event("Preparing plan")
                plan_res = generate_plan(message, collected_results)
                log_tool_run(session_id, "generate_plan", {"goal": message}, plan_res, "success")
                tool_results.append({
                    "tool_name": "generate_plan",
                    "inputs": {"user_goal": message},
                    "outputs": plan_res,
                    "status": "success"
                })

            elif t_name == "create_reminder":
                # Explicit confirmation gate: unconfirmed reminder is staged
                emit_event("Waiting for confirmation")
                rem_title = t_args.get("title") or f"Evening Activity: {plan_res.get('recommended_place', {}).get('name', 'Planned Activity')}"
                time_str = t_args.get("datetime_str", "6:00 PM")
                rem_res = create_reminder(session_id, rem_title, time_str, confirmed=False)
                pending_action_data = rem_res.get("pending_action")
                log_tool_run(session_id, "create_reminder", {"title": rem_title, "datetime_str": time_str, "confirmed": False}, rem_res, "pending_confirmation")
                tool_results.append({
                    "tool_name": "create_reminder",
                    "inputs": {"title": rem_title, "datetime_str": time_str},
                    "outputs": rem_res,
                    "status": "pending_confirmation"
                })

        # Save persistent context
        save_context_item(session_id, "last_goal", message)
        save_context_item(session_id, "location", location_used)
        save_context_item(session_id, "activity_query", activity_used)
        if plan_res:
            save_context_item(session_id, "last_plan", plan_res)

        emit_event("Workflow complete")

        # Response text formulation (concise, verifiable, without chain-of-thought)
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
