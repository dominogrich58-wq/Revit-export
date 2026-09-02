# -*- coding: utf-8 -*-
"""Export vykresov do DWG.

Ak je v konfiguracii uvedeny nazov ulozeneho DWG Export Setupu
(Revit: File > Export > Options > Export Setups DWG/DXF), pouziju sa jeho
nastavenia vrstiev, hladin, textov a liniek. Inak sa pouziju predvolby Revitu.

Exportuje sa vzdy po jednom vykrese - vtedy Revit pouzije presne nazov,
ktory mu dame. Pri viacerych vykresoch naraz si k nazvu prilepi nazvy pohladov.
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


def build_options(doc, dwg_config):
    """Zostavi DWGExportOptions - z ulozeneho setupu alebo z predvolieb."""
    DB = db()
    setup_name = (dwg_config.get("export_setup") or "").strip()
    options = None
    if setup_name:
        settings = DB.ExportDWGSettings.GetPredefinedSettings(doc, setup_name)
        if settings is None:
            raise KeyError("DWG Export Setup '%s' sa v modeli nenasiel. "
                           "Dostupne: %s"
                           % (setup_name, ", ".join(export_setups(doc)) or "ziadne"))
        options = settings.GetDWGExportOptions()
    if options is None:
        options = DB.DWGExportOptions()

    version = ACAD_VERSIONS.get(
        (dwg_config.get("file_version") or "").strip().lower().replace(" ", ""))
    if version and hasattr(DB, "ACADVersion"):
        acad = getattr(DB.ACADVersion, version, None)
        if acad is not None:
            options.FileVersion = acad

    options.MergedViews = bool(dwg_config.get("merge_views"))
    if dwg_config.get("shared_coords") and hasattr(DB, "ExportSharedCoordinates"):
        options.SharedCoords = True
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
