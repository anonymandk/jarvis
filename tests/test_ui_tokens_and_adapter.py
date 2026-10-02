from __future__ import annotations

import ast
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from core.qa_audit import repository_findings
from ui.adapters.events import JarvisEventMapper, normalize_state
from ui.theme.tokens import (
    SPECIAL_TEXT_PAIRS,
    SURFACE_COLOR_KEYS,
    THEME_PALETTES,
    TEXT_COLOR_KEYS,
    TOKENS,
    contrast_failures,
    contrast_ratio,
)


ROOT = Path(__file__).resolve().parents[1]


class UiTokenTests(unittest.TestCase):
    def test_only_token_module_contains_hexadecimal_ui_colors(self):
        literals = []
        for path in (ROOT / "ui").rglob("*.py"):
            if path == ROOT / "ui" / "theme" / "tokens.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"#[0-9A-Fa-f]{3,8}\b", line):
                    literals.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(literals, [])

    def test_only_token_module_contains_numeric_rgb_or_rgba_colors(self):
        literals = []
        pattern = re.compile(r"\brgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+", re.IGNORECASE)
        for path in (ROOT / "ui").rglob("*.py"):
            if path == ROOT / "ui" / "theme" / "tokens.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    literals.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(literals, [])

    def test_ui_design_geometry_and_typography_use_tokens(self):
        violations = []
        numeric_geometry_methods = {"setSpacing", "setContentsMargins", "addSpacing", "setDuration"}
        raw_css_dimensions = re.compile(
            r"\b(?:border-radius|padding(?:-[a-z-]+)?|margin(?:-[a-z-]+)?|font-size|letter-spacing|line-height|font-weight)\s*:\s*[+-]?\d+(?:\.\d+)?(?:px|pt|em|rem|%)?\b",
            re.IGNORECASE,
        )

        for path in (ROOT / "ui").rglob("*.py"):
            if path == ROOT / "ui" / "theme" / "tokens.py":
                continue
            source = path.read_text(encoding="utf-8")
            relative = path.relative_to(ROOT)
            try:
                tree = ast.parse(source, filename=str(relative))
            except SyntaxError as error:
                violations.append(f"{relative}:{error.lineno}: cannot parse UI source")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "_lbl":
                    defaults = node.args.defaults
                    if any(isinstance(value, ast.Constant) and type(value.value) is int for value in defaults):
                        violations.append(f"{relative}:{node.lineno}: numeric _lbl font-size default")
                if not isinstance(node, ast.Call):
                    continue
                method = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else ""
                )
                if method in {"QFont", "_QFont"} and node.args:
                    family = node.args[0]
                    if isinstance(family, ast.Constant) and isinstance(family.value, str):
                        violations.append(f"{relative}:{node.lineno}: literal QFont family")
                if method in {"QFont", "_QFont"} and len(node.args) >= 2:
                    size = node.args[1]
                    if isinstance(size, ast.Constant) and type(size.value) is int:
                        violations.append(f"{relative}:{node.lineno}: numeric QFont size")
                if method == "_lbl" and len(node.args) >= 2:
                    size = node.args[1]
                    if isinstance(size, ast.Constant) and type(size.value) is int:
                        violations.append(f"{relative}:{node.lineno}: numeric _lbl font size")
                if method in numeric_geometry_methods:
                    if any(isinstance(arg, ast.Constant) and type(arg.value) is int for arg in node.args):
                        violations.append(f"{relative}:{node.lineno}: numeric {method} value")
                if method == "setLetterSpacing" and any(
                    isinstance(arg, ast.Constant) and type(arg.value) in {int, float}
                    for arg in node.args
                ):
                    violations.append(f"{relative}:{node.lineno}: raw letter spacing")
                if method == "setEasingCurve":
                    expression = ast.get_source_segment(source, node.args[0]) if node.args else ""
                    if "TOKENS.motion_easing" not in expression:
                        violations.append(f"{relative}:{node.lineno}: easing must use a token")

            for number, line in enumerate(source.splitlines(), 1):
                if raw_css_dimensions.search(line):
                    violations.append(f"{relative}:{number}: raw pixel value in UI stylesheet")
                if re.search(r"\bfont-family\s*:", line, re.IGNORECASE) and not re.search(
                    r"\{(?:UI_FONT|TECH_FONT|TOKENS\.fonts\[[^]]+\])\}", line
                ):
                    violations.append(f"{relative}:{number}: stylesheet font family must use a token")
                if re.search(r"\bletter-spacing\s*:", line, re.IGNORECASE) and "TOKENS.letter_spacing" not in line:
                    violations.append(f"{relative}:{number}: stylesheet letter spacing must use a token")
                if re.search(r"\b(?:font-weight|line-height)\s*:", line, re.IGNORECASE) and not re.search(
                    r"\{TOKENS\.(?:font_weights|line_height_percent)\[", line
                ):
                    violations.append(f"{relative}:{number}: stylesheet weight/line-height must use a token")

        self.assertEqual(violations, [])

    def test_every_theme_text_and_focus_token_meets_contrast_threshold(self):
        self.assertEqual(contrast_failures(), [])
        for palette in THEME_PALETTES.values():
            for role in TEXT_COLOR_KEYS:
                for surface in SURFACE_COLOR_KEYS:
                    self.assertGreaterEqual(contrast_ratio(palette[role], palette[surface]), 4.5)
            for surface in SURFACE_COLOR_KEYS:
                self.assertGreaterEqual(contrast_ratio(palette["PRI"], palette[surface]), 3.0)

    def test_design_tokens_have_semantic_families(self):
        self.assertEqual(TOKENS.fonts["body"], "Space Grotesk")
        self.assertEqual(TOKENS.fonts["mono"], "JetBrains Mono")
        self.assertEqual(TOKENS.fonts["emoji"], "Segoe UI Emoji")
        self.assertEqual(TOKENS.font_family_aliases["Courier New"], "mono")
        self.assertEqual(TOKENS.font_weights["bold"], 700)
        self.assertEqual(TOKENS.line_height_percent["comfortable"], 160)
        self.assertEqual(TOKENS.spacing["md"], 12)
        self.assertEqual(TOKENS.radii["md"], 6)
        self.assertEqual(TOKENS.letter_spacing["tight"], 0.8)
        self.assertEqual(TOKENS.opacity["active_card"], 18)
        self.assertEqual(TOKENS.motion_ms["state"], 240)
        self.assertEqual(TOKENS.motion_easing["standard"], "OutQuart")

    def test_warning_toast_text_contrast_is_checked_for_every_theme(self):
        foreground, background = SPECIAL_TEXT_PAIRS["warning toast"]
        for name, palette in THEME_PALETTES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast_ratio(palette[foreground], palette[background]), 4.5)

    def test_stylesheet_text_colors_are_covered_by_contrast_roles(self):
        used = set()
        for path in (ROOT / "ui").rglob("*.py"):
            if path == ROOT / "ui" / "theme" / "tokens.py":
                continue
            source = path.read_text(encoding="utf-8")
            used.update(re.findall(r"(?<![\w-])color\s*:\s*\{C\.([A-Z_]+)\}", source))
        # Border roles are used for separator rules here, not text foregrounds.
        used.difference_update({"BORDER", "BORDER_B"})
        checked = set(TEXT_COLOR_KEYS) | {foreground for foreground, _ in SPECIAL_TEXT_PAIRS.values()}
        self.assertLessEqual(used, checked)

    def test_file_category_colors_preserve_the_existing_visual_mapping(self):
        self.assertEqual(dict(TOKENS.file_category_colors), {
            "image": "#00d4ff", "video": "#ff6b00", "audio": "#cc44ff",
            "pdf": "#ff4444", "word": "#4488ff", "excel": "#44bb44",
            "code": "#ffcc00", "archive": "#ff8844", "pptx": "#ff6622",
            "text": "#aaaaaa", "data": "#88ddff", "unknown": "#888888",
        })

    def test_ui_has_no_engine_or_vendor_imports(self):
        forbidden = []
        for path in (ROOT / "ui").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                elif isinstance(node, ast.Call) and node.args:
                    function = node.func
                    dynamic = (
                        isinstance(function, ast.Name) and function.id == "__import__"
                    ) or (
                        isinstance(function, ast.Attribute)
                        and function.attr == "import_module"
                        and isinstance(function.value, ast.Name)
                        and function.value.id == "importlib"
                    )
                    modules = [str(node.args[0].value)] if dynamic and isinstance(
                        node.args[0], ast.Constant
                    ) else []
                else:
                    continue
                if any(module == "actions" or module.startswith("actions.") or module == "google" or module.startswith("google.") for module in modules):
                    forbidden.append(str(path.relative_to(ROOT)))
        self.assertEqual(forbidden, [])

    def test_repository_audit_has_no_color_literal_finding(self):
        findings = repository_findings(ROOT)
        self.assertFalse(any(finding.subsystem == "Theming" for finding in findings))

    def test_repository_audit_has_no_ui_dependency_boundary_finding(self):
        findings = repository_findings(ROOT)
        self.assertFalse(any(finding.subsystem == "Architecture" for finding in findings))


