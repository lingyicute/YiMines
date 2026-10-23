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


def _fake_build_subset(chars, _font_path):
    return b"1234", {ord(char) for char in chars}


class SubsetFontTests(unittest.TestCase):
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
            explicit_out = root / "out" / "subset.woff2"

            stdout = io.StringIO()
            with patch.object(subset_font, "HERE", str(output_dir)), \
                    patch.object(subset_font, "build_subset", side_effect=_fake_build_subset), \
                    patch.object(
                        sys, "argv",
                        ["subset_font.py", "--html", str(html_path), "--ttf", str(source_font),
                         "--output", str(explicit_out), "--check"],
                    ), \
                    redirect_stdout(stdout):
                subset_font.main()

            self.assertEqual(html_path.read_text(encoding="utf-8"), original_html)
            self.assertFalse((output_dir / "Nebulove-subset.woff2").exists())
            self.assertFalse(explicit_out.exists())
            self.assertIn("--check：未写入字体或页面。", stdout.getvalue())
            self.assertIn("50.0% 于原字体", stdout.getvalue())

    def test_default_mode_updates_html_without_writing_standalone_font(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_path = root / "page.html"
            html_path.write_text("<style>@font-face { font-family: 'Nebulove'; }</style>\n<p>你好</p>", encoding="utf-8")
            source_font = root / "source.woff2"
            source_font.write_bytes(b"12345678")
            output_dir = root / "scripts"
            output_dir.mkdir()

            stdout = io.StringIO()
            with patch.object(subset_font, "HERE", str(output_dir)), \
                    patch.object(subset_font, "build_subset", side_effect=_fake_build_subset), \
                    patch.object(sys, "argv", ["subset_font.py", "--html", str(html_path), "--ttf", str(source_font)]), \
                    redirect_stdout(stdout):
                subset_font.main()

            updated = html_path.read_text(encoding="utf-8")
            self.assertEqual(list(output_dir.iterdir()), [])
            self.assertIn("font-display: swap;", updated)
            self.assertNotIn("子集文件：", stdout.getvalue())

            stdout_second = io.StringIO()
            with patch.object(subset_font, "HERE", str(output_dir)), \
                    patch.object(subset_font, "build_subset", side_effect=_fake_build_subset), \
                    patch.object(sys, "argv", ["subset_font.py", "--html", str(html_path), "--ttf", str(source_font)]), \
                    redirect_stdout(stdout_second):
                subset_font.main()

            self.assertEqual(html_path.read_text(encoding="utf-8"), updated)
            self.assertIn("页面已经是目标内容，未改动。", stdout_second.getvalue())

    def test_output_option_writes_standalone_font_on_demand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_path = root / "page.html"
            html_path.write_text("<style>@font-face { font-family: 'Nebulove'; }</style>\n<p>你好</p>", encoding="utf-8")
            source_font = root / "source.woff2"
            source_font.write_bytes(b"12345678")
            output_dir = root / "scripts"
            output_dir.mkdir()
            exported_font = root / "dist" / "Nebulove-subset.woff2"

            stdout = io.StringIO()
            with patch.object(subset_font, "HERE", str(output_dir)), \
                    patch.object(subset_font, "build_subset", side_effect=_fake_build_subset), \
                    patch.object(
                        sys, "argv",
                        ["subset_font.py", "--html", str(html_path), "--ttf", str(source_font),
                         "--output", str(exported_font)],
                    ), \
                    redirect_stdout(stdout):
                subset_font.main()

            self.assertFalse((output_dir / "Nebulove-subset.woff2").exists())
            self.assertEqual(exported_font.read_bytes(), b"1234")
            self.assertIn(f"子集文件：{exported_font}", stdout.getvalue())

    def test_temporary_download_is_removed_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_path = root / "page.html"
            html_path.write_text("<style>@font-face { font-family: 'Nebulove'; }</style>", encoding="utf-8")
            downloaded_paths = []

            def fake_download(_url, dest):
                p = Path(dest)
                p.write_bytes(b"12345678")
                downloaded_paths.append(p)

            with patch.object(subset_font, "download", side_effect=fake_download), \
                    patch.object(subset_font, "build_subset", side_effect=RuntimeError("boom")), \
                    patch.object(sys, "argv", ["subset_font.py", "--html", str(html_path)]), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    subset_font.main()

            self.assertEqual(len(downloaded_paths), 1)
            self.assertFalse(downloaded_paths[0].exists())
            self.assertFalse(downloaded_paths[0].parent.exists())


if __name__ == "__main__":
    unittest.main()
