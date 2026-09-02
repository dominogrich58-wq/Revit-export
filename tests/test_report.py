# -*- coding: utf-8 -*-
import io
import os
import shutil
import tempfile
import unittest

from sheetpilot import report as report_mod


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.report = report_mod.Report()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_counts_and_summary(self):
        self.report.ok("A-101", u"Pôdorys", "PDF", "/x/a.pdf")
        self.report.skipped("A-102", u"Rez", "PDF", u"uz existuje")
        self.report.failed("A-103", u"Pohľad", "DWG", u"setup chýba")
        self.assertEqual(self.report.count(report_mod.OK), 1)
        self.assertEqual(self.report.count(report_mod.SKIPPED), 1)
        self.assertTrue(self.report.has_failures())
        self.assertIn("1 OK", self.report.summary())

    def test_exported_files_lists_only_successes(self):
        self.report.ok("A-101", u"Pôdorys", "PDF", "/x/a.pdf")
        self.report.failed("A-102", u"Rez", "PDF", "chyba")
        self.assertEqual(self.report.exported_files, ["/x/a.pdf"])

    def test_csv_log_is_written_with_bom_and_quotes(self):
        self.report.failed("A-101", u'Rez "hlavný"', "DWG", u"chyba; bodkociarka")
        path = self.report.write_csv(os.path.join(self.folder, "log"))
        self.assertTrue(os.path.isfile(path))
        with io.open(path, "r", encoding="utf-8-sig") as handle:
            content = handle.read()
        self.assertIn(u'"Rez ""hlavný"""', content)
        self.assertIn(u"Cislo vykresu;", content)
        self.assertEqual(len(content.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
