from typing import Dict, Any, List

def generate_plan(user_goal: str, tool_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured plan based on user goal and collected tool results.
    """
    weather = tool_results.get("weather", {})
    places = tool_results.get("places", [])
    
    # Formulate step by step plan
    selected_place = places[0] if places else {"name": "Central Campus Lounge", "category": "Relaxation"}
    weather_desc = weather.get("weather_condition", "Clear")
    temp = weather.get("temperature", "22°C")
    
    steps = [
        {
            "step": 1,
            "title": "Weather Check",
            "details": f"Conditions are {weather_desc} ({temp}). {weather.get('recommendation', '')}"
        },
        {
            "step": 2,
            "title": "Evening Activity",
            "details": f"Visit {selected_place.get('name')} ({selected_place.get('category', 'Activity')}) at {selected_place.get('address', 'Nearby')}"
        },
        {
            "step": 3,
            "title": "Schedule & Reminder",
            "details": "Set a reminder at 6:00 PM for the planned evening activity."
        }
    ]
    
    summary = f"Plan created for '{user_goal}': Head to {selected_place.get('name')} after college. Weather is {weather_desc} ({temp}). Reminder set for 6:00 PM."
    
    return {
        "goal": user_goal,
        "summary": summary,
        "steps": steps,
        "recommended_place": selected_place,
        "weather_info": weather
    }
