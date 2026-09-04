# -*- coding: utf-8 -*-
"""Zber vysledkov exportu a ich vypis / ulozenie do CSV logu."""

import io
import os
import time

OK = "OK"
SKIPPED = "PRESKOCENE"
FAILED = "CHYBA"
WARNING = "UPOZORNENIE"


class Result(object):
    __slots__ = ("sheet_number", "sheet_name", "fmt", "status", "path", "message")

    def __init__(self, sheet_number, sheet_name, fmt, status, path="", message=""):
        self.sheet_number = sheet_number
        self.sheet_name = sheet_name
        self.fmt = fmt
        self.status = status
        self.path = path
        self.message = message

    def as_row(self):
        return [self.sheet_number, self.sheet_name, self.fmt,
                self.status, self.path, self.message]

    def __repr__(self):
        return "<%s %s %s %s>" % (self.status, self.fmt,
                                  self.sheet_number, self.path or self.message)


class Report(object):
    """Priebeh a vysledok davky."""

    HEADER = ["Cislo vykresu", "Nazov vykresu", "Format", "Stav", "Subor", "Poznamka"]

    def __init__(self):
        self.results = []
        self.warnings = []
        self.started = time.time()

    def warn(self, message):
        """Poznamka k davke, ktora nie je vysledkom ziadneho suboru.

        Napr. ze parameter zo sablony nazvu nema hodnotu. Do poctov
        OK / preskocene / chyby sa nerata - inak by suhrn tvrdil, ze sa
        nieco nevyexportovalo, hoci sa vyexportovalo vsetko.
        """
        if message not in self.warnings:
            self.warnings.append(message)
        return message

    def add(self, result):
        self.results.append(result)
        return result

    def ok(self, sheet_number, sheet_name, fmt, path):
        return self.add(Result(sheet_number, sheet_name, fmt, OK, path))

    def skipped(self, sheet_number, sheet_name, fmt, message, path=""):
        return self.add(Result(sheet_number, sheet_name, fmt, SKIPPED, path, message))

    def failed(self, sheet_number, sheet_name, fmt, message):
        return self.add(Result(sheet_number, sheet_name, fmt, FAILED, "", message))

    def count(self, status):
        return sum(1 for r in self.results if r.status == status)

    @property
    def elapsed(self):
        return time.time() - self.started

    @property
    def exported_files(self):
        return [r.path for r in self.results if r.status == OK and r.path]

    def has_failures(self):
        return self.count(FAILED) > 0

    def summary(self):
        return (u"Export dokonceny za %.1f s - %d OK, %d preskocenych, %d chyb."
                % (self.elapsed, self.count(OK), self.count(SKIPPED), self.count(FAILED)))

    def lines(self):
        """Citatelny vypis pre Dynamo watch node alebo konzolu."""
        rows = [u"%s | %s" % (WARNING.ljust(11), message)
                for message in self.warnings]
        rows += [u"%s | %s | %s | %s" % (r.status.ljust(11), r.fmt.ljust(4),
                                         r.sheet_number, r.path or r.message)
                 for r in self.results]
        return rows + [u"", self.summary()]

    def write_csv(self, folder, file_name=None):
        """Ulozi log davky ako CSV (oddelovac ';', UTF-8 s BOM kvoli Excelu)."""
        if not os.path.isdir(folder):
            os.makedirs(folder)
        name = file_name or time.strftime("SheetPilot-log-%Y%m%d-%H%M%S.csv")
        path = os.path.join(folder, name)
        with io.open(path, "w", encoding="utf-8-sig", newline="") as handle:
            handle.write(u";".join(self.HEADER) + u"\r\n")
            rows = [["-", "-", "-", WARNING, "", message]
                    for message in self.warnings]
            rows += [result.as_row() for result in self.results]
            for row in rows:
                cells = [u'"%s"' % (u"%s" % cell).replace(u'"', u'""')
                         for cell in row]
                handle.write(u";".join(cells) + u"\r\n")
        return path
