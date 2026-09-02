# -*- coding: utf-8 -*-
"""ProSheets Lite - pomocny node: zoznam vykresov, Sheet Setov a DWG setupov.

Vstupy:
  IN[0] LibPath  string - adresar s balikom `prosheets`
  IN[1] SheetSet string - ak je vyplneny, vrati len vykresy z tohto Sheet Setu

Vystup: [zoznam vykresov, nazvy Sheet Setov, nazvy DWG Export Setupov]
"""

import sys
import traceback

import clr
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager


def main():
    lib_path = IN[0] if len(IN) > 0 and IN[0] else ""   # noqa: F821
    if lib_path and lib_path not in sys.path:
        sys.path.append(lib_path)
    from prosheets import sheets as sheets_mod
    from prosheets.exporters import dwg as dwg_exporter

    doc = DocumentManager.Instance.CurrentDBDocument
    set_name = IN[1] if len(IN) > 1 and IN[1] else ""   # noqa: F821

    found = (sheets_mod.sheets_from_set(doc, set_name) if set_name
             else sheets_mod.all_sheets(doc))
    return [found,
            sheets_mod.sheet_sets(doc),
            dwg_exporter.export_setups(doc)]


try:
    OUT = main()
except Exception:
    OUT = traceback.format_exc().splitlines()
