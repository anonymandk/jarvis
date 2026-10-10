from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "argus_ui_control", "description": "Changes ARGUS's own interface. Use when the user asks to open or close the Command Center, change the theme or graphics quality, open settings, enter compact mode, toggle fullscreen, or show shortcuts.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["open_command_center", "close_command_center", "change_theme", "change_graphics_quality", "open_settings", "compact_mode", "fullscreen", "show_shortcuts"], "description": "The interface action to perform."}, "theme": {"type": "STRING", "enum": ["arc_reactor", "stealth_red", "vibranium_purple", "nanotech_gold", "platinum"], "description": "Required for change_theme."}, "graphics_quality": {"type": "STRING", "enum": ["low", "medium", "high"], "description": "Required for change_graphics_quality. Low favors performance, medium is balanced, and high enables full visual detail."}}, "required": ["action"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "argus_ui_control", args)
