# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from sheetpilot import runner
from sheetpilot.config import normalize

from fakes import FakeDocument, FakeSheet


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.doc = FakeDocument()
        self.config = normalize({"output_folder": tempfile.gettempdir()})

    def test_names_follow_the_template(self):
        sheets = [FakeSheet("A-101", u"Pôdorys 1.NP"), FakeSheet("A-102", u"Rez A-A")]
        pairs, missing = runner.plan(self.doc, sheets, self.config)
        self.assertEqual([name for _, name in pairs],
                         [u"A-101 - Pôdorys 1.NP", u"A-102 - Rez A-A"])
        self.assertEqual(missing, [])

    def test_duplicate_names_are_made_unique(self):
        sheets = [FakeSheet("A-101", u"Pôdorys"), FakeSheet("A-102", u"Pôdorys")]
        self.config["file_name_template"] = "{Sheet Name}"
        pairs, _ = runner.plan(self.doc, sheets, self.config)
        self.assertEqual([name for _, name in pairs], [u"Pôdorys", u"Pôdorys_2"])

    def test_missing_token_is_reported_once(self):
        sheets = [FakeSheet("A-101", u"Pôdorys"), FakeSheet("A-102", u"Rez")]
        self.config["file_name_template"] = "{Sheet Number}-{Faza}"
        _, missing = runner.plan(self.doc, sheets, self.config)
        self.assertEqual(missing, ["Faza"])

    def test_file_name_token_comes_from_model_name(self):
        self.config["file_name_template"] = "{File Name}_{Sheet Number}"
        pairs, _ = runner.plan(self.doc, [FakeSheet("A-101", "X")], self.config)
        self.assertEqual(pairs[0][1], "Bytovka_A-101")

    def test_plan_uses_segments_with_global_prefix_and_suffix(self):
        self.config = normalize({
            "output_folder": tempfile.gettempdir(),
            "file_name_prefix": "DSP_",
            "file_name_suffix": "_v1",
            "file_name_segments": [{"parameter": "Sheet Number"},
                                   {"parameter": "Sheet Name", "prefix": "-"}],
        })
        pairs, _ = runner.plan(self.doc, [FakeSheet("A-101", "Rez")], self.config)
        self.assertEqual(pairs[0][1], "DSP_A-101-Rez_v1")

    def test_illegal_characters_in_sheet_name_are_sanitized(self):
        pairs, _ = runner.plan(self.doc, [FakeSheet("A-101", "Rez A/A")], self.config)
        self.assertEqual(pairs[0][1], "A-101 - Rez A_A")


class TargetFolderTest(unittest.TestCase):
    def test_single_format_exports_into_the_root(self):
        config = normalize({"output_folder": r"/export", "formats": ["PDF"]})
        self.assertEqual(runner.target_folder(config, "PDF"),
                         os.path.abspath("/export"))

    def test_multiple_formats_get_subfolders(self):
        config = normalize({"output_folder": r"/export", "formats": ["PDF", "DWG"]})
        self.assertEqual(runner.target_folder(config, "DWG"),
                         os.path.join(os.path.abspath("/export"), "DWG"))

    def test_subfolders_can_be_turned_off(self):
        config = normalize({"output_folder": r"/export", "formats": ["PDF", "DWG"],
                            "subfolder_per_format": False})
        self.assertEqual(runner.target_folder(config, "DWG"),
                         os.path.abspath("/export"))


class PrepareTargetTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "a.pdf")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_no_existing_file_is_fine(self):
        self.assertIsNone(runner._prepare_target(self.path, True))

    def test_existing_file_is_removed_when_overwriting(self):
        open(self.path, "w").close()
        self.assertIsNone(runner._prepare_target(self.path, True))
        self.assertFalse(os.path.exists(self.path))

    def test_existing_file_blocks_export_without_overwrite(self):
        open(self.path, "w").close()
        self.assertIn("existuje", runner._prepare_target(self.path, False))
        self.assertTrue(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()


class SheetSizeTest(unittest.TestCase):
    """Rozmer vykresu z Sheet Width / Sheet Height."""

    def test_feet_are_converted_to_whole_millimetres(self):
        from sheetpilot.sheets import feet_to_mm
        self.assertEqual(feet_to_mm(1.0), 305)
        self.assertEqual(feet_to_mm(841 / 304.8), 841)
        self.assertEqual(feet_to_mm(0.0), 0)

    def test_sheet_without_the_parameters_gives_no_size(self):
        from sheetpilot.sheets import sheet_size_label, sheet_size_mm
        sheet = FakeSheet("A-101", "Rez")
        self.assertEqual(sheet_size_mm(sheet), (None, None))
        self.assertEqual(sheet_size_label(sheet), "")

    def test_size_tokens_are_empty_when_the_sheet_has_no_size(self):
        config = normalize({"output_folder": tempfile.gettempdir(),
                            "file_name_template": "{Sheet Number}{Sheet Width}"})
        pairs, _ = runner.plan(FakeDocument(), [FakeSheet("A-101", "Rez")], config)
        self.assertEqual(pairs[0][1], "A-101")
