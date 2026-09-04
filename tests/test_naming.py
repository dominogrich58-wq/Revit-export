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


class BuildTemplateTest(unittest.TestCase):
    def test_segments_with_prefix_and_suffix(self):
        segments = [{"parameter": "Sheet Number"},
                    {"parameter": "Sheet Name", "prefix": " - "}]
        self.assertEqual(naming.build_template(segments, "DSP_", "_v1"),
                         "DSP_{Sheet Number} - {Sheet Name}_v1")

    def test_fallback_and_modifier_end_up_in_the_token(self):
        segments = [{"parameter": "Current Revision", "prefix": "R",
                     "fallback": "00", "modifier": "upper"}]
        self.assertEqual(naming.build_template(segments),
                         "R{Current Revision|00:upper}")

    def test_unknown_modifier_is_dropped(self):
        segments = [{"parameter": "Sheet Name", "modifier": "kurziva"}]
        self.assertEqual(naming.build_template(segments), "{Sheet Name}")

    def test_segment_without_parameter_is_plain_text(self):
        segments = [{"parameter": "Sheet Number"},
                    {"parameter": "", "prefix": "_final"}]
        self.assertEqual(naming.build_template(segments),
                         "{Sheet Number}_final")

    def test_braces_in_literals_are_stripped(self):
        segments = [{"parameter": "Sheet Name", "prefix": "{x}"}]
        self.assertEqual(naming.build_template(segments, "}", "{"),
                         "x{Sheet Name}")

    def test_empty_input_gives_empty_template(self):
        self.assertEqual(naming.build_template([]), "")


class SegmentsFromTemplateTest(unittest.TestCase):
    def round_trip(self, template):
        return naming.build_template(naming.segments_from_template(template))

    def test_round_trip_keeps_the_template(self):
        for template in ("{Sheet Number} - {Sheet Name}",
                         "DSP_{Sheet Number}_v1",
                         "R{Current Revision|00:upper}",
                         "bez tokenov",
                         ""):
            self.assertEqual(self.round_trip(template), template)

    def test_literal_before_token_becomes_its_prefix(self):
        segments = naming.segments_from_template("DSP_{Sheet Number}")
        self.assertEqual(segments[0]["prefix"], "DSP_")
        self.assertEqual(segments[0]["parameter"], "Sheet Number")

    def test_trailing_literal_becomes_suffix_of_last_segment(self):
        segments = naming.segments_from_template("{Sheet Number}_v1")
        self.assertEqual(segments[-1]["suffix"], "_v1")

    def test_template_without_tokens_is_one_text_segment(self):
        segments = naming.segments_from_template("vykres")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["parameter"], "")

    def test_fallback_and_modifier_survive(self):
        segment = naming.segments_from_template("{Current Revision|00:upper}")[0]
        self.assertEqual(segment["fallback"], "00")
        self.assertEqual(segment["modifier"], "upper")


class DescribeSegmentTest(unittest.TestCase):
    def test_plain_parameter(self):
        self.assertEqual(naming.describe_segment({"parameter": "Sheet Name"}),
                         "{Sheet Name}")

    def test_all_details(self):
        described = naming.describe_segment(
            {"parameter": "Current Revision", "prefix": "R", "suffix": "!",
             "fallback": "00", "modifier": "upper"})
        for expected in ("'R'", "{Current Revision}", "00", "upper", "'!'"):
            self.assertIn(expected, described)

    def test_text_only_segment(self):
        self.assertEqual(naming.describe_segment({"parameter": "",
                                                  "prefix": "_final"}),
                         "'_final' + (text)")


class RenderSegmentsTest(unittest.TestCase):
    """Cast s prazdnym parametrom vypadne aj s prefixom a suffixom."""

    def setUp(self):
        self.values = {"Sheet Number": "25AB123", "Sheet Name": "ARS_201",
                       "Faza": "", "Revizia": ""}
        self.segments = [
            {"parameter": "Sheet Number"},
            {"parameter": "Faza", "prefix": "_"},
            {"parameter": "Sheet Name", "prefix": "_"},
        ]

    def render(self, missing=None, **kwargs):
        return naming.render_segments(self.segments, self.values.get,
                                      missing=missing, **kwargs)

    def test_empty_parameter_drops_the_whole_part(self):
        self.assertEqual(self.render(), "25AB123_ARS_201")

    def test_filled_parameter_keeps_its_prefix(self):
        self.values["Faza"] = "PSP"
        self.assertEqual(self.render(), "25AB123_PSP_ARS_201")

    def test_fallback_keeps_the_part(self):
        self.segments[1]["fallback"] = "00"
        self.assertEqual(self.render(), "25AB123_00_ARS_201")

    def test_suffix_disappears_with_the_part(self):
        self.segments[1]["suffix"] = "!"
        self.assertEqual(self.render(), "25AB123_ARS_201")

    def test_dropped_part_is_reported_as_missing(self):
        missing = []
        self.render(missing)
        self.assertEqual(missing, ["Faza"])

    def test_part_with_a_fallback_is_not_reported(self):
        self.segments[1]["fallback"] = "00"
        missing = []
        self.render(missing)
        self.assertEqual(missing, [])

    def test_text_only_part_always_stays(self):
        self.segments.append({"parameter": "", "prefix": "_final"})
        self.assertEqual(self.render(), "25AB123_ARS_201_final")

    def test_global_prefix_and_suffix(self):
        self.assertEqual(self.render(prefix="DSP_", suffix="_v1"),
                         "DSP_25AB123_ARS_201_v1")

    def test_modifier_applies_to_the_value_only(self):
        self.segments[2]["modifier"] = "upper"
        self.assertEqual(self.render(), "25AB123_ARS_201")
        self.values["Sheet Name"] = "Rez a-a"
        self.assertEqual(self.render(), "25AB123_REZ A-A")

    def test_all_parts_empty_gives_a_placeholder_name(self):
        self.values = {}
        self.assertEqual(self.render(), "bez-nazvu")

    def test_result_is_sanitized(self):
        self.values["Sheet Name"] = "Rez A/A"
        self.assertEqual(self.render(), "25AB123_Rez A_A")
