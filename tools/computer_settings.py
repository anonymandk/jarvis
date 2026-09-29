from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "computer_settings", "description": "Controls the computer: volume, brightness, window management, keyboard shortcuts, typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. Use for ANY single computer control command. NEVER route to agent_task.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "The action to perform"}, "description": {"type": "STRING", "description": "Natural language description of what to do"}, "value": {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}}, "required": []}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "computer_settings", args)
