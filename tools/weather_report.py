from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "weather_report", "description": "Gives the weather report to user", "parameters": {"type": "OBJECT", "properties": {"city": {"type": "STRING", "description": "City name"}}, "required": ["city"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "weather_report", args)
