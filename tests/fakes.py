# -*- coding: utf-8 -*-
"""Nahrady Revit objektov, aby sa logika dala testovat mimo Revitu."""


class FakeElementId(object):
    def __init__(self, value):
        self.Value = value
        self.IntegerValue = value


class FakeApplication(object):
    def __init__(self, version="2024"):
        self.VersionNumber = version


class FakeDocument(object):
    def __init__(self, version="2024", path=r"C:\projekty\Bytovka.rvt",
                 project_info=None):
        self.Application = FakeApplication(version)
        self.PathName = path
        self.ProjectInformation = project_info

    def GetElement(self, element_id):
        return None


class FakeSheet(object):
    def __init__(self, number, name, parameters=None):
        self.SheetNumber = number
        self.Name = name
        self.IsPlaceholder = False
        self.Id = FakeElementId(abs(hash(number)) % 100000)
        self._parameters = parameters or {}

    def LookupParameter(self, name):
        return self._parameters.get(name)

    def GetCurrentRevision(self):
        return FakeElementId(-1)


class FakeDwgOptions(object):
    """Nahrada za DB.DWGExportOptions."""

    def __init__(self, source="default"):
        self.source = source
        self.MergedViews = False
        self.SharedCoords = False
        self.FileVersion = None


class FakeDwgSettings(object):
    """Nahrada za element DB.ExportDWGSettings."""

    def __init__(self, name):
        self.Name = name

    def GetDWGExportOptions(self):
        return FakeDwgOptions("element:" + self.Name)


class FakeCollector(object):
    def __init__(self, elements):
        self._elements = elements

    def OfClass(self, _cls):
        return list(self._elements)


class FakeAcadVersion(object):
    R2018 = "R2018"
    R2013 = "R2013"


class FakeDb(object):
    """Minimalna nahrada modulu Autodesk.Revit.DB pre testy DWG nastaveni.

    `with_static_getter=False` simuluje verziu Revitu, ktora staticku metodu
    DWGExportOptions.GetPredefinedOptions nema.
    """

    ACADVersion = FakeAcadVersion

    def __init__(self, settings_names=(), with_static_getter=True):
        self.ExportDWGSettings = FakeDwgSettings
        self._settings = [FakeDwgSettings(name) for name in settings_names]

        class DWGExportOptions(FakeDwgOptions):
            pass

        if with_static_getter:
            known = set(settings_names)

            def get_predefined_options(_doc, name):
                return FakeDwgOptions("static:" + name) if name in known else None

            DWGExportOptions.GetPredefinedOptions = staticmethod(get_predefined_options)

        self.DWGExportOptions = DWGExportOptions

    def FilteredElementCollector(self, _doc):
        return FakeCollector(self._settings)
