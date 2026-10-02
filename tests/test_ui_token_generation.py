"""Keep the generated desktop and web token files in sync with design/tokens.json."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UiTokenGenerationTests(unittest.TestCase):
    def test_python_and_css_tokens_are_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_ui_tokens.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_web_styles_import_generated_tokens(self):
        stylesheet = (ROOT / "web" / "src" / "app" / "globals.css").read_text(encoding="utf-8")
        self.assertIn('@import "./design-tokens.css";', stylesheet)


if __name__ == "__main__":
    unittest.main()
