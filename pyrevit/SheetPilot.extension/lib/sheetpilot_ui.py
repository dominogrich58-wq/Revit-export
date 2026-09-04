# -*- coding: utf-8 -*-
"""WPF rozhranie SheetPilotu - jedno okno namiesto sledu dialogov.

Modul obsahuje len obsluhu okien. Vsetka logika - vyber vykresov, skladanie
nazvov, profily a samotny export - zije v balicku `sheetpilot`, ktory sa da
testovat bez Revitu. Okna sem len citaju a zapisuju.
"""

import os
import shutil

from pyrevit import forms

from System.Windows import Visibility, WindowStartupLocation
from System.Windows.Controls import (Button, ComboBox, Grid, ColumnDefinition,
                                     TextBox)
from System.Windows import GridLength, GridUnitType, Thickness
from System.Windows.Media import Brushes, FontFamily
from System.Windows.Threading import (Dispatcher, DispatcherFrame,
                                      DispatcherOperationCallback,
                                      DispatcherPriority)

from sheetpilot import config as sp_config
from sheetpilot import naming, profiles, runner
from sheetpilot import sheets as sheets_mod
from sheetpilot.exporters import dwg as dwg_exporter
from sheetpilot.report import FAILED, OK, SKIPPED

HERE = os.path.dirname(os.path.abspath(__file__))
BUTTON_DIR = os.path.join(
    os.path.dirname(HERE), "SheetPilot.tab", "Export.panel",
    "ExportSheets.pushbutton")

TEXT_ONLY = "(iba text)"
NO_MODIFIER = "bez úpravy"
SHEET_LABEL = "Výkres: "
PROJECT_LABEL = "Projekt: "
DEFAULT_SETUP = "— predvoľby Revitu —"

MODIFIER_LABELS = [
    (NO_MODIFIER, ""),
    ("VEĽKÉ", "upper"),
    ("malé", "lower"),
    ("Prvé Veľké", "title"),
    ("bez diakritiky", "slug"),
    ("bez medzier", "nospace"),
]

PRESETS = [
    "{Sheet Number} - {Sheet Name}",
    "{Sheet Number}_{Sheet Name}",
    "{Project Number}-{Sheet Number}-{Sheet Name}",
    "{Sheet Number} - {Sheet Name} - R{Current Revision|00}",
    "{yyyymmdd}_{Sheet Number}_{Sheet Name:slug}",
]

QUALITY = ["High", "Presentation", "Medium", "Low"]
COLOR_DEPTH = ["Color", "GrayScale", "BlackLine"]
DWG_VERSIONS = ["AutoCAD2018", "AutoCAD2013", "AutoCAD2010", "AutoCAD2007"]


def pump_events():
    """Prekresli okno pocas dlhej synchronnej operacie.

    Revit API sa smie volat len z hlavneho vlakna, takze export nemozeme
    poslat na pozadie. Namiesto toho medzi vykresmi pustime dispatcher,
    aby sa ukazovatel priebehu posunul a tlacidlo Prerusit reagovalo.
    """
    frame = DispatcherFrame()

    def stop(_arg):
        frame.Continue = False
        return None

    Dispatcher.CurrentDispatcher.BeginInvoke(
        DispatcherPriority.Background, DispatcherOperationCallback(stop), None)
    Dispatcher.PushFrame(frame)


def strip_label(name):
    for label in (SHEET_LABEL, PROJECT_LABEL):
        if name.startswith(label):
            return name[len(label):]
    return name


class SheetItem(object):
    """Riadok v zozname vykresov."""

    def __init__(self, sheet):
        self.sheet = sheet
        self.Number = sheet.SheetNumber
        self.Name = sheet.Name
        self.Size = sheets_mod.sheet_size_label(sheet)
        self.Checked = False
        try:
            self.Revision = sheet.GetRevisionNumberOnSheet(
                sheet.GetCurrentRevision()) or u"—"
        except Exception:
            self.Revision = u"—"


