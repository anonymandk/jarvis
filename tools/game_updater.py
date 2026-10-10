from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "game_updater", "description": "THE ONLY tool for ANY Steam or Epic Games request. Use for: installing, downloading, updating games, listing installed games, checking download status, scheduling updates. ALWAYS call directly for any Steam/Epic/game request. NEVER use agent_task, browser_control, or web_search for Steam/Epic.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"}, "platform": {"type": "STRING", "description": "steam | epic | both (default: both)"}, "game_name": {"type": "STRING", "description": "Game name (partial match supported)"}, "app_id": {"type": "STRING", "description": "Steam AppID for install (optional)"}, "hour": {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"}, "minute": {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"}, "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"}}, "required": []}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "game_updater", args)
