# -*- coding: utf-8 -*-
"""Generator Dynamo grafov (.dyn) pre ProSheets Lite.

Grafy sa generuju z Python skriptov v `dynamo/python/`, aby kod existoval
len na jednom mieste - v .dyn subore je totiz Python vlozeny ako JSON retazec
a rucna uprava je nepohodlna a nachylna na chyby.

Spustenie:  python3 tools/build_dyn.py
Cielova schema: Dynamo 2.x (Revit 2021+). Engine Python nodov: CPython3.
"""

import io
import json
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_DIR = os.path.join(ROOT, "dynamo", "python")
OUT_DIR = os.path.join(ROOT, "dynamo")

NAMESPACE = uuid.UUID("6f1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8")


def guid(name):
    """Stabilny identifikator - opakovany build da rovnaky .dyn subor."""
    return uuid.uuid5(NAMESPACE, name).hex


def _port(owner, kind, index, name, description="", default=False):
    return {
        "Id": guid("%s:%s:%d" % (owner, kind, index)),
        "Name": name,
        "Description": description,
        "UsingDefaultValue": default,
        "Level": 2,
        "UseLevels": False,
        "KeepListStructure": False,
    }


def _node(node_id, concrete_type, node_type, inputs, outputs, extra):
    node = {
        "Id": node_id,
        "NodeType": node_type,
        "ConcreteType": concrete_type,
        "Inputs": inputs,
        "Outputs": outputs,
        "Replication": "Disabled",
        "Description": "",
    }
    node.update(extra)
    return node


def string_input(name, value, description=""):
    node_id = guid(name)
    return _node(node_id,
                 "CoreNodeModels.Input.StringInput, CoreNodeModels",
                 "StringInputNode",
                 [],
                 [_port(node_id, "out", 0, "")],
                 {"InputValue": value, "NodeValue": value,
                  "Description": description or "Textovy vstup"})


def bool_input(name, value, description=""):
    node_id = guid(name)
    return _node(node_id,
                 "CoreNodeModels.Input.BoolSelector, CoreNodeModels",
                 "BooleanInputNode",
                 [],
                 [_port(node_id, "out", 0, "")],
                 {"InputValue": bool(value), "NodeValue": str(bool(value)).lower(),
                  "Description": description or "Prepinac True/False"})


def code_block(name, code):
    node_id = guid(name)
    return _node(node_id,
                 "Dynamo.Graph.Nodes.CodeBlockNodeModel, DynamoCore",
                 "CodeBlockNode",
                 [],
                 [_port(node_id, "out", 0, "")],
                 {"Code": code, "Description": "Code block"})


def python_node(name, code, port_names):
    node_id = guid(name)
    inputs = [_port(node_id, "in", i, "IN[%d]" % i, port_names[i])
              for i in range(len(port_names))]
    return _node(node_id,
                 "PythonNodeModels.PythonNode, PythonNodeModels",
                 "PythonScriptNode",
                 inputs,
                 [_port(node_id, "out", 0, "OUT")],
                 {"Code": code, "Engine": "CPython3",
                  "EngineName": "CPython3",
                  "VariableInputPorts": True,
                  "Description": "Python skript ProSheets Lite"})


def watch_node(name):
    node_id = guid(name)
    return _node(node_id,
                 "CoreNodeModels.Watch, CoreNodeModels",
                 "ExtensionNode",
                 [_port(node_id, "in", 0, "")],
                 [_port(node_id, "out", 0, "")],
                 {"WatchWidth": 460.0, "WatchHeight": 260.0,
                  "Description": "Vypis vysledku"})


def connect(source, target_node, target_index):
    return {
        "Start": source["Outputs"][0]["Id"],
        "End": target_node["Inputs"][target_index]["Id"],
        "Id": guid("conn:%s:%s:%d" % (source["Id"], target_node["Id"], target_index)),
        "IsHidden": "False",
    }


def node_view(node, x, y, name):
    return {
        "Id": node["Id"],
        "Name": name,
        "IsSetAsInput": node["NodeType"] in ("StringInputNode", "BooleanInputNode"),
        "IsSetAsOutput": False,
        "Excluded": False,
        "ShowGeometry": True,
        "X": float(x),
        "Y": float(y),
    }