class JarvisEventMapperTests(unittest.TestCase):
    def setUp(self):
        self.mapper = JarvisEventMapper(
            session_id="session-test",
            clock=lambda: datetime(2026, 10, 1, 12, 34, 56, 789000, timezone.utc),
        )

    def test_state_alias_table_normalizes_only_known_states(self):
        cases = (
            ("IDLE", "idle"),
            ("STANDING BY", "idle"),
            ("LISTENING", "listening"),
            ("THINKING", "processing"),
            ("PROCESSING", "processing"),
            ("SPEAKING", "speaking"),
            ("RECONNECTING", "reconnecting"),
            ("ERROR", "error"),
            ("MUTED", "muted"),
            ("NOT_A_STATE", None),
        )
        mapper = JarvisEventMapper(session_id="state-table")
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_state(raw), expected)
                event = mapper.state(raw)
                if expected is None:
                    self.assertIsNone(event)
                else:
                    self.assertEqual(event["type"], "state")
                    self.assertEqual(event["payload"]["state"], expected)

    def test_existing_client_calls_use_v1_envelope_and_sequence(self):
        state = self.mapper.client_call("set_state", "THINKING")
        partial = self.mapper.client_call("show_subtitle", "Olá")
        final = self.mapper.client_call("write_log", "Jarvis: Pronto")
        self.assertEqual([state["seq"], partial["seq"], final["seq"]], [1, 2, 3])
        self.assertEqual(state["payload"]["state"], "processing")
        self.assertEqual(
            {key: partial["payload"][key] for key in ("speaker", "text", "final")},
            {"speaker": "assistant", "text": "Olá", "final": False},
        )
        self.assertEqual(final["payload"]["speaker"], "assistant")
        self.assertEqual(partial["payload"]["turn_id"], final["payload"]["turn_id"])
        self.assertEqual(state["ts"], "2026-10-01T12:34:56.789Z")
        self.assertTrue(all(event["v"] == 1 and event["session_id"] == "session-test" for event in (state, partial, final)))

    def test_log_prefixes_are_mapped_without_inferring_tool_events(self):
        user = self.mapper.log("You: Pesquise isso")
        warning = self.mapper.log("WARN: Serviço lento")
        error = self.mapper.log("ERR: Falha de rede")
        self.assertEqual((user["type"], user["payload"]["speaker"]), ("transcript", "user"))
        self.assertEqual((warning["type"], warning["payload"]["level"]), ("log", "warning"))
        self.assertEqual((error["type"], error["payload"]["level"]), ("log", "error"))
        self.assertNotIn("tool_call", {user["type"], warning["type"], error["type"]})

    def test_engine_order_clear_stream_then_logged_turn_shares_turn_id(self):
        cleared = self.mapper.clear_subtitle()
        partial = self.mapper.subtitle("O processo concluiu.")
        user = self.mapper.log("You: O que aconteceu?")
        final = self.mapper.log("Jarvis: O processo concluiu.")
        turn_ids = {
            event["payload"]["turn_id"]
            for event in (user, partial, final, cleared)
        }
        self.assertEqual(len(turn_ids), 1)
        self.assertTrue(all(event["payload"]["turn_id"] for event in (user, partial, final, cleared)))
        next_user = self.mapper.log("You: Outra pergunta")
        self.assertNotEqual(next_user["payload"]["turn_id"], final["payload"]["turn_id"])

    def test_concurrent_events_receive_unique_monotonic_sequence_numbers(self):
        mapper = JarvisEventMapper(session_id="concurrent")
        with ThreadPoolExecutor(max_workers=8) as executor:
            events = list(executor.map(
                lambda index: mapper.metric(name="sample", value=index, unit="count"),
                range(100),
            ))
        self.assertEqual(sorted(event["seq"] for event in events), list(range(1, 101)))

    def test_missing_metric_stays_null_and_structured_events_are_explicit(self):
        metric = self.mapper.metric(name="rtt", value=None, unit="ms")
        tool = self.mapper.tool_call(call_id="tool-1", name="web_search", status="running")
        error = self.mapper.error(code="network", message="Sem conexão", recoverable=True)
        self.assertIsNone(metric["payload"]["value"])
        self.assertEqual(tool["payload"]["status"], "running")
        self.assertTrue(error["payload"]["recoverable"])

    def test_non_event_client_methods_are_not_silently_reinterpreted(self):
        self.assertIsNone(self.mapper.client_call("handle_ui_command", "open_settings"))
        self.assertIsNone(self.mapper.client_call("set_state", "CONNECTED"))


if __name__ == "__main__":
    unittest.main()
