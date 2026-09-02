# -*- coding: utf-8 -*-
"""Nastavenia exportu - predvolby, nacitanie a ulozenie profilu do JSON.

Modul nema zavislost na Revit API, takze profil sa da pripravit aj mimo Revitu
(napr. v CI alebo v testoch).
"""

import copy
import io
import json
import os

from ._compat import string_types, text_type

SUPPORTED_FORMATS = ("PDF", "DWG")

DEFAULTS = {
    "output_folder": "",
    "formats": ["PDF"],
    "file_name_template": "{Sheet Number} - {Sheet Name}",
    "subfolder_per_format": True,
    "overwrite": True,
    "sheet_selection": {
        "mode": "all",            # all | set | numbers | filter
        "set_name": "",
        "numbers": [],
        "number_prefix": "",
        "name_contains": "",
        "parameter_equals": {},
    },
    "pdf": {
        "combine": False,
        "combined_file_name": "{File Name} - vykresy",
        "raster_quality": "High",      # Low | Medium | High | Presentation
        "color_depth": "Color",        # BlackLine | GrayScale | Color
        "zoom": 100,
        "hide_crop_boundaries": True,
        "hide_scope_boxes": True,
        "hide_reference_planes": True,
        "hide_unreferenced_view_tags": True,
        "mask_coincident_lines": False,
        "view_links_in_blue": False,
        "always_use_raster": False,
        "stop_on_error": False,
    },
    "dwg": {
        "export_setup": "",            # nazov ulozeneho DWG Export Setupu
        "file_version": "AutoCAD2018",
        "merge_views": False,
        "shared_coords": False,
    },
}


class ConfigError(ValueError):
    """Neplatne nastavenia exportu."""


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def defaults():
    return copy.deepcopy(DEFAULTS)


def normalize(user_config=None):
    """Doplni chybajuce klice predvolbami a skontroluje hodnoty."""
    config = _deep_merge(DEFAULTS, user_config)

    formats = config.get("formats") or []
    if isinstance(formats, string_types):
        formats = [part.strip() for part in formats.replace(";", ",").split(",")]
    normalized_formats = []
    for fmt in formats:
        upper = (fmt or "").strip().upper()
        if not upper:
            continue
        if upper not in SUPPORTED_FORMATS:
            raise ConfigError("Nepodporovany format '%s'. Podporovane: %s"
                              % (fmt, ", ".join(SUPPORTED_FORMATS)))
        if upper not in normalized_formats:
            normalized_formats.append(upper)
    if not normalized_formats:
        raise ConfigError("Nie je zvoleny ziadny format exportu (PDF / DWG).")
    config["formats"] = normalized_formats

    mode = (config["sheet_selection"].get("mode") or "all").strip().lower()
    if mode not in ("all", "set", "numbers", "filter"):
        raise ConfigError("Neznamy rezim vyberu vykresov: '%s' "
                          "(pouzi all, set, numbers alebo filter)." % mode)
    config["sheet_selection"]["mode"] = mode
    if mode == "set" and not config["sheet_selection"].get("set_name"):
        raise ConfigError("Rezim 'set' vyzaduje nazov Sheet Setu "
                          "(sheet_selection.set_name).")
    if mode == "numbers" and not config["sheet_selection"].get("numbers"):
        raise ConfigError("Rezim 'numbers' vyzaduje zoznam cisel vykresov "
                          "(sheet_selection.numbers).")

    if not config.get("output_folder"):
        raise ConfigError("Nie je nastaveny vystupny adresar (output_folder).")
    config["output_folder"] = os.path.abspath(
        os.path.expanduser(config["output_folder"]))

    zoom = config["pdf"].get("zoom", 100)
    try:
        config["pdf"]["zoom"] = max(1, min(1000, int(zoom)))
    except (TypeError, ValueError):
        raise ConfigError("pdf.zoom musi byt cislo v percentach, dostal som %r" % zoom)

    from . import naming
    naming.validate_template(config["file_name_template"])
    if config["pdf"]["combine"]:
        naming.validate_template(config["pdf"]["combined_file_name"])

    return config


def load(path):
    """Nacita profil z JSON suboru a doplni predvolby."""
    with io.open(path, "r", encoding="utf-8") as handle:
        return normalize(json.load(handle))


def save(path, config):
    """Ulozi profil do JSON suboru (adresar sa v pripade potreby vytvori)."""
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with io.open(path, "w", encoding="utf-8") as handle:
        text = json.dumps(config, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write(text if isinstance(text, text_type) else text.decode("utf-8"))
    return path
