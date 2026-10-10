from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "save_memory", "description": "Save an important personal fact about the user to long-term memory. Call this silently whenever the user reveals something worth remembering: name, age, city, job, preferences, hobbies, relationships, projects, or future plans. Do NOT call for: weather, reminders, searches, or one-time commands. Do NOT announce that you are saving — just call it silently. Values must be in English regardless of the conversation language.", "parameters": {"type": "OBJECT", "properties": {"category": {"type": "STRING", "description": "identity — name, age, birthday, city, job, language, nationality | preferences — favorite food/color/music/film/game/sport, hobbies | projects — active projects, goals, things being built | relationships — friends, family, partner, colleagues | wishes — future plans, things to buy, travel dreams | notes — habits, schedule, anything else worth remembering"}, "key": {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"}, "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"}}, "required": ["category", "key", "value"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "save_memory", args)
