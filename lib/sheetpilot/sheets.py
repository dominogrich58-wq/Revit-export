# -*- coding: utf-8 -*-
"""Vyber vykresov (sheets) a citanie ich parametrov pre nazvy suborov."""

import datetime
import os
import re

from ._compat import string_types
from .revit_compat import db, element_id_value


def all_sheets(doc, include_placeholders=False):
    """Vsetky vykresy v modeli, zoradene podla cisla vykresu."""
    DB = db()
    collector = (DB.FilteredElementCollector(doc)
                 .OfClass(DB.ViewSheet)
                 .WhereElementIsNotElementType())
    sheets = [s for s in collector
              if include_placeholders or not s.IsPlaceholder]
    return sort_sheets(sheets)


def sheet_sets(doc):
    """Nazvy ulozenych View/Sheet Setov v modeli."""
    DB = db()
    return sorted(s.Name for s in DB.FilteredElementCollector(doc)
                  .OfClass(DB.ViewSheetSet))


def sheets_from_set(doc, set_name):
    """Vykresy z ulozeneho Sheet Setu (View Set v dialogu Print/Export)."""
    DB = db()
    for sheet_set in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheetSet):
        if sheet_set.Name != set_name:
            continue
        sheets = [v for v in sheet_set.Views
                  if isinstance(v, DB.ViewSheet) and not v.IsPlaceholder]
        return sort_sheets(sheets)
    raise KeyError("Sheet Set '%s' sa v modeli nenasiel. Dostupne: %s"
                   % (set_name, ", ".join(sheet_sets(doc)) or "ziadne"))


_NUM_CHUNK = re.compile(r"(\d+)")


def _natural_key(text):
    """'A-10' sa zoradi az za 'A-9' (prirodzene, nie abecedne)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in _NUM_CHUNK.split(text or "")]


def sort_sheets(sheets):
    return sorted(sheets, key=lambda s: _natural_key(s.SheetNumber))


def filter_sheets(sheets, numbers=None, number_prefix=None, name_contains=None,
                  parameter_equals=None):
    """Zuzi zoznam vykresov. Vsetky kriteria plati sucasne (AND)."""
    result = list(sheets)
    if numbers:
        wanted = set(n.strip().lower() for n in numbers if n and n.strip())
        result = [s for s in result if s.SheetNumber.lower() in wanted]
    if number_prefix:
        prefixes = tuple(p.lower() for p in
                         ([number_prefix] if isinstance(number_prefix, string_types)
                          else number_prefix))
        result = [s for s in result if s.SheetNumber.lower().startswith(prefixes)]
    if name_contains:
        needle = name_contains.lower()
        result = [s for s in result if needle in (s.Name or "").lower()]
    if parameter_equals:
        for param_name, expected in parameter_equals.items():
            result = [s for s in result
                      if (parameter_value(s, param_name) or "") == expected]
    return result


def parameter_value(element, name):
    """Textova hodnota parametra prvku, alebo None ak parameter neexistuje."""
    parameter = element.LookupParameter(name)
    if parameter is None:
        return None
    return parameter_as_text(parameter)


def parameter_as_text(parameter):
    """Prevod hodnoty parametra na text vhodny do nazvu suboru."""
    DB = db()
    if not parameter.HasValue:
        return ""
    storage = parameter.StorageType
    if storage == DB.StorageType.String:
        return parameter.AsString() or ""
    if storage == DB.StorageType.Integer:
        # Yes/No parametre exportujeme citatelne, nie ako 0/1.
        text = parameter.AsValueString()
        return text if text else str(parameter.AsInteger())
    if storage == DB.StorageType.Double:
        return parameter.AsValueString() or ""
    if storage == DB.StorageType.ElementId:
        element_id = parameter.AsElementId()
        if element_id_value(element_id) < 0:
            return ""
        target = parameter.Element.Document.GetElement(element_id)
        return getattr(target, "Name", "") if target else ""
    return ""


def current_revision(doc, sheet):
    """(cislo, datum, popis) aktualnej revizie vykresu; prazdne ak ziadna nie je."""
    revision_id = sheet.GetCurrentRevision()
    if revision_id is None or element_id_value(revision_id) < 0:
        return "", "", ""
    revision = doc.GetElement(revision_id)
    if revision is None:
        return "", "", ""
    return (sheet.GetRevisionNumberOnSheet(revision_id) or "",
            revision.RevisionDate or "",
            revision.Description or "")


def make_resolver(doc, sheet):
    """Vrati funkciu nazov_tokenu -> hodnota pre `naming.render`.

    Poradie hladania: specialne tokeny -> parametre vykresu ->
    parametre projektu (Project Information).
    """
    now = datetime.datetime.now()
    revision_number, revision_date, revision_description = current_revision(doc, sheet)
    model_path = doc.PathName or ""
    # Cesta z Revitu je vzdy vo Windows tvare; delime na oboch oddelovacoch,
    # aby sa modul spraval rovnako aj mimo Windows (testy, CI).
    model_name = os.path.splitext(model_path.replace("\\", "/").split("/")[-1])[0]

    specials = {
        "sheet number": sheet.SheetNumber,
        "sheet name": sheet.Name,
        "current revision": revision_number,
        "current revision date": revision_date,
        "current revision description": revision_description,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H%M"),
        "yyyy": now.strftime("%Y"),
        "yyyymmdd": now.strftime("%Y%m%d"),
        "file name": model_name,
    }

    project_info = doc.ProjectInformation

    def resolve(name):
        value = specials.get(name.strip().lower())
        if value is not None:
            return value
        value = parameter_value(sheet, name)
        if value:
            return value
        if project_info is not None:
            value = parameter_value(project_info, name)
            if value:
                return value
        return None

    return resolve


# Tokeny, ktore vie `make_resolver` vyhodnotit bez toho, aby existovali
# ako parameter v modeli.
BUILTIN_TOKENS = (
    "Sheet Number",
    "Sheet Name",
    "Current Revision",
    "Current Revision Date",
    "Current Revision Description",
    "File Name",
    "Date",
    "Time",
    "yyyy",
    "yyyymmdd",
)


def _parameter_names(element):
    if element is None:
        return []
    names = set()
    for parameter in element.Parameters:
        try:
            definition = parameter.Definition
        except Exception:
            continue
        if definition is not None and definition.Name:
            names.add(definition.Name)
    return sorted(names)


def available_parameters(doc, sheet):
    """Co sa da pouzit v nazve suboru.

    Vracia (vstavane tokeny, parametre vykresu, parametre projektu).
    Parametre, ktore uz pokryva vstavany token, sa zo zoznamov vypustia,
    aby si pouzivatel nevyberal to iste dvakrat.
    """
    builtin_lower = set(name.lower() for name in BUILTIN_TOKENS)
    sheet_params = [name for name in _parameter_names(sheet)
                    if name.lower() not in builtin_lower]
    seen = builtin_lower | set(name.lower() for name in sheet_params)
    project_params = [name for name in _parameter_names(doc.ProjectInformation)
                      if name.lower() not in seen]
    return list(BUILTIN_TOKENS), sheet_params, project_params
