# -*- coding: utf-8 -*-
"""SheetPilot - davkovy export vykresov do PDF a DWG."""

__title__ = "Export\nvykresov"
__doc__ = ("Vyberie vykresy, formaty a schemu nazvov, potom davkovo "
           "exportuje do PDF a DWG.")

import os

from pyrevit import forms, revit, script

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot import config as sp_config            # noqa: E402
from sheetpilot import naming, runner                 # noqa: E402
from sheetpilot import sheets as sheets_mod           # noqa: E402
from sheetpilot.exporters import dwg as dwg_exporter  # noqa: E402

logger = script.get_logger()
output = script.get_output()
doc = revit.doc

PRESETS = [
    "{Sheet Number} - {Sheet Name}",
    "{Sheet Number}_{Sheet Name}",
    "{Project Number}-{Sheet Number}-{Sheet Name}",
    "{Sheet Number} - {Sheet Name} - R{Current Revision|00}",
    "{yyyymmdd}_{Sheet Number}_{Sheet Name:slug}",
]

SHEET_LABEL = "Vykres: "
PROJECT_LABEL = "Projekt: "
NO_MODIFIER = "bez upravy"


def load_profile():
    path = sheetpilot_setup.profile_path()
    if os.path.isfile(path):
        try:
            import io
            import json
            with io.open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.debug("Profil sa neda nacitat: %s", exc)
    return sp_config.defaults()


def text_or_empty(value):
    """pyRevit vracia None pri zruseni dialogu - to berieme ako prazdny text."""
    return value if value else ""


# --- Klikacie skladanie nazvu suboru ---------------------------------------

def pick_parameter(sheet):
    """Vyber parametra zo skutocnych parametrov modelu."""
    builtin, sheet_params, project_params = sheets_mod.available_parameters(
        doc, sheet)
    items = list(builtin)
    items += [SHEET_LABEL + name for name in sheet_params]
    items += [PROJECT_LABEL + name for name in project_params]

    choice = forms.SelectFromList.show(
        items, title="Ktory parameter pridat do nazvu?",
        button_name="Pridat", multiselect=False)
    if not choice:
        return None
    for label in (SHEET_LABEL, PROJECT_LABEL):
        if choice.startswith(label):
            return choice[len(label):]
    return choice


def add_segment(sheet, segments):
    parameter = pick_parameter(sheet)
    if parameter is None:
        return
    prefix = text_or_empty(forms.ask_for_string(
        default=" - " if segments else "",
        prompt="Text PRED parametrom (prefix). Napr. ' - ', '_' alebo nic.",
        title="Prefix pre {%s}" % parameter))
    suffix = text_or_empty(forms.ask_for_string(
        default="",
        prompt="Text ZA parametrom (suffix). Nechaj prazdne, ak nic netreba.",
        title="Suffix pre {%s}" % parameter))
    segments.append({"parameter": parameter, "prefix": prefix,
                     "suffix": suffix, "fallback": "", "modifier": ""})


def edit_last_segment(segments):
    """Doplni poslednej casti nahradnu hodnotu a upravu velkosti pismen."""
    if not segments:
        forms.alert("Zatial nie je pridana ziadna cast.", title="SheetPilot")
        return
    segment = segments[-1]
    segment["fallback"] = text_or_empty(forms.ask_for_string(
        default=segment.get("fallback") or "",
        prompt=("Co pouzit, ked je parameter prazdny? Napr. '00' pri revizii. "
                "Nechaj prazdne, ak sa ma vynechat."),
        title="Nahradna hodnota pre {%s}" % segment.get("parameter")))

    choice = forms.SelectFromList.show(
        [NO_MODIFIER] + sorted(naming.MODIFIERS),
        title="Uprava hodnoty {%s}" % segment.get("parameter"),
        button_name="Pouzit", multiselect=False)
    if choice:
        segment["modifier"] = "" if choice == NO_MODIFIER else choice


def compose_name(sheet, segments, prefix, suffix):
    template = naming.build_template(segments, prefix, suffix)
    if not template:
        return template, "(prazdny nazov)"
    return template, naming.render(template, sheets_mod.make_resolver(doc, sheet))


ADD = "Pridat parameter"
EDIT = "Upravit poslednu cast (nahradna hodnota, VELKE pismena)"
REMOVE = "Odobrat poslednu cast"
GLOBAL = "Prefix / suffix celeho nazvu"
PRESET = "Zacat od hotovej schemy"
MANUAL = "Napisat sablonu rucne"
CLEAR = "Vymazat vsetko"
DONE = "Hotovo"


