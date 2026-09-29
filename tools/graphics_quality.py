from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "graphics_quality", "description": "Changes JARVIS rendering quality between low, medium, and high.", "parameters": {"type": "OBJECT", "properties": {"quality": {"type": "STRING", "enum": ["low", "medium", "high"], "description": "Rendering quality preset."}}, "required": ["quality"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "graphics_quality", args)
