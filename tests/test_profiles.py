# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import tempfile
import unittest

from sheetpilot import config, profiles


class ProfileStoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.store = profiles.ProfileStore(self.folder)
        self.config = config.normalize({"output_folder": self.folder,
                                        "formats": ["PDF", "DWG"]})

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # --- ukladanie a citanie ----------------------------------------------

    def test_empty_store_has_no_profiles(self):
        self.assertEqual(self.store.names(), [])
        self.assertIsNone(self.store.active_name())

    def test_save_and_load_round_trip(self):
        self.store.save(u"DSP odovzdanie", self.config)
        self.assertEqual(self.store.names(), [u"DSP odovzdanie"])
        self.assertEqual(self.store.load(u"DSP odovzdanie"), self.config)

    def test_names_are_sorted(self):
        for name in ("Zaver", "Anketa", "Model"):
            self.store.save(name, self.config)
        self.assertEqual(self.store.names(), ["Anketa", "Model", "Zaver"])

    def test_loading_missing_profile_lists_available(self):
        self.store.save("Existuje", self.config)
        try:
            self.store.load("Neexistuje")
        except profiles.ProfileError as exc:
            self.assertIn("Existuje", str(exc))
        else:
            self.fail("ocakaval som ProfileError")

    def test_illegal_characters_in_name_are_cleaned(self):
        effective = self.store.save("DSP/odovzdanie:2026", self.config)
        self.assertEqual(effective, "DSP_odovzdanie_2026")
        self.assertTrue(self.store.exists(effective))

    def test_empty_name_is_rejected(self):
        self.assertRaises(profiles.ProfileError, self.store.save, "  ",
                          self.config)

    def test_saving_twice_overwrites_rather_than_duplicates(self):
        self.store.save("Profil", self.config)
        changed = dict(self.config, formats=["PDF"])
        self.store.save("Profil", changed)
        self.assertEqual(self.store.names(), ["Profil"])
        self.assertEqual(self.store.load("Profil")["formats"], ["PDF"])

    # --- mazanie, premenovanie, kopirovanie -------------------------------

    def test_delete(self):
        self.store.save("Profil", self.config)
        self.store.delete("Profil")
        self.assertEqual(self.store.names(), [])

    def test_deleting_missing_profile_raises(self):
        self.assertRaises(profiles.ProfileError, self.store.delete, "Neexistuje")

    def test_rename_keeps_the_content(self):
        self.store.save("Stary", self.config)
        self.store.rename("Stary", "Novy")
        self.assertEqual(self.store.names(), ["Novy"])
        self.assertEqual(self.store.load("Novy"), self.config)

    def test_duplicate_leaves_the_original(self):
        self.store.save("Original", self.config)
        self.store.duplicate("Original", "Kopia")
        self.assertEqual(self.store.names(), ["Kopia", "Original"])

    # --- aktivny profil ----------------------------------------------------

    def test_active_profile_is_remembered(self):
        self.store.save("Profil", self.config)
        self.store.set_active("Profil")
        self.assertEqual(self.store.active_name(), "Profil")
        self.assertEqual(self.store.active(), self.config)

    def test_active_falls_back_to_defaults(self):
        self.assertEqual(self.store.active(), config.defaults())

    def test_deleting_the_active_profile_clears_the_pointer(self):
        self.store.save("Profil", self.config)
        self.store.set_active("Profil")
        self.store.delete("Profil")
        self.assertIsNone(self.store.active_name())

    def test_renaming_the_active_profile_moves_the_pointer(self):
        self.store.save("Stary", self.config)
        self.store.set_active("Stary")
        self.store.rename("Stary", "Novy")
        self.assertEqual(self.store.active_name(), "Novy")

    def test_pointer_to_a_vanished_profile_is_ignored(self):
        self.store.save("Profil", self.config)
        self.store.set_active("Profil")
        os.remove(self.store.path_for("Profil"))
        self.assertIsNone(self.store.active_name())

    def test_damaged_state_file_does_not_crash(self):
        self.store.save("Profil", self.config)
        with io.open(os.path.join(self.folder, profiles.STATE_FILE), "w",
                     encoding="utf-8") as handle:
            handle.write(u"toto nie je JSON")
        self.assertIsNone(self.store.active_name())

    # --- prechod zo stareho jedneho profilu --------------------------------

    def test_legacy_profile_is_migrated_and_activated(self):
        legacy = os.path.join(self.folder, "profile.json")
        with io.open(legacy, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(self.config, ensure_ascii=False))

        name = self.store.migrate_legacy(legacy)
        self.assertEqual(name, profiles.DEFAULT_NAME)
        self.assertEqual(self.store.active_name(), profiles.DEFAULT_NAME)
        self.assertEqual(self.store.load(name), self.config)
        self.assertTrue(os.path.isfile(legacy), "stary subor sa nema mazat")

    def test_migration_does_nothing_when_profiles_already_exist(self):
        self.store.save("Profil", self.config)
        legacy = os.path.join(self.folder, "profile.json")
        with io.open(legacy, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(self.config, ensure_ascii=False))
        self.assertIsNone(self.store.migrate_legacy(legacy))

    def test_migration_without_legacy_file_is_a_no_op(self):
        self.assertIsNone(self.store.migrate_legacy(
            os.path.join(self.folder, "chyba.json")))


if __name__ == "__main__":
    unittest.main()
