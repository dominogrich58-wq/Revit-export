# -*- coding: utf-8 -*-
"""Sprava ulozeneho profilu nastaveni SheetPilot."""

__title__ = "Profil\nnastaveni"
__doc__ = "Zobrazi, otvori, resetuje alebo prenesie profil exportu (JSON)."

import io
import json
import os
import shutil

from pyrevit import forms

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot import config as sp_config   # noqa: E402

PATH = sheetpilot_setup.profile_path()

OPEN = "Otvorit profil v editore"
SHOW = "Zobrazit nastavenia"
RESET = "Obnovit predvolby"
IMPORT = "Nacitat profil zo suboru"
EXPORT = "Ulozit profil do suboru"


def current():
    if os.path.isfile(PATH):
        with io.open(PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return sp_config.defaults()


def main():
    action = forms.CommandSwitchWindow.show(
        [SHOW, OPEN, RESET, IMPORT, EXPORT],
        message="Profil: %s" % ("ulozeny" if os.path.isfile(PATH)
                                else "zatial neexistuje"))
    if not action:
        return

    if action == SHOW:
        text = json.dumps(current(), indent=2, ensure_ascii=False, sort_keys=True)
        forms.alert(text, title="SheetPilot - profil")

    elif action == OPEN:
        if not os.path.isfile(PATH):
            sp_config.save(PATH, sp_config.defaults())
        os.startfile(PATH)

    elif action == RESET:
        if forms.alert("Naozaj obnovit predvolene nastavenia?",
                       title="SheetPilot", yes=True, no=True):
            sp_config.save(PATH, sp_config.defaults())
            forms.alert("Predvolby obnovene.", title="SheetPilot")

    elif action == IMPORT:
        source = forms.pick_file(file_ext="json", title="Vyber profil")
        if not source:
            return
        try:
            sp_config.load(source)          # validacia pred prepisom
        except Exception as exc:
            forms.alert(u"Profil nie je platny:\n%s" % exc, title="SheetPilot")
            return
        folder = os.path.dirname(PATH)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        shutil.copyfile(source, PATH)
        forms.alert("Profil nacitany.", title="SheetPilot")

    elif action == EXPORT:
        target = forms.save_file(file_ext="json",
                                 default_name="SheetPilot-profil")
        if target:
            sp_config.save(target, current())
            forms.alert("Profil ulozeny do:\n%s" % target, title="SheetPilot")


main()
