# -*- coding: utf-8 -*-
"""Orchestracia davkoveho exportu - spaja vyber vykresov, nazvy a exportery."""

import os

from . import naming, sheets as sheets_mod
from .config import effective_template, normalize
from .exporters import dwg as dwg_exporter
from .exporters import pdf as pdf_exporter
from .report import Report
from .revit_compat import supports_native_pdf


class Cancelled(Exception):
    """Pouzivatel prerusil davku."""


def resolve_sheets(doc, config):
    """Vyberie vykresy podla nastaveni `sheet_selection`."""
    selection = config["sheet_selection"]
    mode = selection["mode"]

    if mode == "set":
        return sheets_mod.sheets_from_set(doc, selection["set_name"])

    found = sheets_mod.all_sheets(doc)
    if mode == "numbers":
        return sheets_mod.filter_sheets(found, numbers=selection["numbers"])
    if mode == "filter":
        return sheets_mod.filter_sheets(
            found,
            number_prefix=selection.get("number_prefix") or None,
            name_contains=selection.get("name_contains") or None,
            parameter_equals=selection.get("parameter_equals") or None)
    return found


def plan(doc, sheet_list, config):
    """Priradi kazdemu vykresu vysledny nazov suboru (bez pripony).

    Vracia (dvojice [(sheet, nazov)], zoznam chybajucich tokenov).
    """
    template = effective_template(config)
    missing, names = [], []
    for sheet in sheet_list:
        per_sheet = []
        names.append(naming.render(template,
                                   sheets_mod.make_resolver(doc, sheet),
                                   per_sheet))
        for token in per_sheet:
            if token not in missing:
                missing.append(token)
    return list(zip(sheet_list, naming.deduplicate(names))), missing


def target_folder(config, fmt):
    root = config["output_folder"]
    if config.get("subfolder_per_format") and len(config["formats"]) > 1:
        return os.path.join(root, fmt)
    return root


def _prepare_target(path, overwrite):
    """Vrati None ak sa ma exportovat, alebo dovod preskocenia."""
    if not os.path.isfile(path):
        return None
    if not overwrite:
        return "Subor uz existuje a prepis je vypnuty."
    try:
        os.remove(path)
        return None
    except OSError as exc:
        return ("Existujuci subor sa neda prepisat (je otvoreny v inej "
                "aplikacii?): %s" % exc)


def run(doc, user_config, progress=None):
    """Spusti davkovy export. Vracia `Report`.

    `progress(hotove, spolu, popis)` sa vola pred kazdym krokom; ak vrati
    False, davka sa preruzi a doteraz vytvorene subory zostanu zachovane.
    """
    config = normalize(user_config)
    report = Report()

    selected = resolve_sheets(doc, config)
    if not selected:
        report.skipped("-", "-", "-", "Vyberu nezodpoveda ziadny vykres.")
        return report

    pairs, missing_tokens = plan(doc, selected, config)
    for token in missing_tokens:
        report.skipped("-", "-", "-",
                       u"Parameter '%s' zo sablony nazvu nema hodnotu - "
                       u"v nazvoch sa nahradil prazdnym retazcom." % token)

    formats = config["formats"]
    combine_pdf = config["pdf"]["combine"] and "PDF" in formats
    total = (len(pairs) * len([f for f in formats if f != "PDF" or not combine_pdf])
             + (1 if combine_pdf else 0))
    done = [0]

    def step(text):
        done[0] += 1
        if progress and progress(done[0], total, text) is False:
            raise Cancelled()

    try:
        for fmt in formats:
            folder = target_folder(config, fmt)
            if fmt == "PDF":
                if combine_pdf:
                    _export_combined_pdf(doc, pairs, folder, config, report, step)
                else:
                    _export_pdfs(doc, pairs, folder, config, report, step)
            elif fmt == "DWG":
                _export_dwgs(doc, pairs, folder, config, report, step)
    except Cancelled:
        report.skipped("-", "-", "-", "Davka prerusena pouzivatelom.")

    return report


def _export_pdfs(doc, pairs, folder, config, report, step):
    if not supports_native_pdf(doc):
        for sheet, _ in pairs:
            step(u"PDF %s" % sheet.SheetNumber)
            report.failed(sheet.SheetNumber, sheet.Name, "PDF",
                          "Revit %s nema nativny PDF export - pouzi Revit 2022+ "
                          "alebo tlac cez virtualnu PDF tlaciaren."
                          % doc.Application.VersionNumber)
        return

    overwrite = config["overwrite"]
    for sheet, name in pairs:
        step(u"PDF %s - %s" % (sheet.SheetNumber, sheet.Name))
        path = os.path.join(folder, name + ".pdf")
        reason = _prepare_target(path, overwrite)
        if reason:
            report.skipped(sheet.SheetNumber, sheet.Name, "PDF", reason, path)
            continue
        try:
            created = pdf_exporter.export(doc, [sheet], folder, name, config["pdf"])
            report.ok(sheet.SheetNumber, sheet.Name, "PDF", created)
        except Exception as exc:
            report.failed(sheet.SheetNumber, sheet.Name, "PDF", u"%s" % exc)


def _export_combined_pdf(doc, pairs, folder, config, report, step):
    first_sheet = pairs[0][0]
    name = naming.render(config["pdf"]["combined_file_name"],
                         sheets_mod.make_resolver(doc, first_sheet))
    step(u"PDF (spojene, %d vykresov)" % len(pairs))

    if not supports_native_pdf(doc):
        report.failed("-", "-", "PDF",
                      "Spojene PDF vyzaduje Revit 2022 alebo novsi.")
        return

    path = os.path.join(folder, name + ".pdf")
    reason = _prepare_target(path, config["overwrite"])
    if reason:
        report.skipped("-", "-", "PDF", reason, path)
        return
    try:
        created = pdf_exporter.export(doc, [s for s, _ in pairs], folder, name,
                                      config["pdf"])
        report.ok("%s..%s" % (pairs[0][0].SheetNumber, pairs[-1][0].SheetNumber),
                  "%d vykresov" % len(pairs), "PDF", created)
    except Exception as exc:
        report.failed("-", "-", "PDF", u"%s" % exc)


def _export_dwgs(doc, pairs, folder, config, report, step):
    try:
        options = dwg_exporter.build_options(doc, config["dwg"])
    except Exception as exc:
        for sheet, _ in pairs:
            step(u"DWG %s" % sheet.SheetNumber)
            report.failed(sheet.SheetNumber, sheet.Name, "DWG", u"%s" % exc)
        return

    overwrite = config["overwrite"]
    for sheet, name in pairs:
        step(u"DWG %s - %s" % (sheet.SheetNumber, sheet.Name))
        path = os.path.join(folder, name + ".dwg")
        reason = _prepare_target(path, overwrite)
        if reason:
            report.skipped(sheet.SheetNumber, sheet.Name, "DWG", reason, path)
            continue
        try:
            created = dwg_exporter.export(doc, sheet, folder, name, options)
            report.ok(sheet.SheetNumber, sheet.Name, "DWG", created)
        except Exception as exc:
            report.failed(sheet.SheetNumber, sheet.Name, "DWG", u"%s" % exc)
