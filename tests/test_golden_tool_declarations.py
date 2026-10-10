"""Test that tool declarations match the golden fixture from Phase 0."""

import json
from pathlib import Path


def test_tool_declarations_match_golden():
    """Compare current tool declarations with golden fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "golden_tool_declarations.json"
    
    with open(fixture_path, "r") as f:
        golden = json.load(f)
    
    # Get current declarations from registry
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.registry import registry
    registry._internal_discover()
    
    current = []
    for name in sorted(registry._declarations.keys()):
        decl = registry._declarations[name]
        current.append({
            "name": decl["name"],
            "description": decl["description"],
            "parameters": decl["parameters"]
        })
    
    golden_by_name = {declaration["name"]: declaration for declaration in golden}
    assert len(current) == len(golden_by_name), (
        f"Tool count mismatch: current={len(current)}, golden={len(golden_by_name)}"
    )
    assert {declaration["name"] for declaration in current} == set(golden_by_name), (
        "Tool names do not match the golden fixture"
    )

    for declaration in current:
        expected = golden_by_name[declaration["name"]]
        assert declaration["description"] == expected["description"], (
            f"Description mismatch for {declaration['name']}"
        )
        assert declaration["parameters"] == expected["parameters"], (
            f"Parameters mismatch for {declaration['name']}"
        )


if __name__ == "__main__":
    test_tool_declarations_match_golden()
    print("Golden fixture test passed!")
