# -*- coding: utf-8 -*-
"""Export vykresov do PDF.

Primarne sa pouziva nativny `PDFExportOptions` (Revit 2022 a novsi).
Aby sme mali plnu kontrolu nad nazvom suboru, exportuje sa vzdy s
`Combine = True` - aj pri jedinom vykrese - lebo v tom rezime Revit pouzije
presne nazov z `PDFExportOptions.FileName`. Pri `Combine = False` si Revit
sklada nazov sam podla naming rules, co by nam schemu nazvov rozbilo.

Pre Revit 2021 a starsi je k dispozicii zaloha cez tlac na virtualnu
PDF tlaciaren (`print_via_driver`).
"""

import os

from ..revit_compat import db, to_element_id_list, supports_native_pdf

RASTER_QUALITY = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "presentation": "Presentation",
}

COLOR_DEPTH = {
    "blackline": "BlackLine",
    "black line": "BlackLine",
    "grayscale": "GrayScale",
    "greyscale": "GrayScale",
    "color": "Color",
    "colour": "Color",
}


def _set(options, name, value):
    """Nastavi vlastnost, ak ju dana verzia Revitu pozna."""
    if value is None or not hasattr(options, name):
        return False
    try:
        setattr(options, name, value)
        return True
    except Exception:
        return False


def _enum(type_name, member):
    enum_type = getattr(db(), type_name, None)
    if enum_type is None or member is None:
        return None
    return getattr(enum_type, member, None)


def build_options(pdf_config):
    """Zostavi PDFExportOptions z konfiguracie."""
    DB = db()
    options = DB.PDFExportOptions()

    quality = RASTER_QUALITY.get((pdf_config.get("raster_quality") or "").lower())
    _set(options, "RasterQuality", _enum("RasterQualityType", quality))
    depth = COLOR_DEPTH.get((pdf_config.get("color_depth") or "").lower())
    _set(options, "ColorDepth", _enum("ColorDepthType", depth))

    zoom = int(pdf_config.get("zoom", 100) or 100)
    if zoom == 100:
        _set(options, "ZoomType", _enum("ZoomType", "FitToPage"))
    else:
        _set(options, "ZoomType", _enum("ZoomType", "Zoom"))
        _set(options, "ZoomPercentage", zoom)

    _set(options, "HideCropBoundaries", bool(pdf_config.get("hide_crop_boundaries")))
    _set(options, "HideScopeBoxes", bool(pdf_config.get("hide_scope_boxes")))
    _set(options, "HideReferencePlane", bool(pdf_config.get("hide_reference_planes")))
    _set(options, "HideUnreferencedViewTags",
         bool(pdf_config.get("hide_unreferenced_view_tags")))
    _set(options, "MaskCoincidentLines", bool(pdf_config.get("mask_coincident_lines")))
    _set(options, "ViewLinksInBlue", bool(pdf_config.get("view_links_in_blue")))
    _set(options, "AlwaysUseRaster", bool(pdf_config.get("always_use_raster")))
    _set(options, "StopOnError", bool(pdf_config.get("stop_on_error")))
    _set(options, "PaperFormat", _enum("ExportPaperFormat", "Default"))
    _set(options, "PaperPlacement", _enum("PaperPlacementType", "Center"))
    return options


def export(doc, sheets, folder, file_name, pdf_config):
    """Exportuje vykresy do jedneho PDF suboru s presne danym nazvom.

    `sheets` moze byt jeden vykres (samostatny subor) alebo viac vykresov
    (spojene PDF). Vracia cestu k vytvorenemu suboru.
    """
    if not supports_native_pdf(doc):
        raise RuntimeError(
            "Tento Revit (verzia %s) nema nativny PDF export. Pouzi "
            "print_via_driver() s virtualnou PDF tlaciarnou."
            % doc.Application.VersionNumber)

    options = build_options(pdf_config)
    _set(options, "Combine", True)
    _set(options, "FileName", file_name)

    if not os.path.isdir(folder):
        os.makedirs(folder)

    view_ids = to_element_id_list([s.Id for s in sheets])
    if not doc.Export(folder, view_ids, options):
        raise RuntimeError("Revit odmietol export PDF (doc.Export vratil False).")

    path = os.path.join(folder, file_name + ".pdf")
    if not os.path.isfile(path):
        raise RuntimeError("Revit export nahlasil uspech, ale subor '%s' "
                           "neexistuje." % path)
    return path


def available_printers():
    """Nazvy tlaciarni nainstalovanych na stanici - pre PDF zalohu."""
    import System.Drawing.Printing as printing
    return list(printing.PrinterSettings.InstalledPrinters)


def print_via_driver(doc, sheet, folder, file_name, printer_name):
    """Zaloha pre Revit 2021 a starsi: tlac vykresu na virtualnu PDF tlaciaren.

    Vyzaduje tlaciaren, ktora vie tlacit do suboru bez dialogu
    (napr. 'Microsoft Print to PDF' alebo Bluebeam PDF).
    """
    DB = db()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, file_name + ".pdf")

    manager = doc.PrintManager
    manager.SelectNewPrintDriver(printer_name)
    manager.PrintRange = DB.PrintRange.Select
    manager.PrintToFile = True
    manager.CombinedFile = False

    view_set = DB.ViewSet()
    view_set.Insert(sheet)
    sheet_setting = manager.ViewSheetSetting
    sheet_setting.CurrentViewSheetSet.Views = view_set

    manager.PrintToFileName = path
    manager.Apply()
    manager.SubmitPrint()
    return path
