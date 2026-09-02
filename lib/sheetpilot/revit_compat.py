# -*- coding: utf-8 -*-
"""Tenka vrstva nad Revit API - izoluje rozdiely medzi verziami Revitu.

Import Revit API sa deje lenivo, aby sa moduly bez zavislosti na Revite
(naming, config, report) dali importovat a testovat aj mimo Revitu.
"""


class RevitApiUnavailable(Exception):
    """Vyhodena, ked kod bezi mimo Revitu a pyta si Revit API."""


_DB = None


def db():
    """Vrati modul Autodesk.Revit.DB (nacita ho pri prvom pouziti)."""
    global _DB
    if _DB is None:
        try:
            import clr
            clr.AddReference("RevitAPI")
            from Autodesk.Revit import DB
        except Exception as exc:                     # pragma: no cover - iba v Revite
            raise RevitApiUnavailable(
                "Revit API nie je dostupne v tomto prostredi: %s" % exc)
        _DB = DB
    return _DB


def revit_version(doc):
    """Rok verzie Revitu ako int, napr. 2024."""
    try:
        return int(doc.Application.VersionNumber)
    except Exception:                                # pragma: no cover
        return 0


def supports_native_pdf(doc):
    """PDFExportOptions pribudlo v Revite 2022."""
    return revit_version(doc) >= 2022 and hasattr(db(), "PDFExportOptions")


def element_id_value(element_id):
    """Hodnota ElementId - `Value` od 2024, `IntegerValue` predtym."""
    for attribute in ("Value", "IntegerValue"):
        if hasattr(element_id, attribute):
            return getattr(element_id, attribute)
    return int(str(element_id))                      # pragma: no cover


def to_element_id_list(ids):
    """Python zoznam ElementId -> List[ElementId] pre Revit API."""
    import System.Collections.Generic as generic
    typed = generic.List[db().ElementId]()
    for element_id in ids:
        typed.Add(element_id)
    return typed


def enum_value(enum_type_name, member, default=None):
    """Bezpecne ziskanie hodnoty enumu, ktory v starsej verzii nemusi existovat."""
    enum_type = getattr(db(), enum_type_name, None)
    if enum_type is None:
        return default
    return getattr(enum_type, member, default)
