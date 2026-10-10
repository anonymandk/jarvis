from __future__ import annotations

from typing import Any

declaration: dict[str, Any] = {"name": "flight_finder", "description": "Searches Google Flights and speaks the best options.", "parameters": {"type": "OBJECT", "properties": {"origin": {"type": "STRING", "description": "Departure city or airport code"}, "destination": {"type": "STRING", "description": "Arrival city or airport code"}, "date": {"type": "STRING", "description": "Departure date (any format)"}, "return_date": {"type": "STRING", "description": "Return date for round trips"}, "passengers": {"type": "INTEGER", "description": "Number of passengers (default: 1)"}, "cabin": {"type": "STRING", "description": "economy | premium | business | first"}, "save": {"type": "BOOLEAN", "description": "Save results to Notepad"}}, "required": ["origin", "destination", "date"]}}

async def execute(ctx: Any, args: dict[str, Any]) -> dict[str, Any]:
    from tools.impl import execute as _execute
    return await _execute(ctx, "flight_finder", args)