class ChipItem(object):
    def __init__(self, label):
        self.Label = label


class ResultItem(object):
    """Riadok vo vysledku exportu."""

    BRUSHES = {OK: Brushes.SeaGreen, SKIPPED: Brushes.DarkGoldenrod,
               FAILED: Brushes.Firebrick}

    def __init__(self, result):
        self.Status = result.status
        self.Format = result.fmt
        self.Detail = result.path or result.message
        self.StatusBrush = self.BRUSHES.get(result.status, Brushes.Gray)


class NameWindow(forms.WPFWindow):
    """Okno na skladanie nazvu suboru z casti."""

    def __init__(self, doc, sheet, segments, prefix, suffix):
        forms.WPFWindow.__init__(self, os.path.join(BUTTON_DIR, "NameWindow.xaml"))
        self.doc = doc
        self.sheet = sheet
        self.result = None
        self._rows = []
        self._loading = True

        builtin, sheet_params, project_params = ([], [], [])
        if sheet is not None:
            builtin, sheet_params, project_params = \
                sheets_mod.available_parameters(doc, sheet)
        self.params = ([TEXT_ONLY] + list(builtin)
                       + [SHEET_LABEL + n for n in sheet_params]
                       + [PROJECT_LABEL + n for n in project_params])

        self.preset_box.ItemsSource = ["— vyber —"] + PRESETS
        self.preset_box.SelectedIndex = 0
        self.addparam_box.ItemsSource = ["+ pridať parameter…"] + self.params[1:]
        self.addparam_box.SelectedIndex = 0
        self.gprefix_box.Text = prefix or ""
        self.gsuffix_box.Text = suffix or ""

        for segment in segments:
            self._add_row(segment)
        self._loading = False
        self.refresh()

    # --- riadky ---------------------------------------------------------

    def _add_row(self, segment):
        widths = [(1, GridUnitType.Star), (110, GridUnitType.Pixel),
                  (110, GridUnitType.Pixel), (110, GridUnitType.Pixel),
                  (130, GridUnitType.Pixel), (106, GridUnitType.Pixel)]
        grid = Grid()
        grid.Margin = Thickness(0, 0, 0, 3)
        for value, unit in widths:
            column = ColumnDefinition()
            column.Width = GridLength(value, unit)
            grid.ColumnDefinitions.Add(column)

        parameter = ComboBox()
        parameter.ItemsSource = self.params
        name = segment.get("parameter") or ""
        parameter.SelectedItem = self._label_for(name) if name else TEXT_ONLY
        parameter.SelectionChanged += self.on_changed
        parameter.Margin = Thickness(0, 0, 4, 0)

        boxes = []
        for key in ("prefix", "suffix", "fallback"):
            box = TextBox()
            box.Text = segment.get(key) or ""
            box.FontFamily = FontFamily("Consolas")
            box.TextChanged += self.on_changed
            box.Margin = Thickness(0, 0, 4, 0)
            boxes.append(box)

        modifier = ComboBox()
        modifier.ItemsSource = [label for label, _ in MODIFIER_LABELS]
        current = segment.get("modifier") or ""
        modifier.SelectedIndex = next(
            (i for i, pair in enumerate(MODIFIER_LABELS) if pair[1] == current), 0)
        modifier.SelectionChanged += self.on_changed
        modifier.Margin = Thickness(0, 0, 4, 0)

        actions = Grid()
        for index, (text, handler) in enumerate(
                (("↑", self.on_up), ("↓", self.on_down), ("✕", self.on_remove))):
            column = ColumnDefinition()
            column.Width = GridLength(1, GridUnitType.Star)
            actions.ColumnDefinitions.Add(column)
            button = Button()
            button.Content = text
            button.Margin = Thickness(0, 0, 3, 0)
            button.Tag = grid
            button.Click += handler
            Grid.SetColumn(button, index)
            actions.Children.Add(button)

        for index, control in enumerate([parameter] + boxes + [modifier, actions]):
            Grid.SetColumn(control, index)
            grid.Children.Add(control)

        self.rows_panel.Children.Add(grid)
        self._rows.append({"grid": grid, "param": parameter, "pre": boxes[0],
                           "suf": boxes[1], "fb": boxes[2], "mod": modifier})

    def _label_for(self, name):
        for candidate in self.params:
            if strip_label(candidate) == name:
                return candidate
        return name

    def _index_of(self, grid):
        for index, row in enumerate(self._rows):
            if row["grid"] is grid:
                return index
        return -1

    def _rebuild(self, segments):
        self.rows_panel.Children.Clear()
        self._rows = []
        self._loading = True
        for segment in segments:
            self._add_row(segment)
        self._loading = False
        self.refresh()

    # --- data -----------------------------------------------------------

    def collect(self):
        segments = []
        for row in self._rows:
            selected = row["param"].SelectedItem or TEXT_ONLY
            modifier = MODIFIER_LABELS[max(0, row["mod"].SelectedIndex)][1]
            segments.append({
                "parameter": "" if selected == TEXT_ONLY else strip_label(selected),
                "prefix": row["pre"].Text,
                "suffix": row["suf"].Text,
                "fallback": row["fb"].Text,
                "modifier": modifier,
            })
        return segments

    def template(self):
        return naming.build_template(self.collect(), self.gprefix_box.Text,
                                     self.gsuffix_box.Text)

    def refresh(self):
        if self._loading:
            return
        template = self.template()
        self.template_label.Text = template or "(prázdna)"
        if self.sheet is not None and template:
            resolver = sheets_mod.make_resolver(self.doc, self.sheet)
            self.preview_label.Text = naming.render(template, resolver)
        else:
            self.preview_label.Text = "(nie je z čoho urobiť ukážku)"

        count = len(self._rows)
        self.count_label.Text = u"%d %s" % (
            count, u"časť" if count == 1 else (u"časti" if count < 5 else u"častí"))
        self.warn_label.Text = "" if template else \
            u"Názov je prázdny — pridaj aspoň jednu časť."

    # --- obsluha --------------------------------------------------------

    def on_changed(self, sender, args):
        self.refresh()

    def on_add_param(self, sender, args):
        if self._loading or self.addparam_box.SelectedIndex <= 0:
            return
        name = strip_label(self.addparam_box.SelectedItem)
        self._loading = True
        self._add_row({"parameter": name,
                       "prefix": " - " if self._rows else ""})
        self.addparam_box.SelectedIndex = 0
        self._loading = False
        self.refresh()

    def on_add_text(self, sender, args):
        self._loading = True
        self._add_row({"parameter": "", "suffix": "_text"})
        self._loading = False
        self.refresh()

    def on_preset(self, sender, args):
        if self._loading or self.preset_box.SelectedIndex <= 0:
            return
        template = self.preset_box.SelectedItem
        self.gprefix_box.Text = ""
        self.gsuffix_box.Text = ""
        self._rebuild(naming.segments_from_template(template))
        self.preset_box.SelectedIndex = 0

    def _move(self, sender, offset):
        index = self._index_of(sender.Tag)
        target = index + offset
        if index < 0 or target < 0 or target >= len(self._rows):
            return
        segments = self.collect()
        segments.insert(target, segments.pop(index))
        self._rebuild(segments)

    def on_up(self, sender, args):
        self._move(sender, -1)

    def on_down(self, sender, args):
        self._move(sender, 1)

    def on_remove(self, sender, args):
        index = self._index_of(sender.Tag)
        if index < 0:
            return
        segments = self.collect()
        del segments[index]
        self._rebuild(segments)

    def on_ok(self, sender, args):
        self.result = {
            "file_name_segments": self.collect(),
            "file_name_prefix": self.gprefix_box.Text,
            "file_name_suffix": self.gsuffix_box.Text,
            "file_name_template": naming.build_template(self.collect()),
        }
        self.Close()

    def on_cancel(self, sender, args):
        self.result = None
        self.Close()


