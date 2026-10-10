from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "dev_agent", "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.", "parameters": {"type": "OBJECT", "properties": {"description": {"type": "STRING", "description": "What the project should do"}, "language": {"type": "STRING", "description": "Programming language (default: python)"}, "project_name": {"type": "STRING", "description": "Optional project folder name"}, "timeout": {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"}}, "required": ["description"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "dev_agent", args)
