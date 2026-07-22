from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_tabs.py"
SPEC = importlib.util.spec_from_file_location("generate_tabs", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_tabs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_tabs)


class HarmonicAnalysisTests(unittest.TestCase):
    def test_extracts_declared_minor_key_and_removes_metadata_line(self) -> None:
        metadata, content = generate_tabs.extract_inline_metadata(
            ["Tom: Gm", "", "Gm  Cm  D7", "Uma letra"]
        )

        self.assertEqual(metadata["harmonic_key"], "G")
        self.assertEqual(metadata["harmonic_mode"], "minor")
        self.assertEqual(metadata["harmonic_key_source"], "declared")
        self.assertNotIn("Tom: Gm", content)

    def test_infers_major_key_from_tonic_subdominant_and_dominant(self) -> None:
        self.assertEqual(
            generate_tabs.infer_harmonic_key(["C", "Dm7", "G7", "C"]),
            ("C", "major"),
        )

    def test_infers_minor_key_with_major_dominant(self) -> None:
        self.assertEqual(
            generate_tabs.infer_harmonic_key(["Am", "Dm", "E7", "Am"]),
            ("A", "minor"),
        )

    def test_generated_page_contains_harmonic_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            source = input_dir / "grupo" / "musica.txt"
            source.parent.mkdir(parents=True)
            source.write_text(
                "Canção\nArtista\n\nTom: F\nF  Gm  C7\nUma letra\n",
                encoding="utf-8",
            )

            result = generate_tabs.convert_tab(source, input_dir, output_dir, "musicas")
            page = (output_dir / result["output_file"]).read_text(encoding="utf-8")

            self.assertIn("harmonic_key: F", page)
            self.assertIn("harmonic_mode: major", page)
            self.assertIn("harmonic_key_source: declared", page)
            self.assertNotIn("Tom: F", page)


if __name__ == "__main__":
    unittest.main()
