# -*- coding: utf-8 -*-
"""Export vykresov do DWG.

Ak je v konfiguracii uvedeny nazov ulozeneho DWG Export Setupu
(Revit: File > Export > Options > Export Setups DWG/DXF), pouziju sa jeho
nastavenia vrstiev, hladin, textov a liniek. Inak sa pouziju predvolby Revitu.

Exportuje sa vzdy po jednom vykrese - vtedy Revit pouzije presne nazov,
ktory mu dame. Pri viacerych vykresoch naraz si k nazvu prilepi nazvy pohladov.

Volba `external_references` riadi, ci Revit vytvori vedla hlavneho DWG este
xref subory pre pohlady na vykrese a pre linkovane modely. Predvolene je
vypnuta, takze vznikne jeden samostatny DWG na vykres.
"""

import os

from ..revit_compat import db, to_element_id_list

ACAD_VERSIONS = {
    "autocad2018": "R2018", "2018": "R2018", "r2018": "R2018",
    "autocad2013": "R2013", "2013": "R2013", "r2013": "R2013",
    "autocad2010": "R2010", "2010": "R2010", "r2010": "R2010",
    "autocad2007": "R2007", "2007": "R2007", "r2007": "R2007",
    "autocad2004": "R2004", "2004": "R2004", "r2004": "R2004",
    "autocad2000": "R2000", "2000": "R2000", "r2000": "R2000",
}


def export_setups(doc):
    """Nazvy DWG Export Setupov ulozenych v modeli."""
    DB = db()
    return sorted(s.Name for s in DB.FilteredElementCollector(doc)
                  .OfClass(DB.ExportDWGSettings))


def _set(options, name, value):
    """Nastavi vlastnost, ak ju dana verzia Revitu pozna."""
    if not hasattr(options, name):
        return False
    try:
        setattr(options, name, value)
        return True
    except Exception:
        return False


def predefined_options(doc, setup_name):
    """DWGExportOptions z ulozeneho Export Setupu, alebo None ak setup nie je.

    Revit ponuka dve cesty k tomu istemu a kazda verzia ma inu z nich:
    staticku `DWGExportOptions.GetPredefinedOptions`, alebo najdenie
    elementu `ExportDWGSettings` a jeho `GetDWGExportOptions()`. Skusame
    obe, aby kod nezavisel na jednej konkretnej verzii API.
    """
    DB = db()
    getter = getattr(DB.DWGExportOptions, "GetPredefinedOptions", None)
    if getter is not None:
        try:
            options = getter(doc, setup_name)
        except Exception:
            options = None
        if options is not None:
            return options

    for settings in DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings):
        if settings.Name == setup_name:
            return settings.GetDWGExportOptions()
    return None


def build_options(doc, dwg_config):
    """Zostavi DWGExportOptions - z ulozeneho setupu alebo z predvolieb."""
    DB = db()
    setup_name = (dwg_config.get("export_setup") or "").strip()
    options = None
    if setup_name:
        options = predefined_options(doc, setup_name)
        if options is None:
            raise KeyError("DWG Export Setup '%s' sa v modeli nenasiel. "
                           "Dostupne: %s"
                           % (setup_name, ", ".join(export_setups(doc)) or "ziadne"))
    if options is None:
        options = DB.DWGExportOptions()

    version = ACAD_VERSIONS.get(
        (dwg_config.get("file_version") or "").strip().lower().replace(" ", ""))
    if version and hasattr(DB, "ACADVersion"):
        acad = getattr(DB.ACADVersion, version, None)
        if acad is not None:
            _set(options, "FileVersion", acad)

    # MergedViews je opak volby "Export views on sheets and links as
    # external references" v DWG Export Setupe: zlucene = ziadne xref subory.
    _set(options, "MergedViews", not bool(dwg_config.get("external_references")))
    if dwg_config.get("shared_coords"):
        _set(options, "SharedCoords", True)
    return options


def export(doc, sheet, folder, file_name, options):
    """Exportuje jeden vykres do DWG a vrati cestu k suboru."""
    if not os.path.isdir(folder):
        os.makedirs(folder)

    view_ids = to_element_id_list([sheet.Id])
    if not doc.Export(folder, file_name, view_ids, options):
        raise RuntimeError("Revit odmietol export DWG (doc.Export vratil False).")

    path = os.path.join(folder, file_name + ".dwg")
    if not os.path.isfile(path):
        raise RuntimeError("Revit export nahlasil uspech, ale subor '%s' "
                           "neexistuje." % path)
    return path
