# -*- coding: utf-8 -*-
import unittest

from sheetpilot import revit_compat
from sheetpilot.exporters import dwg

from fakes import FakeDb, FakeDocument


class DwgOptionsTest(unittest.TestCase):
    """Zostavenie DWGExportOptions musi fungovat na oboch cestach k setupu."""

    def setUp(self):
        self.doc = FakeDocument()
        self._original = revit_compat._DB

    def tearDown(self):
        revit_compat._DB = self._original

    def use(self, **kwargs):
        revit_compat._DB = FakeDb(**kwargs)

    def test_static_getter_is_preferred(self):
        self.use(settings_names=["Odovzdanie"])
        options = dwg.build_options(self.doc, {"export_setup": "Odovzdanie"})
        self.assertEqual(options.source, "static:Odovzdanie")

    def test_falls_back_to_element_when_static_getter_is_missing(self):
        # Revit 2026: DWGExportOptions.GetPredefinedOptions neexistuje.
        self.use(settings_names=["Odovzdanie"], with_static_getter=False)
        options = dwg.build_options(self.doc, {"export_setup": "Odovzdanie"})
        self.assertEqual(options.source, "element:Odovzdanie")

    def test_unknown_setup_raises_and_lists_available(self):
        self.use(settings_names=["Odovzdanie"], with_static_getter=False)
        try:
            dwg.build_options(self.doc, {"export_setup": "Neexistuje"})
        except KeyError as exc:
            self.assertIn("Odovzdanie", str(exc))
        else:
            self.fail("ocakaval som KeyError")

    def test_no_setup_gives_plain_options(self):
        self.use(settings_names=["Odovzdanie"])
        options = dwg.build_options(self.doc, {"export_setup": ""})
        self.assertEqual(options.source, "default")

    def test_acad_version_is_applied(self):
        self.use()
        options = dwg.build_options(self.doc, {"file_version": "AutoCAD2018"})
        self.assertEqual(options.FileVersion, "R2018")

    def test_unknown_acad_version_is_ignored(self):
        self.use()
        options = dwg.build_options(self.doc, {"file_version": "AutoCAD1997"})
        self.assertIsNone(options.FileVersion)

    def test_merge_views_and_shared_coords(self):
        self.use()
        options = dwg.build_options(self.doc, {"merge_views": True,
                                               "shared_coords": True})
        self.assertTrue(options.MergedViews)
        self.assertTrue(options.SharedCoords)

    def test_export_setups_lists_names(self):
        self.use(settings_names=["B", "A"])
        self.assertEqual(dwg.export_setups(self.doc), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
