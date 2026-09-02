# -*- coding: utf-8 -*-
"""Sprava ulozeneho profilu nastaveni ProSheets Lite."""

__title__ = "Profil\nnastaveni"
__doc__ = "Zobrazi, otvori, resetuje alebo prenesie profil exportu (JSON)."

import io
import json
import os
import shutil

from pyrevit import forms

import prosheets_setup
prosheets_setup.ensure()

from prosheets import config as ps_config   # noqa: E402

PATH = prosheets_setup.profile_path()

OPEN = "Otvorit profil v editore"
SHOW = "Zobrazit nastavenia"
RESET = "Obnovit predvolby"
IMPORT = "Nacitat profil zo suboru"
EXPORT = "Ulozit profil do suboru"


def current():
    if os.path.isfile(PATH):
        with io.open(PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return ps_config.defaults()


def main():
    action = forms.CommandSwitchWindow.show(
        [SHOW, OPEN, RESET, IMPORT, EXPORT],
        message="Profil: %s" % ("ulozeny" if os.path.isfile(PATH)
                                else "zatial neexistuje"))
    if not action:
        return

    if action == SHOW:
        text = json.dumps(current(), indent=2, ensure_ascii=False, sort_keys=True)
        forms.alert(text, title="ProSheets Lite - profil")

    elif action == OPEN:
        if not os.path.isfile(PATH):
            ps_config.save(PATH, ps_config.defaults())
        os.startfile(PATH)

    elif action == RESET:
        if forms.alert("Naozaj obnovit predvolene nastavenia?",
                       title="ProSheets Lite", yes=True, no=True):
            ps_config.save(PATH, ps_config.defaults())
            forms.alert("Predvolby obnovene.", title="ProSheets Lite")

    elif action == IMPORT:
        source = forms.pick_file(file_ext="json", title="Vyber profil")
        if not source:
            return
        try:
            ps_config.load(source)          # validacia pred prepisom
        except Exception as exc:
            forms.alert(u"Profil nie je platny:\n%s" % exc, title="ProSheets Lite")
            return
        folder = os.path.dirname(PATH)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        shutil.copyfile(source, PATH)
        forms.alert("Profil nacitany.", title="ProSheets Lite")

    elif action == EXPORT:
        target = forms.save_file(file_ext="json",
                                 default_name="ProSheetsLite-profil")
        if target:
            ps_config.save(target, current())
            forms.alert("Profil ulozeny do:\n%s" % target, title="ProSheets Lite")


main()
