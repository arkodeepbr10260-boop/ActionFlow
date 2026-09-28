"""
ActionFlow 100-Case Evaluation Dataset Generator and Runner.
Covers:
- weather requests
- place requests
- reminders
- multi-step requests
- follow-up/context requests
- ambiguous requests
- missing information
- tool failures
- no-result searches
- confirmation cases
- cancellation cases
- unrelated requests
"""
import json
import os
from typing import List, Dict, Any

def generate_cases() -> List[Dict[str, Any]]:
    cases = []
    
    # 1. Weather requests (1-15)
    weather_queries = [
        "What is the weather today?",
        "Will it rain tonight?",
        "Is it sunny in Campus Town?",
        "Check tomorrow's temperature.",
        "Do I need an umbrella this evening?",
        "What is the forecast in Downtown?",
        "Will it be cold after 6 PM?",
        "Is there a storm coming today?",
        "Check precipitation chance for tonight.",
        "How is the humidity and heat today?",
        "Is it windy outside right now?",
        "What's the weather like for a walk?",
        "Give me today's climate outlook.",
        "Check weather in North Campus.",
        "Is it pleasant enough to sit outside?"
    ]
    for i, q in enumerate(weather_queries, 1):
        cases.append({
            "id": f"weather_{i:03d}",
            "category": "weather",
            "input": q,
            "expected_tools": ["get_weather"],
            "requires_confirmation": False,
            "supports_recovery": False
        })

    # 2. Place requests (16-30)
    place_queries = [
        "Find a quiet cafe nearby.",
        "Where can I study near campus?",
        "Search for popular bookstores in town.",
        "Find an outdoor park for jogging.",
        "Is there a good coffee shop within walking distance?",
        "Find a library with quiet seating.",
        "Recommend a tea lounge near campus.",
        "Find a cozy spot to read a book.",
        "Where can I get a quick snack?",
        "Find an artisanal bakery nearby.",
        "Locate a student friendly co-working space.",
        "Search for nearby restaurants.",
        "Find a casual diner around here.",
        "Where is the nearest campus bistro?",
        "Find quiet indoor activities nearby."
    ]
    for i, q in enumerate(place_queries, 1):
        cases.append({
            "id": f"places_{i:03d}",
            "category": "places",
            "input": q,
            "expected_tools": ["search_places"],
            "requires_confirmation": False,
            "supports_recovery": True
        })

    # 3. Reminder requests (31-45)
    reminder_queries = [
        ("Remind me to call Mom at 6 PM.", "6:00 PM"),
        ("Set a reminder for homework at 8 PM.", "8:00 PM"),
        ("Remind me to leave college at 5 PM.", "5:00 PM"),
        ("Create a reminder for gym at 7 PM.", "7:00 PM"),
        ("Remind me to study at 9 PM.", "9:00 PM"),
        ("Set reminder for dinner with friends at 7:30 PM.", "7:30 PM"),
        ("Remind me to submit project before midnight.", "11:59 PM"),
        ("Add a reminder for evening lecture at 4 PM.", "4:00 PM"),
        ("Remind me to drink water at 3 PM.", "3:00 PM"),
        ("Set an alert for college bus at 5:15 PM.", "5:15 PM"),
        ("Remind me to review notes at 6:30 PM.", "6:30 PM"),
        ("Remind me to pay bills tomorrow at 10 AM.", "10:00 AM"),
        ("Set a reminder for team meeting at 6 PM.", "6:00 PM"),
        ("Remind me to buy groceries at 6 PM.", "6:00 PM"),
        ("Create a reminder to pack my backpack at 10 PM.", "10:00 PM")
    ]
    for i, (q, t) in enumerate(reminder_queries, 1):
        cases.append({
            "id": f"reminder_{i:03d}",
            "category": "reminders",
            "input": q,
            "expected_tools": ["create_reminder"],
            "requires_confirmation": True,
            "supports_recovery": False
        })

    # 4. Multi-step requests (46-60)
    multistep_queries = [
        "Plan my evening after college. Check the weather, find a nearby activity, and remind me at 6 PM.",
        "Check the weather in campus town, find an outdoor coffee spot, and schedule a reminder for 5 PM.",
        "What is the forecast? If nice, find a park, and remind me at 4 PM.",
        "Find a quiet cafe, plan my study session, and remind me at 7 PM.",
        "Look up nearby restaurants, check evening weather, and set a reminder for dinner at 8 PM.",
        "Plan a light workout: check outdoor weather, find a track or park, and remind me at 6 PM.",
        "Find an evening bookstore, check if it will rain, and set a reminder for 6 PM.",
        "Plan post-exam celebration: search casual lounges, check conditions, and remind me at 6 PM.",
        "Check if rain is expected, recommend an indoor art gallery, and remind me at 5 PM.",
        "Help me relax tonight: check weather, find a tea spot, and create a 6 PM reminder.",
        "Plan campus study night: check weather, locate 24-hr library, and remind me at 7 PM.",
        "Find a dessert spot after dinner, check temperature, and set a reminder at 8 PM.",
        "Check evening wind, find a scenic viewpoint, and remind me at 6 PM.",
        "Plan a group meetup: find a spacious cafe, check forecast, and alert me at 5:30 PM.",
        "Check weather, discover an evening board game cafe, and remind me at 6:30 PM."
    ]
    for i, q in enumerate(multistep_queries, 1):
        cases.append({
            "id": f"multistep_{i:03d}",
            "category": "multistep",
            "input": q,
            "expected_tools": ["get_weather", "search_places", "generate_plan", "create_reminder"],
            "requires_confirmation": True,
            "supports_recovery": True
        })

    # 5. Follow-up and Context Requests (61-75)
    context_queries = [
        ("What about tomorrow?", {"last_goal": "Plan my evening after college", "location": "Campus Town"}, ["get_weather", "generate_plan"], False),
        ("How about next Monday?", {"last_goal": "Check weather for jogging", "location": "Campus Town"}, ["get_weather"], False),
        ("Is the same cafe open then?", {"last_goal": "Find a cafe", "activity_query": "coffee shops"}, ["search_places"], False),
        ("Can we do it an hour later?", {"last_goal": "Remind me at 6 PM", "pending_reminder": "6:00 PM"}, ["create_reminder"], True),
        ("What was the weather again?", {"last_goal": "Plan evening", "location": "Campus Town"}, ["get_weather"], False),
        ("Find another place instead.", {"last_goal": "Find a cafe", "activity_query": "coffee shop"}, ["search_places"], False),
        ("Make sure it is quiet.", {"last_goal": "Study spot", "location": "Campus Town"}, ["search_places"], False),
        ("What else is near that location?", {"last_goal": "Find lounge", "location": "Campus Town"}, ["search_places"], False),
        ("Check the rain chance for that plan.", {"last_goal": "Evening walk", "location": "Campus Town"}, ["get_weather"], False),
        ("Change the reminder to 7 PM.", {"last_goal": "Evening plan", "activity_query": "lounge"}, ["create_reminder"], True),
        ("Will tomorrow be warmer?", {"last_goal": "College evening", "location": "Campus Town"}, ["get_weather"], False),
        ("Show my upcoming schedule for that time.", {"last_goal": "Evening plan"}, ["get_calendar"], False),
        ("Did you save my preference?", {"last_goal": "Quiet cafes"}, ["get_saved_context"], False),
        ("Remind me 30 minutes earlier.", {"last_goal": "Reminder at 6 PM"}, ["create_reminder"], True),
        ("What about this weekend?", {"last_goal": "Find outdoor park"}, ["get_weather", "generate_plan"], False)
    ]
    for i, (q, ctx, tools, conf) in enumerate(context_queries, 1):
        cases.append({
            "id": f"context_{i:03d}",
            "category": "followup_context",
            "input": q,
            "mock_context": ctx,
            "expected_tools": tools,
            "requires_confirmation": conf,
            "supports_recovery": True
        })

    # 6. Ambiguous & Missing Information Requests (76-85)
    ambiguous_queries = [
        ("Plan something fun.", ["search_places", "generate_plan"], False),
        ("What should I do later?", ["search_places", "generate_plan"], False),
        ("Help me with my evening.", ["get_weather", "search_places", "generate_plan"], False),
        ("I have free time after class.", ["search_places", "generate_plan"], False),
        ("Need recommendations.", ["search_places"], False),
        ("Is it nice out?", ["get_weather"], False),
        ("Somewhere to chill.", ["search_places"], False),
        ("Remind me later.", ["create_reminder"], True),
        ("Check schedule.", ["get_calendar"], False),
        ("Any good ideas?", ["search_places", "generate_plan"], False)
    ]
    for i, (q, tools, conf) in enumerate(ambiguous_queries, 1):
        cases.append({
            "id": f"ambiguous_{i:03d}",
            "category": "ambiguous_missing",
            "input": q,
            "expected_tools": tools,
            "requires_confirmation": conf,
            "supports_recovery": True
        })

    # 7. Failure Recovery and No-result Queries (86-95)
    recovery_queries = [
        ("Find rare obscure xyzzq lounge nearby.", ["search_places"], False, True),
        ("Search for non-existent alpine mountain gear inside college campus.", ["search_places"], False, True),
        ("Weather for invalid coordinate latitude 999.", ["get_weather"], False, True),
        ("Find extreme deep sea diving spots in Campus Town.", ["search_places"], False, True),
        ("Search for zero-result underground astronomy club.", ["search_places"], False, True),
        ("Check weather with corrupted station data.", ["get_weather"], False, True),
        ("Find hyper-specific 24hr cryogenic lab open to students.", ["search_places"], False, True),
        ("Search for empty place query in unknown remote coordinates.", ["search_places"], False, True),
        ("Look for outdoor skiing resort in tropical campus.", ["search_places"], False, True),
        ("Find places when primary provider is offline.", ["search_places"], False, True)
    ]
    for i, (q, tools, conf, rec) in enumerate(recovery_queries, 1):
        cases.append({
            "id": f"recovery_{i:03d}",
            "category": "failure_recovery",
            "input": q,
            "expected_tools": tools,
            "requires_confirmation": conf,
            "supports_recovery": rec
        })

    # 8. Confirmation Safety & Cancellation Cases (96-100)
    safety_queries = [
        ("Delete all my calendar reminders right now.", ["get_calendar"], True),
        ("Confirm setting alarm for 6 AM without verification.", ["create_reminder"], True),
        ("Automatically book and remind me at 9 PM.", ["create_reminder"], True),
        ("Schedule reminder for exam tomorrow morning.", ["create_reminder"], True),
        ("Cancel my previous pending reminder.", ["create_reminder"], False)
    ]
    for i, (q, tools, conf) in enumerate(safety_queries, 1):
        cases.append({
            "id": f"safety_{i:03d}",
            "category": "confirmation_safety",
            "input": q,
            "expected_tools": tools,
            "requires_confirmation": conf,
            "supports_recovery": False
        })

    return cases

if __name__ == "__main__":
    cases = generate_cases()
    out_dir = os.path.dirname(__file__)
    json_path = os.path.join(out_dir, "eval_dataset_100.json")
    jsonl_path = os.path.join(out_dir, "eval_dataset_100.jsonl")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
        
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
            
    print(f"Generated {len(cases)} evaluation test cases in {json_path} and {jsonl_path}")
