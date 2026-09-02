# -*- coding: utf-8 -*-
"""Pomenovane profily nastaveni - viac schem exportu vedla seba.

Kazdy profil je jeden JSON subor v adresari `profiles`. Vedla nich lezi
`state.json` s nazvom aktivneho profilu, aby si tlacidla pamatali, s cim
sa naposledy pracovalo.

    %APPDATA%\\SheetPilot\\
        profiles\\
            DSP odovzdanie.json
            Rychly nahlad PDF.json
        state.json

Modul nema zavislost na Revit API, takze sa da testovat mimo Revitu.
"""

import io
import json
import os

from . import config as config_mod
from . import naming

EXTENSION = ".json"
STATE_FILE = "state.json"
DEFAULT_NAME = "Predvoleny"


class ProfileError(ValueError):
    """Neplatny nazov profilu alebo chybajuci profil."""


def safe_name(name):
    """Nazov profilu ocisteny tak, aby sa dal pouzit ako nazov suboru."""
    cleaned = naming.sanitize((name or "").strip())
    if not cleaned or cleaned == "bez-nazvu":
        raise ProfileError("Nazov profilu nesmie byt prazdny.")
    return cleaned


class ProfileStore(object):
    """Adresar s profilmi."""

    def __init__(self, folder):
        self.folder = folder
        self.profiles_folder = os.path.join(folder, "profiles")

    # --- pomocne -----------------------------------------------------------

    def _ensure_folder(self):
        if not os.path.isdir(self.profiles_folder):
            os.makedirs(self.profiles_folder)

    def path_for(self, name):
        return os.path.join(self.profiles_folder, safe_name(name) + EXTENSION)

    def _read_json(self, path):
        with io.open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path, data):
        text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(text if isinstance(text, type(u"")) else text.decode("utf-8"))

    # --- profily -----------------------------------------------------------

    def names(self):
        """Nazvy ulozenych profilov, zoradene."""
        if not os.path.isdir(self.profiles_folder):
            return []
        return sorted(os.path.splitext(entry)[0]
                      for entry in os.listdir(self.profiles_folder)
                      if entry.lower().endswith(EXTENSION))

    def exists(self, name):
        return os.path.isfile(self.path_for(name))

    def load(self, name):
        """Nacita profil a doplni predvolby. Vyhodi ProfileError, ak nie je."""
        path = self.path_for(name)
        if not os.path.isfile(path):
            raise ProfileError("Profil '%s' neexistuje. Dostupne: %s"
                               % (name, ", ".join(self.names()) or "ziadne"))
        return config_mod.normalize(self._read_json(path))

    def save(self, name, config):
        """Ulozi profil. Vracia nazov, pod ktorym sa naozaj ulozil."""
        self._ensure_folder()
        effective = safe_name(name)
        self._write_json(self.path_for(effective), config)
        return effective

    def delete(self, name):
        path = self.path_for(name)
        if not os.path.isfile(path):
            raise ProfileError("Profil '%s' neexistuje." % name)
        os.remove(path)
        if self.active_name() == safe_name(name):
            self.set_active(None)

    def rename(self, old_name, new_name):
        """Premenuje profil; vracia novy nazov."""
        data = self.load(old_name)
        old = safe_name(old_name)
        # Zapamatat si to treba pred mazanim - delete() ukazovatel na
        # aktivny profil sam vynuluje.
        was_active = self.active_name() == old
        effective = self.save(new_name, data)
        if effective != old:
            self.delete(old_name)
        if was_active:
            self.set_active(effective)
        return effective

    def duplicate(self, name, new_name):
        return self.save(new_name, self.load(name))

    # --- aktivny profil ----------------------------------------------------

    def _state_path(self):
        return os.path.join(self.folder, STATE_FILE)

    def active_name(self):
        """Nazov naposledy pouziteho profilu, alebo None."""
        path = self._state_path()
        if not os.path.isfile(path):
            return None
        try:
            name = self._read_json(path).get("active")
        except (ValueError, IOError):
            return None
        return name if name and self.exists(name) else None

    def set_active(self, name):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        self._write_json(self._state_path(),
                         {"active": safe_name(name) if name else None})

    def active(self):
        """Nastavenia aktivneho profilu, alebo predvolby ak ziadny nie je."""
        name = self.active_name()
        return self.load(name) if name else config_mod.defaults()

    # --- prechod zo stareho jedneho profilu --------------------------------

    def migrate_legacy(self, legacy_path, name=DEFAULT_NAME):
        """Prenesie stary jednosuborovy profil medzi pomenovane.

        Vracia nazov vznikleho profilu, alebo None ak nebolo co preniest.
        Stary subor sa necha na mieste - nic sa nemaze.
        """
        if self.names() or not os.path.isfile(legacy_path):
            return None
        try:
            data = self._read_json(legacy_path)
        except (ValueError, IOError):
            return None
        effective = self.save(name, data)
        self.set_active(effective)
        return effective
