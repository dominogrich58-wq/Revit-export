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