def build_name_schema(sheet, profile):
    """Interaktivne poskladanie nazvu suboru. Vracia patch do profilu."""
    segments = list(profile.get("file_name_segments") or [])
    if not segments:
        segments = naming.segments_from_template(
            profile.get("file_name_template") or PRESETS[0])
    prefix = profile.get("file_name_prefix") or ""
    suffix = profile.get("file_name_suffix") or ""

    while True:
        template, preview = compose_name(sheet, segments, prefix, suffix)
        parts = "\n".join("  %d. %s" % (index, naming.describe_segment(segment))
                          for index, segment in enumerate(segments, start=1))
        message = (u"Ukazka na vykrese %s:   %s\n\nCasti nazvu:\n%s"
                   % (sheet.SheetNumber, preview, parts or "  (ziadne)"))

        choice = forms.CommandSwitchWindow.show(
            [DONE, ADD, EDIT, REMOVE, GLOBAL, PRESET, MANUAL, CLEAR],
            message=message)

        if choice is None:
            return None
        if choice == DONE:
            try:
                naming.validate_template(template)
            except naming.NamingError as exc:
                forms.alert(u"%s" % exc, title="Nazov este nie je pouzitelny")
                continue
            return {"file_name_segments": segments,
                    "file_name_prefix": prefix,
                    "file_name_suffix": suffix,
                    "file_name_template": naming.build_template(segments)}
        if choice == ADD:
            add_segment(sheet, segments)
        elif choice == EDIT:
            edit_last_segment(segments)
        elif choice == REMOVE:
            if segments:
                segments.pop()
        elif choice == GLOBAL:
            prefix = text_or_empty(forms.ask_for_string(
                default=prefix, title="Prefix celeho nazvu",
                prompt="Text na zaciatku kazdeho suboru, napr. 'DSP_'."))
            suffix = text_or_empty(forms.ask_for_string(
                default=suffix, title="Suffix celeho nazvu",
                prompt="Text na konci kazdeho suboru, napr. '_na-schvalenie'."))
        elif choice == PRESET:
            picked = forms.SelectFromList.show(
                PRESETS, title="Hotove schemy", button_name="Pouzit",
                multiselect=False)
            if picked:
                segments = naming.segments_from_template(picked)
        elif choice == MANUAL:
            typed = forms.ask_for_string(
                default=naming.build_template(segments),
                title="Sablona nazvu",
                prompt=("Tokeny v zlozenych zatvorkach, napr. "
                        "{Sheet Number} - {Sheet Name}\n"
                        "Nahradna hodnota: {Current Revision|00}\n"
                        "Uprava: {Sheet Name:upper}"))
            if typed:
                try:
                    naming.validate_template(typed)
                    segments = naming.segments_from_template(typed)
                except naming.NamingError as exc:
                    forms.alert(u"%s" % exc, title="Chybna sablona")
        elif choice == CLEAR:
            segments, prefix, suffix = [], "", ""


# --- Hlavny priebeh ---------------------------------------------------------

def ask_dwg_options(profile):
    dwg_config = dict(profile.get("dwg") or {})

    setups = dwg_exporter.export_setups(doc)
    if setups:
        choice = forms.SelectFromList.show(
            ["<predvolby Revitu>"] + setups, title="DWG Export Setup",
            button_name="Pouzit", multiselect=False)
        if not choice:
            return None
        dwg_config["export_setup"] = "" if choice.startswith("<") else choice
    else:
        dwg_config["export_setup"] = ""

    dwg_config["external_references"] = not forms.alert(
        "Exportovat kazdy vykres ako jeden samostatny DWG bez externych "
        "referencii?\n\n"
        "Ano  = pohlady a linkovane modely sa zlucia do jedneho suboru.\n"
        "Nie  = Revit vytvori navyse xref subory.",
        title="Externe referencie", yes=True, no=True)
    return dwg_config


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

    schema = build_name_schema(sheets[0], profile)
    if schema is None:
        return
    profile.update(schema)

    combine = False
    if "PDF" in formats and len(sheets) > 1:
        combine = forms.alert("Spojit vsetky vykresy do jedneho PDF suboru?",
                              title="PDF", yes=True, no=True)

    if "DWG" in formats:
        dwg_config = ask_dwg_options(profile)
        if dwg_config is None:
            return
        profile["dwg"] = dwg_config

    subfolders = False
    if len(formats) > 1:
        subfolders = forms.alert(
            "Rozdelit vystup do podpriecinkov PDF a DWG?\n\n"
            "Ano = ...\\PDF\\ a ...\\DWG\\\n"
            "Nie = vsetko dokopy v jednom priecinku.",
            title="Usporiadanie suborov", yes=True, no=True)

    folder = forms.pick_folder(title="Vystupny adresar")
    if not folder:
        return

    profile.update({
        "output_folder": folder,
        "formats": list(formats),
        "subfolder_per_format": bool(subfolders),
        "sheet_selection": {"mode": "numbers",
                            "numbers": [s.SheetNumber for s in sheets]},
    })
    profile.setdefault("pdf", {})["combine"] = bool(combine)

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
