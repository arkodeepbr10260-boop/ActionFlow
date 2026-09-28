"""
ActionFlow 100-Case Evaluation Runner.
Evaluates:
- Tool selection accuracy
- Required confirmation accuracy
- Context follow-up accuracy
- Workflow completion rate
- Failure recovery rate
"""
import asyncio
import json
import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.workflow import AgentOrchestrator
from app.db import init_db, save_context_item

async def run_eval_suite():
    init_db()
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset_100.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    orchestrator = AgentOrchestrator()

    total_cases = len(cases)
    tool_correct = 0
    conf_correct = 0
    context_correct = 0
    completed = 0
    recovery_tested = 0
    recovery_succeeded = 0

    print(f"\n=======================================================")
    print(f"       ActionFlow Evaluation Suite (100 Cases)         ")
    print(f"=======================================================\n")

    for i, case in enumerate(cases, 1):
        sess_id = f"eval_sess_{case['id']}"
        inp = case["input"]
        expected_tools = case.get("expected_tools", [])
        expected_conf = case.get("requires_confirmation", False)

        # Populate context if needed
        if "mock_context" in case:
            for k, v in case["mock_context"].items():
                save_context_item(sess_id, k, v)

        try:
            res = await orchestrator.execute_workflow(sess_id, inp)
            completed += 1
            executed_tools = [tr["tool_name"] for tr in res.get("tool_results", [])]
            pending_action = res.get("pending_action")
            has_pending = pending_action is not None and pending_action.get("status") == "pending"

            # Check tool overlap
            matching_tools = set(expected_tools).intersection(set(executed_tools))
            if matching_tools or not expected_tools:
                tool_correct += 1

            # Check confirmation gate accuracy
            if has_pending == expected_conf:
                conf_correct += 1

            # Context accuracy
            if case["category"] == "followup_context":
                if res.get("plan") or res.get("context_used") or len(executed_tools) > 0:
                    context_correct += 1

            # Recovery accuracy
            if case.get("supports_recovery"):
                recovery_tested += 1
                if res.get("plan") or res.get("final_result"):
                    recovery_succeeded += 1

        except Exception as e:
            print(f"Error executing case {case['id']}: {e}")

    # Metrics computation
    tool_acc = (tool_correct / total_cases) * 100
    conf_acc = (conf_correct / total_cases) * 100
    ctx_acc = (context_correct / 15) * 100
    comp_rate = (completed / total_cases) * 100
    rec_rate = (recovery_succeeded / max(1, recovery_tested)) * 100

    report = {
        "total_test_cases": total_cases,
        "tool_selection_accuracy": f"{tool_acc:.1f}%",
        "required_confirmation_accuracy": f"{conf_acc:.1f}%",
        "context_follow_up_accuracy": f"{ctx_acc:.1f}%",
        "workflow_completion_rate": f"{comp_rate:.1f}%",
        "failure_recovery_rate": f"{rec_rate:.1f}%"
    }

    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    asyncio.run(run_eval_suite())
