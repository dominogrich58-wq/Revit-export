# -*- coding: utf-8 -*-
"""Overovaci skript - ziadna zavislost na ProSheets Lite.

Sluzi len na zistenie, ci pyRevit v danom Revite vobec dokaze postavit
vlastnu zalozku a spustit skript. Ak sa toto tlacidlo objavi a funguje,
problem je v balicku ProSheetsLite; ak sa neobjavi, problem je v pyRevite
alebo v nastaveni Custom Extension Directories.

Priecinok PyRevitTest.extension sa da po overeni pokojne zmazat.
"""

__title__ = "Test"
__doc__ = "Overi, ze pyRevit funguje - vypise verziu Revitu a nazov modelu."

import sys

from pyrevit import forms, revit

forms.alert(
    "pyRevit funguje.\n\n"
    "Revit: %s\n"
    "Python engine: %s\n"
    "Model: %s" % (revit.doc.Application.VersionNumber,
                   sys.version.split()[0],
                   revit.doc.Title),
    title="pyRevit test")
