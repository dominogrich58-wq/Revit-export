# -*- coding: utf-8 -*-
"""Spustenie ulozeneho profilu bez otvarania okna.

Hodi sa na opakovane odovzdavky: profil si nastavis raz v okne Export
vykresov a odvtedy je export na dva kliky. Tlacidlo nepouziva WPF, takze
funguje aj tam, kde by sa hlavne okno nepodarilo otvorit.
"""

__title__ = "Rýchly\nexport"
__doc__ = ("Spusti ulozeny profil exportu na aktualnom modeli, bez "
           "otvarania hlavneho okna.")

from pyrevit import forms, revit, script

import sheetpilot_setup
sheetpilot_setup.ensure()

from sheetpilot import profiles   # noqa: E402
from sheetpilot import runner     # noqa: E402

output = script.get_output()
STORE = sheetpilot_setup.store()


def pick_profile():
    """Aktivny profil, alebo vyber zo zoznamu ak ich je viac."""
    names = STORE.names()
    if not names:
        forms.alert("Zatial nie je ulozeny ziadny profil. Spusti najprv "
                    "'Export vykresov'.", title="SheetPilot")
        return None
    if len(names) == 1:
        return names[0]

    active = STORE.active_name()
    labelled = [(u"%s  (aktivny)" % name) if name == active else name
                for name in names]
    choice = forms.SelectFromList.show(labelled, title="Ktory profil spustit?",
                                       button_name="Spustit", multiselect=False)
    if not choice:
        return None
    return names[labelled.index(choice)]


def describe(config):
    selection = config["sheet_selection"]
    lines = [u"Formaty: %s" % ", ".join(config["formats"]),
             u"Nazov: %s" % config_template(config),
             u"Vystup: %s" % config["output_folder"],
             u"Vyber vykresov: %s" % selection["mode"]]
    if selection["mode"] == "numbers":
        lines[-1] += u" (%d vykresov)" % len(selection["numbers"])
    elif selection["mode"] == "set":
        lines[-1] += u" (%s)" % selection["set_name"]
    return u"\n".join(lines)


def config_template(config):
    from sheetpilot.config import effective_template
    return effective_template(config)


def main():
    name = pick_profile()
    if not name:
        return
    try:
        config = STORE.load(name)
    except profiles.ProfileError as exc:
        forms.alert(u"%s" % exc, title="SheetPilot")
        return
    except Exception as exc:
        forms.alert(u"Profil '%s' sa neda pouzit:\n%s" % (name, exc),
                    title="SheetPilot")
        return

    if not forms.alert(u"Profil %s\n\n%s\n\nSpustit export?"
                       % (name, describe(config)),
                       title="SheetPilot", yes=True, no=True):
        return
    STORE.set_active(name)

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
    output.print_md("### SheetPilot - profil %s" % name)
    for line in report.lines():
        output.print_md("    " + line)
    output.print_md("Log davky: `%s`" % log_path)
    forms.alert(report.summary(), title="SheetPilot")


main()
