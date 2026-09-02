# -*- coding: utf-8 -*-
"""Najde balik `prosheets` a prida ho do sys.path.

Hlada v tomto poradi:
  1. premenna prostredia PROSHEETS_LIB
  2. adresar `lib` vedla extensionu (ked je extension sucastou repozitara)
  3. %APPDATA%\\ProSheetsLite\\lib (rucna instalacia)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _candidates():
    env = os.environ.get("PROSHEETS_LIB")
    if env:
        yield env
    # .../pyrevit/ProSheetsLite.extension/lib -> korenovy 'lib' repozitara
    repo_root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    yield os.path.join(repo_root, "lib")
    yield HERE
    appdata = os.environ.get("APPDATA")
    if appdata:
        yield os.path.join(appdata, "ProSheetsLite", "lib")


def ensure():
    """Zabezpeci importovatelnost baliku `prosheets`; vrati pouzity adresar."""
    for folder in _candidates():
        if folder and os.path.isdir(os.path.join(folder, "prosheets")):
            if folder not in sys.path:
                sys.path.append(folder)
            return folder
    raise ImportError(
        "Balik 'prosheets' sa nenasiel. Skopiruj priecinok 'lib/prosheets' do "
        "%APPDATA%\\ProSheetsLite\\lib alebo nastav premennu PROSHEETS_LIB.")


def profile_path():
    """Cesta k ulozenemu profilu nastaveni."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ProSheetsLite", "profile.json")
