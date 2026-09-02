# -*- coding: utf-8 -*-
"""Drobne rozdiely medzi IronPython 2.7 (pyRevit, Dynamo) a CPython 3."""

try:                              # IronPython 2.7
    string_types = (str, unicode)      # noqa: F821
    text_type = unicode                # noqa: F821
except NameError:                 # CPython 3
    string_types = (str,)
    text_type = str
