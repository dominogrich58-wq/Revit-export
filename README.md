# ProSheets Lite — dávkový export Revit výkresov do PDF a DWG

Vlastná náhrada za **DiRoots ProSheets**: vyberieš výkresy, nastavíš schému názvov
súborov a jedným spustením ich vyexportuješ do PDF a DWG. K dispozícii sú dve
rozhrania nad tým istým jadrom:

* **Dynamo graf** (`dynamo/`) — na spustenie priamo z Dynama, bez inštalácie čohokoľvek.
* **pyRevit plugin** (`pyrevit/`) — tlačidlá na páse s dialógmi, priebehom a logom.

## Čo to vie

| Funkcia | Poznámka |
|---|---|
| Export do PDF | natívny `PDFExportOptions` (Revit 2022+); pre staršie Revity záloha cez virtuálnu PDF tlačiareň |
| Export do DWG | s použitím uloženého **DWG Export Setupu**, voliteľná verzia AutoCADu |
| Vlastná schéma názvov | tokeny z parametrov výkresu a projektu, napr. `{Sheet Number} - {Sheet Name}` |
| Spojené PDF | všetky výkresy do jedného súboru s vlastným názvom |
| Výber výkresov | ručne, podľa Sheet Setu, podľa čísel, alebo filtrom (prefix / názov / parameter) |
| Podpriečinky | `PDF/` a `DWG/` sa vytvoria automaticky pri exporte viacerých formátov |
| Ochrana proti prepisu | existujúci súbor sa preskočí alebo prepíše podľa nastavenia |
| Jedinečné názvy | dva výkresy s rovnakým názvom nedostanú ten istý súbor (`… _2`) |
| CSV log | po každej dávke sa uloží prehľad OK / preskočené / chyby |
| Profily | nastavenia sa ukladajú do JSON a dajú sa prenášať medzi ľuďmi |

## Štruktúra repozitára

```
lib/prosheets/          jadro (naming, config, výber výkresov, exportéry, report)
dynamo/                 .dyn grafy + zdrojové Python skripty nodov
pyrevit/                pyRevit extension (tlačidlá Export / Profil / Opakuj)
examples/               ukážkové JSON profily
tools/build_dyn.py      generátor .dyn grafov zo skriptov v dynamo/python
tests/                  unit testy logiky (bežia bez Revitu)
```

Moduly `naming`, `config` a `report` nemajú žiadnu závislosť na Revit API,
preto sa dajú testovať a ladiť mimo Revitu.

## Inštalácia — Dynamo

1. Skopíruj priečinok `lib` napríklad do `C:\ProSheetsLite\lib`
   (musí v ňom zostať podpriečinok `prosheets`).
2. Otvor `dynamo/ProSheets Lite - Export.dyn` v Dynamo for Revit.
3. Do vstupu **LibPath** zadaj `C:\ProSheetsLite\lib`.
4. Vyplň **OutputFolder**, **Formats** (`["PDF"]`, `["DWG"]` alebo oboje)
   a **FileNameTemplate**.
5. Voliteľne pripoj do vstupu **Sheets** výkresy z Dynama (napr. z node
   `Categories → Sheets → All Elements of Category`). Ak necháš prázdne,
   exportujú sa všetky výkresy v modeli.
6. Prepni **Run** na `True`.

Graf `ProSheets Lite - Zoznam výkresov.dyn` vypíše, aké výkresy, Sheet Sety
a DWG Export Setupy v modeli existujú — hodí sa pri ladení nastavení.

> Python nody sú nastavené na engine **CPython3**. V Revite 2021 a staršom
> prepni engine nodu na IronPython 2.7 — kód je kompatibilný s oboma.

## Inštalácia — pyRevit

```
pyrevit extend ui ProSheetsLite <url-repozitara>
```

alebo ručne (odporúčané, keď pyRevit používaš prvýkrát):

