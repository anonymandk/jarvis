from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "desktop_control", "description": "Controls the desktop: wallpaper, organize, clean, list, stats.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"}, "path": {"type": "STRING", "description": "Image path for wallpaper"}, "url": {"type": "STRING", "description": "Image URL for wallpaper_url"}, "mode": {"type": "STRING", "description": "by_type or by_date for organize"}, "task": {"type": "STRING", "description": "Natural language desktop task"}}, "required": ["action"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "desktop_control", args)
