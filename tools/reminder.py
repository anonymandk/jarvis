from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "reminder", "description": "Sets a timed reminder using Task Scheduler.", "parameters": {"type": "OBJECT", "properties": {"date": {"type": "STRING", "description": "Date in YYYY-MM-DD format"}, "time": {"type": "STRING", "description": "Time in HH:MM format (24h)"}, "message": {"type": "STRING", "description": "Reminder message text"}}, "required": ["date", "time", "message"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "reminder", args)
