# -*- coding: utf-8 -*-
import unittest

from sheetpilot import naming


class ParseTokenTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(naming.parse_token("Sheet Name"), ("Sheet Name", "", None))

    def test_fallback_and_modifier(self):
        self.assertEqual(naming.parse_token("Current Revision|00:upper"),
                         ("Current Revision", "00", "upper"))

    def test_colon_that_is_not_a_modifier_stays_in_the_name(self):
        self.assertEqual(naming.parse_token("Poznamka: interne"),
                         ("Poznamka: interne", "", None))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.values = {"Sheet Number": "A-101", "Sheet Name": u"Podorys 1.NP",
                       "Current Revision": ""}

    def render(self, template, missing=None):
        return naming.render(template, self.values.get, missing)

    def test_basic(self):
        self.assertEqual(self.render("{Sheet Number} - {Sheet Name}"),
                         u"A-101 - Podorys 1.NP")

    def test_modifiers(self):
        self.assertEqual(self.render("{Sheet Name:upper}"), u"PODORYS 1.NP")
        self.assertEqual(self.render("{Sheet Name:nospace}"), u"Podorys1.NP")
        self.assertEqual(self.render("{Sheet Name:slug}"), u"Podorys-1-NP")

    def test_diacritics_survive_without_slug(self):
        self.values["Sheet Name"] = u"Pôdorys strechy"
        self.assertEqual(self.render("{Sheet Name}"), u"Pôdorys strechy")

    def test_fallback_used_for_empty_value(self):
        self.assertEqual(self.render("R{Current Revision|00}"), "R00")

    def test_missing_tokens_reported(self):
        missing = []
        self.render("{Sheet Number}-{Neexistuje}", missing)
        self.assertEqual(missing, ["Neexistuje"])

    def test_fallback_does_not_report_missing(self):
        missing = []
        self.render("{Current Revision|00}", missing)
        self.assertEqual(missing, [])


class SanitizeTest(unittest.TestCase):
    def test_illegal_characters_replaced(self):
        self.assertEqual(naming.sanitize('A/B:C*D?E"F<G>H|I'),
                         "A_B_C_D_E_F_G_H_I")

    def test_trailing_dot_and_space_removed(self):
        self.assertEqual(naming.sanitize("Vykres . "), "Vykres")

    def test_reserved_windows_name_prefixed(self):
        self.assertEqual(naming.sanitize("CON"), "_CON")
        self.assertEqual(naming.sanitize("com1.dwg"), "_com1.dwg")

    def test_empty_result_gets_placeholder(self):
        self.assertEqual(naming.sanitize("///"), "___")
        self.assertEqual(naming.sanitize("  "), "bez-nazvu")

    def test_length_is_capped(self):
        self.assertEqual(len(naming.sanitize("x" * 500)), naming.MAX_LENGTH)


class DeduplicateTest(unittest.TestCase):
    def test_case_insensitive_like_windows(self):
        self.assertEqual(naming.deduplicate(["A", "a", "B"]), ["A", "a_2", "B"])

    def test_does_not_collide_with_existing_suffix(self):
        self.assertEqual(naming.deduplicate(["A", "A_2", "A"]),
                         ["A", "A_2", "A_3"])

    def test_unique_names_untouched(self):
        self.assertEqual(naming.deduplicate(["A", "B"]), ["A", "B"])


class ValidateTest(unittest.TestCase):
    def test_empty_template_rejected(self):
        self.assertRaises(naming.NamingError, naming.validate_template, "  ")

    def test_unbalanced_braces_rejected(self):
        self.assertRaises(naming.NamingError, naming.validate_template,
                          "{Sheet Number")

    def test_template_without_tokens_warns(self):
        self.assertEqual(len(naming.validate_template("vykres")), 1)

    def test_valid_template_has_no_warnings(self):
        self.assertEqual(naming.validate_template("{Sheet Number}"), [])

    def test_tokens_in(self):
        self.assertEqual(naming.tokens_in("{Sheet Number}-{Current Revision|00}"),
                         ["Sheet Number", "Current Revision"])


if __name__ == "__main__":
    unittest.main()