class ExportWindow(forms.WPFWindow):
    """Hlavne okno exportu."""

    def __init__(self, doc, store):
        forms.WPFWindow.__init__(self, os.path.join(BUTTON_DIR, "ExportWindow.xaml"))
        self.doc = doc
        self.store = store
        self.cancelled = False
        self._loading = True

        self.model_label.Text = os.path.basename(doc.PathName or "") or "(neuložený model)"
        self.version_label.Text = "Revit %s" % doc.Application.VersionNumber

        self.all_items = [SheetItem(s) for s in sheets_mod.all_sheets(doc)]
        self.sheet_sets = sheets_mod.sheet_sets(doc)
        self._set_cache = {}
        self.sheetset_box.ItemsSource = [u"— všetky výkresy —"] + self.sheet_sets
        self.sheetset_box.SelectedIndex = 0

        self.quality_box.ItemsSource = QUALITY
        self.color_box.ItemsSource = COLOR_DEPTH
        self.dwgversion_box.ItemsSource = DWG_VERSIONS
        self.dwg_setups = dwg_exporter.export_setups(doc)
        self.dwgsetup_box.ItemsSource = [DEFAULT_SETUP] + self.dwg_setups

        self.config = self.store.active()
        self._restore_geometry()
        self._fill_profiles()
        self._apply_config(self.config)
        self._loading = False
        self.refresh()

    # --- profily --------------------------------------------------------

    def _fill_profiles(self):
        names = self.store.names()
        self.profile_box.ItemsSource = names or [u"(žiadny profil)"]
        active = self.store.active_name()
        self.profile_box.SelectedIndex = names.index(active) if active in names else 0

    def _apply_config(self, config):
        self.config = config
        formats = config.get("formats") or []
        self.pdf_check.IsChecked = "PDF" in formats
        self.dwg_check.IsChecked = "DWG" in formats

        pdf = config.get("pdf") or {}
        self.combine_check.IsChecked = bool(pdf.get("combine"))
        self._select(self.quality_box, pdf.get("raster_quality"), QUALITY[0])
        self._select(self.color_box, pdf.get("color_depth"), COLOR_DEPTH[0])

        dwg = config.get("dwg") or {}
        self.noxref_check.IsChecked = not dwg.get("external_references")
        setup = dwg.get("export_setup") or ""
        self.dwgsetup_box.SelectedItem = setup if setup in self.dwg_setups else DEFAULT_SETUP
        self._select(self.dwgversion_box, dwg.get("file_version"), DWG_VERSIONS[0])

        self.folder_box.Text = config.get("output_folder") or ""
        self.subfolder_check.IsChecked = bool(config.get("subfolder_per_format"))
        self.overwrite_check.IsChecked = bool(config.get("overwrite"))

        wanted = set(config.get("sheet_selection", {}).get("numbers") or [])
        for item in self.all_items:
            item.Checked = item.Number in wanted
        self._show_sheets()

    def _select(self, combo, value, default):
        combo.SelectedItem = value if value in combo.ItemsSource else default

    def collect_config(self):
        """Zlozi nastavenia z okna. Vracia neznormalizovany slovnik."""
        formats = []
        if self.pdf_check.IsChecked:
            formats.append("PDF")
        if self.dwg_check.IsChecked:
            formats.append("DWG")

        setup = self.dwgsetup_box.SelectedItem or DEFAULT_SETUP
        config = dict(self.config)
        config.update({
            "output_folder": self.folder_box.Text,
            "formats": formats,
            "subfolder_per_format": bool(self.subfolder_check.IsChecked),
            "overwrite": bool(self.overwrite_check.IsChecked),
            "sheet_selection": {"mode": "numbers",
                                "numbers": [i.Number for i in self.all_items
                                            if i.Checked]},
        })
        config["pdf"] = dict(config.get("pdf") or {}, **{
            "combine": bool(self.combine_check.IsChecked),
            "raster_quality": self.quality_box.SelectedItem or QUALITY[0],
            "color_depth": self.color_box.SelectedItem or COLOR_DEPTH[0],
        })
        config["dwg"] = dict(config.get("dwg") or {}, **{
            "external_references": not bool(self.noxref_check.IsChecked),
            "export_setup": "" if setup == DEFAULT_SETUP else setup,
            "file_version": self.dwgversion_box.SelectedItem or DWG_VERSIONS[0],
        })
        return config

    # --- zoznam vykresov ------------------------------------------------

    def visible_items(self):
        needle = (self.filter_box.Text or "").lower()
        set_index = self.sheetset_box.SelectedIndex
        allowed = None
        if set_index > 0:
            name = self.sheet_sets[set_index - 1]
            if name not in self._set_cache:
                self._set_cache[name] = set(
                    s.SheetNumber for s in sheets_mod.sheets_from_set(self.doc, name))
            allowed = self._set_cache[name]

        items = []
        for item in self.all_items:
            if allowed is not None and item.Number not in allowed:
                continue
            haystack = u"%s %s %s" % (item.Number, item.Name, item.Size)
            if needle and needle not in haystack.lower():
                continue
            items.append(item)
        return items

    def _show_sheets(self):
        self.sheet_list.ItemsSource = self.visible_items()

    def checked_items(self):
        return [i for i in self.all_items if i.Checked]

    # --- prekreslenie ---------------------------------------------------

    def refresh(self):
        if self._loading:
            return
        chosen = self.checked_items()
        self.sheet_count.Text = u"%d z %d" % (len(chosen), len(self.all_items))

        segments = self.config.get("file_name_segments") or \
            naming.segments_from_template(self.config.get("file_name_template") or "")
        chips = []
        prefix = self.config.get("file_name_prefix") or ""
        suffix = self.config.get("file_name_suffix") or ""
        if prefix:
            chips.append(ChipItem(u"'%s'" % prefix))
        chips.extend(ChipItem(naming.describe_segment(s)) for s in segments)
        if suffix:
            chips.append(ChipItem(u"'%s'" % suffix))
        self.chip_list.ItemsSource = chips or [ChipItem(u"(názov nie je nastavený)")]

        template = sp_config.effective_template(self.config)
        if chosen and template:
            resolver = sheets_mod.make_resolver(self.doc, chosen[0].sheet)
            self.preview_label.Text = naming.render(template, resolver)
        else:
            self.preview_label.Text = u"(nie je vybraný žiadny výkres)"

        self.pdf_panel.Visibility = (Visibility.Visible if self.pdf_check.IsChecked
                                     else Visibility.Collapsed)
        self.dwg_panel.Visibility = (Visibility.Visible if self.dwg_check.IsChecked
                                     else Visibility.Collapsed)

        formats = (1 if self.pdf_check.IsChecked else 0) + \
                  (1 if self.dwg_check.IsChecked else 0)
        self.export_button.IsEnabled = bool(chosen) and bool(formats)
        if not chosen:
            self.status_label.Text = u"Nie je vybraný žiadny výkres."
        elif not formats:
            self.status_label.Text = u"Nie je zvolený formát."
        else:
            self.status_label.Text = u"%d vykresov, %s" % (
                len(chosen),
                u"spojené PDF" if (self.combine_check.IsChecked
                                   and self.pdf_check.IsChecked)
                else u"samostatné súbory")

    def show_stage(self, stage):
        self.form_view.Visibility = (Visibility.Visible if stage == "form"
                                     else Visibility.Collapsed)
        self.progress_view.Visibility = (Visibility.Visible if stage == "progress"
                                         else Visibility.Collapsed)
        self.result_view.Visibility = (Visibility.Visible if stage == "result"
                                       else Visibility.Collapsed)

    # --- obsluha formulara ----------------------------------------------

    def on_sheet_toggled(self, sender, args):
        item = sender.DataContext
        if item is not None:
            item.Checked = bool(sender.IsChecked)
        self.refresh()

    def on_filter_changed(self, sender, args):
        if not self._loading:
            self._show_sheets()

    def on_sheetset_changed(self, sender, args):
        if not self._loading:
            self._show_sheets()

    def _set_all(self, items, value):
        for item in items:
            item.Checked = value
        self._show_sheets()
        self.refresh()

    def on_select_all(self, sender, args):
        self._set_all(self.all_items, True)

    def on_select_none(self, sender, args):
        self._set_all(self.all_items, False)

    def on_select_invert(self, sender, args):
        for item in self.all_items:
            item.Checked = not item.Checked
        self._show_sheets()
        self.refresh()

    def on_select_visible(self, sender, args):
        self._set_all(self.visible_items(), True)

    def on_format_changed(self, sender, args):
        self.refresh()

    def on_setting_changed(self, sender, args):
        self.refresh()

    def on_edit_name(self, sender, args):
        chosen = self.checked_items()
        sheet = chosen[0].sheet if chosen else (
            self.all_items[0].sheet if self.all_items else None)
        segments = self.config.get("file_name_segments") or \
            naming.segments_from_template(self.config.get("file_name_template") or "")

        dialog = NameWindow(self.doc, sheet, segments,
                            self.config.get("file_name_prefix") or "",
                            self.config.get("file_name_suffix") or "")
        dialog.ShowDialog()
        if dialog.result:
            self.config.update(dialog.result)
            self.refresh()

    def on_pick_folder(self, sender, args):
        folder = forms.pick_folder(title=u"Výstupný adresár")
        if folder:
            self.folder_box.Text = folder

    def on_close(self, sender, args):
        self.Close()

    # --- profily --------------------------------------------------------

    def on_profile_changed(self, sender, args):
        if self._loading:
            return
        name = self.profile_box.SelectedItem
        if not name or name not in self.store.names():
            return
        try:
            self._loading = True
            self.store.set_active(name)
            self._apply_config(self.store.load(name))
        except Exception as exc:
            forms.alert(u"Profil sa nedá načítať:\n%s" % exc, title="SheetPilot")
        finally:
            self._loading = False
            self.refresh()

    def _save_as(self, name):
        try:
            normalized = sp_config.normalize(self.collect_config())
        except sp_config.ConfigError as exc:
            forms.alert(u"%s" % exc, title=u"Nastavenia ešte nie sú úplné")
            return None
        effective = self.store.save(name, normalized)
        self.store.set_active(effective)
        self._loading = True
        self._fill_profiles()
        self._loading = False
        return effective

    def on_profile_save(self, sender, args):
        name = self.store.active_name()
        if not name:
            self.on_profile_save_as(sender, args)
            return
        if self._save_as(name):
            forms.alert(u"Profil '%s' uložený." % name, title="SheetPilot")

    def on_profile_save_as(self, sender, args):
        name = forms.ask_for_string(default=profiles.DEFAULT_NAME,
                                    title=u"Uložiť profil ako",
                                    prompt=u"Názov profilu:")
        if name and self._save_as(name):
            forms.alert(u"Profil '%s' uložený." % name, title="SheetPilot")

    def on_profile_delete(self, sender, args):
        name = self.store.active_name()
        if not name:
            forms.alert(u"Nie je zvolený žiadny profil.", title="SheetPilot")
            return
        if not forms.alert(u"Naozaj zmazať profil '%s'?" % name,
                           title="SheetPilot", yes=True, no=True):
            return
        self.store.delete(name)
        self._loading = True
        self._fill_profiles()
        self._loading = False

    def on_profile_import(self, sender, args):
        source = forms.pick_file(file_ext="json", title=u"Vyber súbor s profilom")
        if not source:
            return
        try:
            data = sp_config.load(source)
        except Exception as exc:
            forms.alert(u"Súbor nie je platný profil:\n%s" % exc, title="SheetPilot")
            return
        name = forms.ask_for_string(
            default=os.path.splitext(os.path.basename(source))[0],
            title=u"Načítaný profil uložiť ako", prompt=u"Názov profilu:")
        if not name:
            return
        effective = self.store.save(name, data)
        self.store.set_active(effective)
        self._loading = True
        self._fill_profiles()
        self._apply_config(self.store.load(effective))
        self._loading = False
        self.refresh()

    def on_profile_export(self, sender, args):
        name = self.store.active_name()
        if not name:
            forms.alert(u"Najprv profil ulož.", title="SheetPilot")
            return
        target = forms.save_file(file_ext="json", default_name=name)
        if target:
            shutil.copyfile(self.store.path_for(name), target)
            forms.alert(u"Profil uložený do:\n%s" % target, title="SheetPilot")

    # --- export ---------------------------------------------------------

    def on_export(self, sender, args):
        try:
            normalized = sp_config.normalize(self.collect_config())
        except sp_config.ConfigError as exc:
            forms.alert(u"%s" % exc, title=u"Chybné nastavenia")
            return

        self.cancelled = False
        self.progress_bar.Value = 0
        self.progress_text.Text = u"Pripravujem…"
        self.progress_count.Text = ""
        self.show_stage("progress")
        pump_events()

        def progress(done, total, text):
            if self.cancelled:
                return False
            self.progress_bar.Value = 100.0 * done / max(1, total)
            self.progress_text.Text = text
            self.progress_count.Text = u"%d z %d" % (done, total)
            pump_events()
            return True

        report = runner.run(self.doc, normalized, progress)

        try:
            log_path = report.write_csv(normalized["output_folder"])
        except Exception as exc:
            log_path = u"log sa nepodarilo uložiť: %s" % exc

        name = self.store.active_name()
        if name:
            self.store.save(name, normalized)

        self.output_folder = normalized["output_folder"]
        self._show_result(report, log_path)

        if self.openafter_check.IsChecked and not report.has_failures():
            self.on_open_folder(None, None)

    def _show_result(self, report, log_path):
        self.result_head.Text = u"HOTOVO"
        self.result_summary.Text = u"%d OK    %d preskočených    %d chýb    %.1f s" % (
            report.count(OK), report.count(SKIPPED), report.count(FAILED),
            report.elapsed)
        self.result_list.ItemsSource = [ResultItem(r) for r in report.results]
        self.result_note.Text = (
            u"Časť výkresov sa nevyexportovala — dôvod je v stĺpci vpravo a v CSV logu."
            if report.has_failures() else u"Všetky výkresy prešli.")
        self.result_note.Foreground = (Brushes.Firebrick if report.has_failures()
                                       else Brushes.SeaGreen)
        self.result_log.Text = u"Log: %s" % log_path
        self.show_stage("result")

    def on_cancel_run(self, sender, args):
        self.cancelled = True

    def on_back(self, sender, args):
        self.show_stage("form")
        self.refresh()

    def on_open_folder(self, sender, args):
        folder = getattr(self, "output_folder", None) or self.folder_box.Text
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    # --- poloha okna ----------------------------------------------------

    def _restore_geometry(self):
        saved = self.store.get_ui_state("window")
        if not saved:
            return
        try:
            self.Width = max(self.MinWidth, float(saved["w"]))
            self.Height = max(self.MinHeight, float(saved["h"]))
            self.Left = float(saved["x"])
            self.Top = float(saved["y"])
            self.WindowStartupLocation = WindowStartupLocation.Manual
        except Exception:
            # Ulozena poloha moze ukazovat na monitor, ktory uz nie je
            # pripojeny - vtedy nechame okno tam, kam ho da Windows.
            pass

    def window_closing(self, sender, args):
        try:
            self.store.set_ui_state("window", {"w": self.Width, "h": self.Height,
                                               "x": self.Left, "y": self.Top})
        except Exception:
            pass