def graph(name, description, nodes, connectors, views):
    return {
        "Uuid": str(uuid.uuid5(NAMESPACE, "graph:" + name)),
        "IsCustomNode": False,
        "Description": description,
        "Name": name,
        "ElementResolver": {"ResolutionMap": {}},
        "Inputs": [],
        "Outputs": [],
        "Nodes": nodes,
        "Connectors": connectors,
        "Dependencies": [],
        "NodeLibraryDependencies": [],
        "Author": "ProSheets Lite",
        "Bindings": [],
        "View": {
            "Dynamo": {
                "ScaleFactor": 1.0,
                "HasRunWithoutCrash": True,
                "IsVisibleInDynamoLibrary": True,
                "Version": "2.13.1.3887",
                "RunType": "Manual",
                "RunPeriod": "1000",
            },
            "Camera": {"Name": "_Background Preview", "EyeX": -17.0, "EyeY": 24.0,
                       "EyeZ": 50.0, "LookX": 12.0, "LookY": -13.0, "LookZ": -58.0,
                       "UpX": 0.0, "UpY": 1.0, "UpZ": 0.0},
            "ConnectorPins": [],
            "NodeViews": views,
            "Annotations": [],
            "X": 0.0,
            "Y": 0.0,
            "Zoom": 0.75,
        },
    }


def read_script(file_name):
    with io.open(os.path.join(PY_DIR, file_name), "r", encoding="utf-8") as handle:
        return handle.read()


def build_export_graph():
    prefix = "export"
    run = bool_input(prefix + ".run", False, "Run - spustenie exportu")
    lib = string_input(prefix + ".lib", r"C:\ProSheetsLite\lib",
                       "Adresar s balikom prosheets")
    sheets = code_block(prefix + ".sheets", "[];")
    folder = string_input(prefix + ".folder", r"C:\Export",
                          "Vystupny adresar")
    formats = code_block(prefix + ".formats", '["PDF","DWG"];')
    template = string_input(prefix + ".template", "{Sheet Number} - {Sheet Name}",
                            "Sablona nazvu suboru")
    combine = bool_input(prefix + ".combine", False, "Spojit PDF do jedneho suboru")
    setup = string_input(prefix + ".dwgsetup", "", "Nazov DWG Export Setupu")

    script = python_node(prefix + ".script", read_script("export_node.py"),
                         ["Run", "LibPath", "Sheets", "OutputFolder", "Formats",
                          "FileNameTemplate", "CombinePDF", "DWGExportSetup"])
    watch = watch_node(prefix + ".watch")

    sources = [run, lib, sheets, folder, formats, template, combine, setup]
    connectors = [connect(source, script, index)
                  for index, source in enumerate(sources)]
    connectors.append(connect(script, watch, 0))

    labels = ["Run", "LibPath", "Sheets (volitelne)", "OutputFolder", "Formats",
              "FileNameTemplate", "CombinePDF", "DWGExportSetup"]
    views = [node_view(node, 0, index * 110, label)
             for index, (node, label) in enumerate(zip(sources, labels))]
    views.append(node_view(script, 560, 240, "ProSheets Lite - Export"))
    views.append(node_view(watch, 940, 240, "Vysledok"))

    return graph("ProSheets Lite - Export",
                 "Davkovy export Revit vykresov do PDF a DWG.",
                 sources + [script, watch], connectors, views)


def build_list_graph():
    prefix = "list"
    lib = string_input(prefix + ".lib", r"C:\ProSheetsLite\lib",
                       "Adresar s balikom prosheets")
    sheet_set = string_input(prefix + ".set", "", "Nazov Sheet Setu (volitelne)")
    script = python_node(prefix + ".script", read_script("list_sheets_node.py"),
                         ["LibPath", "SheetSet"])
    watch = watch_node(prefix + ".watch")

    sources = [lib, sheet_set]
    connectors = [connect(source, script, index)
                  for index, source in enumerate(sources)]
    connectors.append(connect(script, watch, 0))

    views = [node_view(lib, 0, 0, "LibPath"),
             node_view(sheet_set, 0, 110, "SheetSet"),
             node_view(script, 480, 40, "ProSheets Lite - Zoznam vykresov"),
             node_view(watch, 860, 40, "Vykresy / Sheet Sety / DWG setupy")]

    return graph("ProSheets Lite - Zoznam vykresov",
                 "Vypise vykresy, Sheet Sety a DWG Export Setupy v modeli.",
                 sources + [script, watch], connectors, views)


def write(graph_data, file_name):
    path = os.path.join(OUT_DIR, file_name)
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(graph_data, indent=2, ensure_ascii=False))
        handle.write(u"\n")
    return path


def main():
    for builder, file_name in ((build_export_graph, "ProSheets Lite - Export.dyn"),
                               (build_list_graph, "ProSheets Lite - Zoznam vykresov.dyn")):
        print("zapisane: %s" % write(builder(), file_name))


if __name__ == "__main__":
    main()