1. Nainštaluj **pyRevit** z [pyrevitlabs.io](https://pyrevitlabs.io) — je to samostatný
   Windows inštalátor, nie doplnok do Revitu. Revit musí byť pri inštalácii zavretý.
2. Vytvor si priečinok pre extensions, napr. `C:\pyRevitExtensions`, a skopíruj doň
   celý priečinok `ProSheetsLite.extension` (názov musí končiť na `.extension`).
3. Otvor Revit → pás **pyRevit** → **Settings** → sekcia **Custom Extension Directories**
   → **Add Folder** → vyber `C:\pyRevitExtensions` (**nie** samotný `.extension` priečinok!)
   → **Save Settings and Reload**.

Balík `prosheets` sa hľadá v tomto poradí:

1. premenná prostredia `PROSHEETS_LIB`,
2. priečinok `lib` v koreni tohto repozitára (keď je extension v repozitári),
3. `lib` priamo v extensione (sebestačná kópia),
4. `%APPDATA%\ProSheetsLite\lib`,
5. `C:\ProSheetsLite\lib` — teda to isté miesto ako pri Dynamo návode, takže
   stačí jedna kópia knižnice pre obe rozhrania.

Na páse pribudne záložka **ProSheets** s tromi tlačidlami:

* **Export výkresov** — sprievodca: výkresy → formáty → schéma názvov → PDF spojiť? → DWG setup → priečinok.
* **Profil nastavení** — zobrazenie, otvorenie, reset, import a export profilu.
* **Opakuj posledný** — zopakuje posledný export bez dialógov (ideálne na pravidelné odovzdávky).

## Schéma názvov súborov

```
{Názov parametra[|náhradná hodnota][:modifikátor]}
```

Vstavané tokeny: `{Sheet Number}`, `{Sheet Name}`, `{Current Revision}`,
`{Current Revision Date}`, `{Current Revision Description}`, `{Project Number}`,
`{File Name}` (názov modelu), `{Date}`, `{Time}`, `{yyyy}`, `{yyyymmdd}`.
Okrem nich funguje **ľubovoľný parameter výkresu**, a ak ho výkres nemá,
hľadá sa v **Project Information**.

Modifikátory: `:upper`, `:lower`, `:title`, `:slug` (bez diakritiky a medzier),
`:nospace`, `:trim`.

Príklady:

```
{Sheet Number} - {Sheet Name}                 ->  A-101 - Pôdorys 1.NP
{Project Number}_{Sheet Number}               ->  2024-018_A-101
{Sheet Number} R{Current Revision|00}         ->  A-101 R00
{yyyymmdd}_{Sheet Number}_{Sheet Name:slug}   ->  20260902_A-101_Podorys-1-NP
```

Znaky, ktoré Windows v názve súboru nedovolí (`\ / : * ? " < > |`), sa nahradia
podčiarkovníkom; názov sa oreže na 180 znakov a rezervované názvy (`CON`, `PRN`…)
dostanú prefix.

## Profil (JSON)

Kompletné nastavenia s predvolbami sú v `lib/prosheets/config.py`, hotové ukážky
v `examples/`. Kľúčové položky:

```jsonc
{
  "output_folder": "C:\\Export\\Vykresy",
  "formats": ["PDF", "DWG"],
  "file_name_template": "{Sheet Number} - {Sheet Name}",
  "subfolder_per_format": true,        // PDF/ a DWG/ podpriečinky
  "overwrite": true,
  "sheet_selection": {
    "mode": "filter",                  // all | set | numbers | filter
    "set_name": "DSP - odovzdanie",    // pre mode "set"
    "numbers": ["A-101", "A-102"],     // pre mode "numbers"
    "number_prefix": "A-",             // pre mode "filter"
    "name_contains": "",
    "parameter_equals": {}
  },
  "pdf": { "combine": false, "raster_quality": "High", "color_depth": "Color" },
  "dwg": { "export_setup": "", "file_version": "AutoCAD2018" }
}
```

Profil sa ukladá do `%APPDATA%\ProSheetsLite\profile.json` a dá sa cez tlačidlo
**Profil nastavení** vyexportovať a rozdistribuovať v tíme, aby všetci odovzdávali
rovnako pomenované súbory.

## Obmedzenia, o ktorých je dobré vedieť

* **PDF vyžaduje Revit 2022+.** Staršie verzie nemajú `PDFExportOptions`; v `lib/prosheets/exporters/pdf.py`
  je funkcia `print_via_driver()`, ktorá tlačí cez virtuálnu PDF tlačiareň, ale
  závisí od konkrétneho ovládača na stanici.
* PDF sa exportuje po jednom výkrese s `Combine = True`. Je to zámer — len v tomto
  režime Revit použije presne náš názov súboru, inak si ho skladá podľa vlastných
  naming rules.
* DWG sa exportuje po jednom výkrese z rovnakého dôvodu (pri viacerých naraz si
  Revit lepí názvy pohľadov za názov súboru).
* Nastavenia vrstiev, hrúbok čiar a textov pre DWG sa neriešia tu — použije sa
  uložený **DWG Export Setup** z modelu (`dwg.export_setup`).
* Placeholder výkresy sa preskakujú, exportovať sa nedajú.
* Ak je cieľový súbor otvorený v inej aplikácii, export ho preskočí a zapíše
  dôvod do logu namiesto pádu celej dávky.

## Vývoj

```bash
PYTHONPATH=lib:tests python3 -m unittest discover -s tests -v   # 50 testov
python3 tools/build_dyn.py                                      # regenerácia .dyn grafov
```

Python kód nodov uprav v `dynamo/python/*.py` a spusti `tools/build_dyn.py` —
`.dyn` súbory sú generované, needituj v nich Python ručne. CI kontroluje, že
vygenerované grafy sedia so zdrojmi.
