# -*- coding: utf-8 -*-
"""SheetPilot - davkovy export vykresov do PDF a DWG."""

__title__ = "Export\nvykresov"
__doc__ = ("Vyberie vykresy, formaty a schemu nazvov, potom davkovo "
           "exportuje do PDF a DWG.")

import os

from pyrevit import forms, revit, script

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot import config as sp_config      # noqa: E402
from sheetpilot import naming, runner           # noqa: E402
from sheetpilot.exporters import dwg as dwg_exporter   # noqa: E402

logger = script.get_logger()
output = script.get_output()
doc = revit.doc

TEMPLATE_PRESETS = [
    "{Sheet Number} - {Sheet Name}",
    "{Sheet Number}_{Sheet Name}",
    "{Project Number}-{Sheet Number}-{Sheet Name}",
    "{Sheet Number} - {Sheet Name} - R{Current Revision|00}",
    "{yyyymmdd}_{Sheet Number}_{Sheet Name:slug}",
    "Vlastna sablona...",
]


def load_profile():
    path = sheetpilot_setup.profile_path()
    if os.path.isfile(path):
        try:
            import io, json
            with io.open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.debug("Profil sa neda nacitat: %s", exc)
    return sp_config.defaults()


def ask_template(previous):
    presets = list(TEMPLATE_PRESETS)
    if previous and previous not in presets:
        presets.insert(0, previous)
    choice = forms.SelectFromList.show(
        presets, title="Schema nazvu suboru", button_name="Pouzit",
        multiselect=False)
    if not choice:
        return None
    if choice != "Vlastna sablona...":
        return choice

    while True:
        custom = forms.ask_for_string(
            default=previous or TEMPLATE_PRESETS[0],
            prompt=("Tokeny: {Sheet Number}, {Sheet Name}, {Current Revision}, "
                    "{Project Number}, {Date}, {File Name} alebo lubovolny "
                    "parameter vykresu.\n"
                    "Nahradna hodnota: {Current Revision|00}\n"
                    "Modifikatory: :upper :lower :title :slug :nospace"),
            title="Vlastna schema nazvu")
        if not custom:
            return None
        try:
            naming.validate_template(custom)
            return custom
        except naming.NamingError as exc:
            forms.alert(u"%s" % exc, title="Chybna sablona")


def main():
    sheets = forms.select_sheets(title="Vyber vykresy na export",
                                 button_name="Pokracovat")
    if not sheets:
        return
    sheets = [s for s in sheets if not s.IsPlaceholder]
    if not sheets:
        forms.alert("Vybrane boli len placeholder vykresy, tie sa exportovat "
                    "nedaju.", title="SheetPilot")
        return

    profile = load_profile()

    formats = forms.SelectFromList.show(
        ["PDF", "DWG"], title="Formaty exportu", button_name="Pokracovat",
        multiselect=True)
    if not formats:
        return

    template = ask_template(profile.get("file_name_template"))
    if not template:
        return

    combine = False
    if "PDF" in formats and len(sheets) > 1:
        combine = forms.alert("Spojit vsetky vykresy do jedneho PDF suboru?",
                              title="PDF", yes=True, no=True)

    dwg_setup = profile.get("dwg", {}).get("export_setup", "")
    if "DWG" in formats:
        setups = dwg_exporter.export_setups(doc)
        if setups:
            choice = forms.SelectFromList.show(
                ["<predvolby Revitu>"] + setups, title="DWG Export Setup",
                button_name="Pouzit", multiselect=False)
            if not choice:
                return
            dwg_setup = "" if choice.startswith("<") else choice
        else:
            dwg_setup = ""

    folder = forms.pick_folder(title="Vystupny adresar")
    if not folder:
        return

    profile.update({
        "output_folder": folder,
        "formats": list(formats),
        "file_name_template": template,
        "sheet_selection": {"mode": "numbers",
                            "numbers": [s.SheetNumber for s in sheets]},
    })
    profile.setdefault("pdf", {})["combine"] = bool(combine)
    profile.setdefault("dwg", {})["export_setup"] = dwg_setup

    try:
        normalized = sp_config.normalize(profile)
    except sp_config.ConfigError as exc:
        forms.alert(u"%s" % exc, title="Chybne nastavenia")
        return

    sp_config.save(sheetpilot_setup.profile_path(), normalized)

    with forms.ProgressBar(title="Export {value}/{max_value} - {title}",
                           cancellable=True) as progress_bar:
        def progress(done, total, text):
            if progress_bar.cancelled:
                return False
            progress_bar.title = text
            progress_bar.update_progress(done, total)
            return True

        report = runner.run(doc, normalized, progress)

    log_path = report.write_csv(normalized["output_folder"])

    output.print_md("### SheetPilot - vysledok exportu")
    for line in report.lines():
        output.print_md("    " + line)
    output.print_md("Log davky: `%s`" % log_path)

    if report.has_failures():
        forms.alert(report.summary() + "\n\nDetaily najdes v okne vystupu "
                    "a v CSV logu.", title="SheetPilot")
    elif forms.alert(report.summary() + "\n\nOtvorit vystupny adresar?",
                     title="SheetPilot", yes=True, no=True):
        os.startfile(normalized["output_folder"])


main()
