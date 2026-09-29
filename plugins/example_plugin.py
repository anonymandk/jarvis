"""Example plugin demonstrating how to extend JARVIS with custom tools."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from tools.registry import ToolRegistry


# Type alias matching the registry's expectation
ExecuteFn = Callable[[Any, Dict[str, Any]], Awaitable[Dict[str, Any]]]


def register(tool_registry: ToolRegistry) -> None:
    """Register the example ping tool.

    Args:
        tool_registry: The global tool registry instance.
    """
    tool_registry.register_tool(
        name="ping",
        declaration={
            "name": "ping",
            "description": "Responds with pong to test plugin tool loading.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": [],
            },
        },
        execute_fn=_ping_execute,
    )


async def _ping_execute(_ctx: Any, _args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the ping tool.

    Returns a simple pong response.
    """
    return {"result": "pong"}