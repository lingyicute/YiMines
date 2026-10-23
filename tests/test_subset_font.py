"""Regression tests for scripts/subset_font.py."""
from contextlib import redirect_stdout
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import subset_font  # noqa: E402


class SubsetFontCheckModeTests(unittest.TestCase):
    def test_check_mode_does_not_write_generated_font_or_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_path = root / "page.html"
            original_html = "<style>@font-face { font-family: 'Nebulove'; }</style>\n<p>你好</p>"
            html_path.write_text(original_html, encoding="utf-8")
            source_font = root / "source.woff2"
            source_font.write_bytes(b"12345678")
            output_dir = root / "scripts"
            output_dir.mkdir()

            def build_subset(chars, _font_path):
                return b"1234", {ord(char) for char in chars}

            stdout = io.StringIO()
            with patch.object(subset_font, "HERE", str(output_dir)), \
                    patch.object(subset_font, "build_subset", side_effect=build_subset), \
                    patch.object(sys, "argv", ["subset_font.py", "--html", str(html_path), "--ttf", str(source_font), "--check"]), \
                    redirect_stdout(stdout):
                subset_font.main()

            self.assertEqual(html_path.read_text(encoding="utf-8"), original_html)
            self.assertFalse((output_dir / "Nebulove-subset.woff2").exists())
            self.assertIn("--check：未写入字体或页面。", stdout.getvalue())
            self.assertIn("50.0% 于原字体", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
