from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "youtube_video", "description": "Controls YouTube. Use for: playing videos, summarizing a video's content, getting video info, or showing trending videos.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"}, "query": {"type": "STRING", "description": "Search query for play action"}, "save": {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"}, "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"}, "url": {"type": "STRING", "description": "Video URL for get_info action"}}, "required": []}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "youtube_video", args)
