# -*- coding: utf-8 -*-
"""Zopakovanie posledneho exportu bez dialogov."""

__title__ = "Opakuj\nposledny"
__doc__ = "Spusti posledny ulozeny profil exportu na aktualnom modeli."

import os

from pyrevit import forms, revit, script

import prosheets_setup
prosheets_setup.ensure()

from prosheets import config as ps_config   # noqa: E402
from prosheets import runner                # noqa: E402

output = script.get_output()
PATH = prosheets_setup.profile_path()


def main():
    if not os.path.isfile(PATH):
        forms.alert("Zatial nie je ulozeny ziadny profil. Spusti najprv "
                    "'Export vykresov'.", title="ProSheets Lite")
        return
    try:
        config = ps_config.load(PATH)
    except Exception as exc:
        forms.alert(u"Profil sa neda pouzit:\n%s" % exc, title="ProSheets Lite")
        return

    selection = config["sheet_selection"]
    summary = (u"Formaty: %s\nSablona: %s\nVystup: %s\nVyber: %s"
               % (", ".join(config["formats"]), config["file_name_template"],
                  config["output_folder"], selection["mode"]))
    if selection["mode"] == "numbers":
        summary += u" (%d vykresov)" % len(selection["numbers"])
    if not forms.alert(summary + "\n\nSpustit export?", title="ProSheets Lite",
                       yes=True, no=True):
        return

    with forms.ProgressBar(title="Export {value}/{max_value} - {title}",
                           cancellable=True) as progress_bar:
        def progress(done, total, text):
            if progress_bar.cancelled:
                return False
            progress_bar.title = text
            progress_bar.update_progress(done, total)
            return True

        report = runner.run(revit.doc, config, progress)

    log_path = report.write_csv(config["output_folder"])
    output.print_md("### ProSheets Lite - opakovany export")
    for line in report.lines():
        output.print_md("    " + line)
    output.print_md("Log davky: `%s`" % log_path)
    forms.alert(report.summary(), title="ProSheets Lite")


main()
