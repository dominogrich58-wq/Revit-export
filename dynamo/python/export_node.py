# -*- coding: utf-8 -*-
"""ProSheets Lite - Dynamo Python node pre davkovy export vykresov.

Vstupy:
  IN[0]  Run              bool    - export sa spusti az pri True
  IN[1]  LibPath          string  - adresar s balikom `prosheets` (napr. C:\\ProSheetsLite\\lib)
  IN[2]  Sheets           list    - konkretne vykresy z Dynama; prazdne = podla Selection
  IN[3]  OutputFolder     string  - vystupny adresar
  IN[4]  Formats          list    - napr. ["PDF", "DWG"]
  IN[5]  FileNameTemplate string  - napr. "{Sheet Number} - {Sheet Name}"
  IN[6]  CombinePDF       bool    - vsetky vykresy do jedneho PDF
  IN[7]  DWGExportSetup   string  - nazov ulozeneho DWG Export Setupu ("" = predvolby)

Vystup: zoznam riadkov s vysledkom pre kazdy vykres + suhrn.
"""

import os
import sys
import traceback

import clr
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager


def _input(index, default=None):
    try:
        value = IN[index]            # noqa: F821 - IN dodava Dynamo
    except (IndexError, NameError):
        return default
    return default if value is None else value


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v not in (None, "")]
    return [value]


def main():
    if not _input(0, False):
        return ["Prepni Run na True a export sa spusti."]

    lib_path = _input(1, "")
    if lib_path and lib_path not in sys.path:
        sys.path.append(lib_path)
    try:
        from prosheets import runner
    except ImportError:
        return ["Balik 'prosheets' sa nenasiel. Do vstupu LibPath zadaj adresar, "
                "ktory obsahuje priecinok 'prosheets' (v repozitari je to 'lib').",
                "Aktualna hodnota LibPath: %r" % lib_path]

    doc = DocumentManager.Instance.CurrentDBDocument
    # Export sa nesmie diat v otvorenej transakcii, ktoru Dynamo drzi.
    TransactionManager.Instance.ForceCloseTransaction()

    selected = _as_list(_input(2))
    sheet_numbers = []
    for item in selected:
        sheet = UnwrapElement(item)  # noqa: F821 - UnwrapElement dodava Dynamo
        if sheet is not None:
            sheet_numbers.append(sheet.SheetNumber)

    config = {
        "output_folder": _input(3, ""),
        "formats": _as_list(_input(4, ["PDF"])) or ["PDF"],
        "file_name_template": _input(5, "{Sheet Number} - {Sheet Name}"),
        "pdf": {"combine": bool(_input(6, False))},
        "dwg": {"export_setup": _input(7, "") or ""},
        "sheet_selection": ({"mode": "numbers", "numbers": sheet_numbers}
                            if sheet_numbers else {"mode": "all"}),
    }

    report = runner.run(doc, config)
    log = report.write_csv(config["output_folder"])
    return report.lines() + ["Log davky: %s" % log]


try:
    OUT = main()
except Exception:
    OUT = ["Export zlyhal:"] + traceback.format_exc().splitlines()
