# -*- coding: utf-8 -*-
"""SheetPilot - davkovy export vykresov do PDF a DWG."""

__title__ = "Export\nvykresov"
__doc__ = ("Jedno okno: vyber vykresov, formaty, schema nazvov a vystupny "
           "adresar. Po spusteni sa okno prepne na priebeh a vysledok.")

from pyrevit import forms, revit

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot_ui import ExportWindow   # noqa: E402


def main():
    doc = revit.doc
    if doc is None:
        forms.alert("Najprv otvor projekt.", title="SheetPilot")
        return

    from sheetpilot.sheets import all_sheets
    if not all_sheets(doc):
        forms.alert("Model neobsahuje žiadne výkresy na export.",
                    title="SheetPilot")
        return

    ExportWindow(doc, sheetpilot_setup.store()).ShowDialog()


main()
