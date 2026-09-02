# -*- coding: utf-8 -*-
"""Sprava pomenovanych profilov SheetPilot."""

__title__ = "Profily"
__doc__ = ("Vytvori, prepne, premenuje, skopiruje, zmaze alebo prenesie "
           "profil nastaveni exportu.")

import json
import os
import shutil

from pyrevit import forms

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot import config as sp_config   # noqa: E402
from sheetpilot import profiles              # noqa: E402

STORE = sheetpilot_setup.store()

SWITCH = "Prepnut aktivny profil"
NEW = "Novy profil z predvolieb"
COPY = "Skopirovat aktivny profil"
SHOW = "Zobrazit nastavenia aktivneho profilu"
OPEN = "Otvorit aktivny profil v editore"
RENAME = "Premenovat aktivny profil"
DELETE = "Zmazat profil"
IMPORT = "Nacitat profil zo suboru"
EXPORT = "Ulozit aktivny profil do suboru"


def active_or_warn():
    name = STORE.active_name()
    if not name:
        forms.alert("Nie je zvoleny ziadny profil. Vytvor ho volbou "
                    "'Novy profil z predvolieb' alebo spusti export.",
                    title="SheetPilot")
    return name


def pick_profile(title):
    names = STORE.names()
    if not names:
        forms.alert("Zatial nie je ulozeny ziadny profil.", title="SheetPilot")
        return None
    if len(names) == 1:
        return names[0]
    return forms.SelectFromList.show(names, title=title, button_name="Vybrat",
                                     multiselect=False)


def ask_name(title, default=""):
    while True:
        name = forms.ask_for_string(default=default, title=title,
                                    prompt="Nazov profilu:")
        if not name:
            return None
        try:
            return profiles.safe_name(name)
        except profiles.ProfileError as exc:
            forms.alert(u"%s" % exc, title="SheetPilot")


def main():
    active = STORE.active_name()
    message = ("Aktivny profil: %s\nUlozenych profilov: %d"
               % (active or "ziadny", len(STORE.names())))

    action = forms.CommandSwitchWindow.show(
        [SWITCH, NEW, COPY, SHOW, OPEN, RENAME, DELETE, IMPORT, EXPORT],
        message=message)
    if not action:
        return

    if action == SWITCH:
        name = pick_profile("Ktory profil pouzivat?")
        if name:
            STORE.set_active(name)
            forms.alert("Aktivny profil je teraz '%s'." % name,
                        title="SheetPilot")

    elif action == NEW:
        name = ask_name("Novy profil")
        if name:
            if STORE.exists(name) and not forms.alert(
                    "Profil '%s' uz existuje. Prepisat ho?" % name,
                    title="SheetPilot", yes=True, no=True):
                return
            STORE.save(name, sp_config.defaults())
            STORE.set_active(name)
            forms.alert("Profil '%s' vytvoreny a nastaveny ako aktivny.\n\n"
                        "Vystupny adresar a schemu nazvov mu nastavis pri "
                        "najblizsom exporte." % name, title="SheetPilot")

    elif action == COPY:
        source = active_or_warn()
        if not source:
            return
        name = ask_name("Kopia profilu", default=source + " - kopia")
        if name:
            STORE.duplicate(source, name)
            STORE.set_active(name)
            forms.alert("Vytvorena kopia '%s'." % name, title="SheetPilot")

    elif action == SHOW:
        name = active_or_warn()
        if name:
            text = json.dumps(STORE.load(name), indent=2, ensure_ascii=False,
                              sort_keys=True)
            forms.alert(text, title="Profil %s" % name)

    elif action == OPEN:
        name = active_or_warn()
        if name:
            os.startfile(STORE.path_for(name))

    elif action == RENAME:
        old = active_or_warn()
        if not old:
            return
        name = ask_name("Premenovat profil", default=old)
        if name and name != old:
            STORE.rename(old, name)
            forms.alert("Premenovane na '%s'." % name, title="SheetPilot")

    elif action == DELETE:
        name = pick_profile("Ktory profil zmazat?")
        if name and forms.alert("Naozaj zmazat profil '%s'?" % name,
                                title="SheetPilot", yes=True, no=True):
            STORE.delete(name)
            forms.alert("Profil '%s' zmazany." % name, title="SheetPilot")

    elif action == IMPORT:
        source = forms.pick_file(file_ext="json", title="Vyber subor s profilom")
        if not source:
            return
        try:
            data = sp_config.load(source)
        except Exception as exc:
            forms.alert(u"Subor nie je platny profil:\n%s" % exc,
                        title="SheetPilot")
            return
        default = os.path.splitext(os.path.basename(source))[0]
        name = ask_name("Nacitany profil ulozit ako", default=default)
        if name:
            STORE.save(name, data)
            STORE.set_active(name)
            forms.alert("Profil '%s' nacitany a nastaveny ako aktivny." % name,
                        title="SheetPilot")

    elif action == EXPORT:
        name = active_or_warn()
        if not name:
            return
        target = forms.save_file(file_ext="json", default_name=name)
        if target:
            shutil.copyfile(STORE.path_for(name), target)
            forms.alert("Profil ulozeny do:\n%s" % target, title="SheetPilot")


main()
