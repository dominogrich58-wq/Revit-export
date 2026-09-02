# -*- coding: utf-8 -*-
"""Najde balik `sheetpilot` a prida ho do sys.path.

Hlada v tomto poradi:
  1. premenna prostredia SHEETPILOT_LIB
  2. adresar `lib` vedla extensionu (ked je extension sucastou repozitara)
  3. `lib` priamo v extensione (sebestacna kopia)
  4. %APPDATA%\\SheetPilot\\lib
  5. C:\\SheetPilot\\lib (miesto z navodu pre Dynamo - aby stacila
     jedna kopia kniznice pre Dynamo aj pyRevit)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _candidates():
    env = os.environ.get("SHEETPILOT_LIB")
    if env:
        yield env
    # .../pyrevit/SheetPilot.extension/lib -> korenovy 'lib' repozitara
    repo_root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    yield os.path.join(repo_root, "lib")
    yield HERE
    appdata = os.environ.get("APPDATA")
    if appdata:
        yield os.path.join(appdata, "SheetPilot", "lib")
    yield os.path.join(os.environ.get("SystemDrive", "C:") + os.sep,
                       "SheetPilot", "lib")


def ensure():
    """Zabezpeci importovatelnost baliku `sheetpilot`; vrati pouzity adresar."""
    for folder in _candidates():
        if folder and os.path.isdir(os.path.join(folder, "sheetpilot")):
            if folder not in sys.path:
                sys.path.append(folder)
            return folder
    raise ImportError(
        "Balik 'sheetpilot' sa nenasiel. Skopiruj priecinok 'sheetpilot' "
        "(z 'lib' v repozitari) do niektoreho z tychto miest:\n  "
        + "\n  ".join(f for f in _candidates() if f))


def profile_path():
    """Cesta k ulozenemu profilu nastaveni."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "SheetPilot", "profile.json")
