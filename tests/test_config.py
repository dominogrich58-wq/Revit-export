# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from prosheets import config


class NormalizeTest(unittest.TestCase):
    def base(self, **overrides):
        data = {"output_folder": tempfile.gettempdir()}
        data.update(overrides)
        return data

    def test_defaults_are_filled_in(self):
        result = config.normalize(self.base())
        self.assertEqual(result["formats"], ["PDF"])
        self.assertEqual(result["pdf"]["raster_quality"], "High")
        self.assertFalse(result["pdf"]["combine"])

    def test_partial_nested_override_keeps_siblings(self):
        result = config.normalize(self.base(pdf={"combine": True}))
        self.assertTrue(result["pdf"]["combine"])
        self.assertEqual(result["pdf"]["raster_quality"], "High")

    def test_formats_accept_string_and_are_deduplicated(self):
        result = config.normalize(self.base(formats="pdf, dwg ,PDF"))
        self.assertEqual(result["formats"], ["PDF", "DWG"])

    def test_unknown_format_rejected(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(formats=["IFC"]))

    def test_empty_formats_rejected(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(formats=[]))

    def test_missing_output_folder_rejected(self):
        self.assertRaises(config.ConfigError, config.normalize, {})

    def test_set_mode_requires_set_name(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(sheet_selection={"mode": "set"}))

    def test_numbers_mode_requires_numbers(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(sheet_selection={"mode": "numbers"}))

    def test_unknown_selection_mode_rejected(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(sheet_selection={"mode": "vsetko"}))

    def test_invalid_template_rejected(self):
        self.assertRaises(Exception, config.normalize,
                          self.base(file_name_template="{Sheet Number"))

    def test_zoom_is_clamped(self):
        self.assertEqual(config.normalize(self.base(pdf={"zoom": 5000}))["pdf"]["zoom"],
                         1000)

    def test_non_numeric_zoom_rejected(self):
        self.assertRaises(config.ConfigError, config.normalize,
                          self.base(pdf={"zoom": "vela"}))

    def test_defaults_are_not_shared_between_calls(self):
        first = config.normalize(self.base())
        first["pdf"]["combine"] = True
        self.assertFalse(config.normalize(self.base())["pdf"]["combine"])


class RoundTripTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_save_and_load(self):
        original = config.normalize({
            "output_folder": self.folder,
            "formats": ["PDF", "DWG"],
            "file_name_template": u"{Sheet Number} - {Sheet Name} - Pôdorys",
        })
        path = config.save(os.path.join(self.folder, "sub", "profil.json"), original)
        self.assertEqual(config.load(path), original)


if __name__ == "__main__":
    unittest.main()
