import pytest
from app.tools.weather import get_weather
from app.tools.places import search_places
from app.tools.reminder import create_reminder
from app.db import init_db

@pytest.mark.asyncio
async def test_get_weather():
    res = await get_weather("Campus Town")
    assert "temperature" in res
    assert "weather_condition" in res
    assert "recommendation" in res

@pytest.mark.asyncio
async def test_search_places():
    res = await search_places("lounge", "Campus Town")
    assert isinstance(res, list)
    assert len(res) > 0
    assert "name" in res[0]

def test_create_reminder_unconfirmed():
    init_db()
    session_id = "test_sess_tools"
    res = create_reminder(session_id, "Study Session", "6:00 PM", confirmed=False)
    assert res["status"] == "pending_confirmation"
    assert "pending_action" in res
    assert res["pending_action"]["tool_name"] == "create_reminder"
