# SheetPilot — dávkový export Revit výkresov do PDF a DWG

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
| Vlastná schéma názvov | naklikaná z parametrov výkresu a projektu, s prefixom a suffixom pri každej časti |
| Export DWG bez xref | všetko sa zlúči do jedného DWG na výkres, alebo sa vytvoria externé referencie |
| Spojené PDF | všetky výkresy do jedného súboru s vlastným názvom |
| Výber výkresov | ručne, podľa Sheet Setu, podľa čísel, alebo filtrom (prefix / názov / parameter) |
| Usporiadanie výstupu | buď podpriečinky `PDF/` a `DWG/`, alebo všetko dokopy v jednom |
| Ochrana proti prepisu | existujúci súbor sa preskočí alebo prepíše podľa nastavenia |
| Jedinečné názvy | dva výkresy s rovnakým názvom nedostanú ten istý súbor (`… _2`) |
| CSV log | po každej dávke sa uloží prehľad OK / preskočené / chyby |
| Pomenované profily | viac schém exportu vedľa seba, prepínanie jedným klikom, prenos medzi ľuďmi |

## Štruktúra repozitára

```
lib/sheetpilot/         jadro (naming, config, profiles, výber výkresov,
                        exportéry, report)
dynamo/                 .dyn grafy + zdrojové Python skripty nodov
pyrevit/                pyRevit extension (Export výkresov / Profily / Spusti profil)
                        - okná sú v .xaml, ich obsluha v lib/sheetpilot_ui.py
examples/               ukážkové JSON profily
tools/build_dyn.py      generátor .dyn grafov zo skriptov v dynamo/python
tests/                  unit testy logiky (bežia bez Revitu)
```

Moduly `naming`, `config`, `profiles` a `report` nemajú žiadnu závislosť na Revit API,
preto sa dajú testovať a ladiť mimo Revitu.

## Inštalácia — Dynamo

1. Skopíruj priečinok `lib` napríklad do `C:\SheetPilot\lib`
   (musí v ňom zostať podpriečinok `sheetpilot`).
2. Otvor `dynamo/SheetPilot - Export.dyn` v Dynamo for Revit.
3. Do vstupu **LibPath** zadaj `C:\SheetPilot\lib`.
4. Vyplň **OutputFolder**, **Formats** (`["PDF"]`, `["DWG"]` alebo oboje)
   a **FileNameTemplate**.
5. Voliteľne pripoj do vstupu **Sheets** výkresy z Dynama (napr. z node
   `Categories → Sheets → All Elements of Category`). Ak necháš prázdne,
   exportujú sa všetky výkresy v modeli.
6. Prepni **Run** na `True`.

Graf `SheetPilot - Zoznam výkresov.dyn` vypíše, aké výkresy, Sheet Sety
a DWG Export Setupy v modeli existujú — hodí sa pri ladení nastavení.

> Python nody sú nastavené na engine **CPython3**. V Revite 2021 a staršom
> prepni engine nodu na IronPython 2.7 — kód je kompatibilný s oboma.

## Inštalácia — pyRevit

```
pyrevit extend ui SheetPilot <url-repozitara>
```

alebo ručne (odporúčané, keď pyRevit používaš prvýkrát):

1. Nainštaluj **pyRevit** z [pyrevitlabs.io](https://pyrevitlabs.io) — je to samostatný
   Windows inštalátor, nie doplnok do Revitu. Revit musí byť pri inštalácii zavretý.
2. Vytvor si priečinok pre extensions, napr. `C:\pyRevitExtensions`, a skopíruj doň
   celý priečinok `SheetPilot.extension` (názov musí končiť na `.extension`).
3. Otvor Revit → pás **pyRevit** → **Settings** → sekcia **Custom Extension Directories**
   → **Add Folder** → vyber `C:\pyRevitExtensions` (**nie** samotný `.extension` priečinok!)
   → **Save Settings and Reload**.

Balík `sheetpilot` sa hľadá v tomto poradí:

1. premenná prostredia `SHEETPILOT_LIB`,
2. priečinok `lib` v koreni tohto repozitára (keď je extension v repozitári),
3. `lib` priamo v extensione (sebestačná kópia),
4. `%APPDATA%\SheetPilot\lib`,
5. `C:\SheetPilot\lib` — teda to isté miesto ako pri Dynamo návode, takže
   stačí jedna kópia knižnice pre obe rozhrania.

Na páse pribudne záložka **SheetPilot** s dvoma tlačidlami:

* **Export výkresov** — jedno okno so všetkým: zoznam výkresov s filtrom a Sheet Setmi,
  formáty s podvoľbami, skladačka názvu a výstupný priečinok. Po spustení sa okno prepne
  na ukazovateľ priebehu a potom na výsledok so zoznamom súborov a odkazom na CSV log.
* **Rýchly export** — spustí uložený profil bez otvárania okna. Na opakované
  odovzdávky: nastavíš raz, potom sú to dva kliky. Nepoužíva WPF, takže funguje
  aj tam, kde by sa hlavné okno nepodarilo otvoriť.

Profily sa spravujú priamo v hornej lište hlavného okna, samostatné tlačidlo
na ne netreba.

Ikony sa generujú skriptom `tools/make_icons.py` — sú kreslené kódom, takže sa
dajú prekresliť bez grafického editora (`python3 tools/make_icons.py`).

## Schéma názvov súborov

Názov sa dá poskladať dvoma spôsobmi — naklikaním v pyRevite, alebo napísaním
šablóny. Obe cesty vedú k tomu istému, klikanie len šablónu skladá za teba.

### Naklikanie

V hlavnom okne vidíš názov ako pás **žiletiek** — jedna žiletka = jedna časť názvu.
Tlačidlo **Upraviť názov…** otvorí tabuľku, kde má každá časť riadok:

| Stĺpec | Význam |
|---|---|
| Parameter | zo skutočných parametrov modelu, alebo `(iba text)` pre oddeľovač |
| Pred / Za | text pred parametrom a za ním, napr. `" - "` alebo `"_"` |
| Ak prázdne | náhradná hodnota, napr. `00` pri chýbajúcej revízii. **Keď zostane prázdne a parameter nemá hodnotu, vypadne celá časť aj s oddeľovačom** — v názve tak nezostanú osamotené podčiarkovníky |
| Písmená | VEĽKÉ, malé, Prvé Veľké, bez diakritiky, bez medzier |
| ↑ ↓ ✕ | poradie a odobratie |

Pod tabuľkou je prefix a suffix celého názvu (napr. `DSP_` a `_na-schvalenie`),
päť hotových schém a **živá ukážka** na prvom vybranom výkrese.

Ponuka parametrov sa načíta zo skutočného modelu — vstavané tokeny, parametre
výkresu (`Výkres: …`) a parametre projektu (`Projekt: …`), takže si nemusíš
pamätať, ako sa čo volá. Poskladané časti sa uložia do profilu
(`file_name_segments`).

### Šablóna

```
{Názov parametra[|náhradná hodnota][:modifikátor]}
```

Vstavané tokeny: `{Sheet Number}`, `{Sheet Name}`, `{Current Revision}`,
`{Current Revision Date}`, `{Current Revision Description}`, `{Sheet Width}`,
`{Sheet Height}` (rozmer výkresu v mm), `{Project Number}`, `{File Name}`
(názov modelu), `{Date}`, `{Time}`, `{yyyy}`, `{yyyymmdd}`.
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

## Profily

Nastavenia sa neukladajú do jedného súboru, ale do **pomenovaných profilov** —
môžeš mať vedľa seba napríklad *DSP odovzdanie*, *Rýchly náhľad PDF*
a *DWG pre statika* a prepínať medzi nimi jedným klikom.

```
%APPDATA%\SheetPilot\
    profiles\
        DSP odovzdanie.json
        Rychly nahlad PDF.json
    state.json          <- ktorý profil je aktívny
```

Ako s nimi pracovať:

* **Export výkresov** načíta aktívny profil ako predvyplnenie a na konci doň
  uloží, čo si nastavil. Pri úplne prvom exporte sa spýta na názov profilu.
* **Profily** slúžia na správu — *Nový profil z predvolieb*, *Prepnúť aktívny*,
  *Skopírovať aktívny* (dobré na variantu existujúceho nastavenia),
  *Premenovať*, *Zmazať*, *Otvoriť v editore*, a import/export do súboru
  na zdieľanie s kolegami.
* **Spusti profil** ponúkne zoznam profilov a vybraný spustí bez ďalších otázok.

Starý jednosúborový `profile.json` sa pri prvom spustení automaticky prenesie
medzi pomenované profily pod názvom *Predvoleny*; pôvodný súbor sa nemaže.

### Obsah profilu (JSON)

Kompletné nastavenia s predvolbami sú v `lib/sheetpilot/config.py`, hotové ukážky
v `examples/`. Kľúčové položky:

```jsonc
{
  "output_folder": "C:\\Export\\Vykresy",
  "formats": ["PDF", "DWG"],
  "file_name_template": "{Sheet Number} - {Sheet Name}",
  "file_name_segments": [                // naklikané časti; majú prednosť
    {"parameter": "Sheet Number", "prefix": "", "suffix": ""},
    {"parameter": "Sheet Name", "prefix": " - ", "suffix": ""}
  ],
  "file_name_prefix": "DSP_",            // pred celým názvom
  "file_name_suffix": "",                // za celým názvom
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
  "dwg": {
    "export_setup": "",
    "file_version": "AutoCAD2018",
    "external_references": false         // false = jeden DWG bez xref súborov
  }
}
```

Profil sa dá cez tlačidlo **Profily** vyexportovať do súboru a rozdistribuovať
v tíme, aby všetci odovzdávali rovnako pomenované súbory. Kolega ho načíta tou
istou cestou (*Načítať profil zo súboru*) a stačí mu prepísať výstupný adresár.

### Živý náhľad rozhrania

`docs/nahlad-okna.html` je klikací náhľad okna v prehliadači — slúžil na
odsúhlasenie rozloženia pred písaním XAML a hodí sa aj na vysvetlenie
rozhrania niekomu, kto Revit práve nemá otvorený.

### Keď sa záložka neobjaví

Chyba `Can not de/activate native item: Name: <nieco>` znamená, že názov záložky
sa zráža s existujúcou záložkou iného doplnku. Preto sa záložka volá
**SheetPilot**, a nie ProSheets — ten názov už používa DiRoots ProSheets.
Ak by kolidovala s niečím ďalším, stačí premenovať priečinok `SheetPilot.tab`.

## Obmedzenia, o ktorých je dobré vedieť

* **PDF vyžaduje Revit 2022+.** Staršie verzie nemajú `PDFExportOptions`; v `lib/sheetpilot/exporters/pdf.py`
  je funkcia `print_via_driver()`, ktorá tlačí cez virtuálnu PDF tlačiareň, ale
  závisí od konkrétneho ovládača na stanici.
* PDF sa exportuje po jednom výkrese s `Combine = True`. Je to zámer — len v tomto
  režime Revit použije presne náš názov súboru, inak si ho skladá podľa vlastných
  naming rules.
* DWG sa exportuje po jednom výkrese z rovnakého dôvodu (pri viacerých naraz si
  Revit lepí názvy pohľadov za názov súboru).
* Nastavenia vrstiev, hrúbok čiar a textov pre DWG sa neriešia tu — použije sa
  uložený **DWG Export Setup** z modelu (`dwg.export_setup`).
* Voľba `dwg.external_references` sa v Revit API mapuje na `MergedViews`
  (zlúčené = žiadne xref súbory). Overené to je len na úrovni volania API,
  nie na skutočnom exporte — po prvom behu si skontroluj, či vedľa hlavných
  DWG nepribudli súbory navyše.
* Placeholder výkresy sa preskakujú, exportovať sa nedajú.
* Okno je WPF, takže potrebuje **IronPython engine** pyRevitu (predvolený).
  Jadro aj tlačidlo *Spusti profil* bežia pod IronPythonom aj CPython3, takže
  keby okno v tvojej verzii pyRevitu zlyhalo, uložený profil sa dá spustiť aj tak.
* Export beží na hlavnom vlákne Revitu — inak sa Revit API volať nedá. Okno sa
  medzi výkresmi prekresľuje, takže priebeh je vidieť a *Prerušiť* reaguje,
  ale počas exportu sa s Revitom pracovať nedá.
* Ak je cieľový súbor otvorený v inej aplikácii, export ho preskočí a zapíše
  dôvod do logu namiesto pádu celej dávky.

## Vývoj

```bash
PYTHONPATH=lib:tests python3 -m unittest discover -s tests -v   # 125 testov
python3 tools/build_dyn.py                                      # regenerácia .dyn grafov
python3 tools/make_icons.py                                     # prekreslenie ikon
```

Python kód nodov uprav v `dynamo/python/*.py` a spusti `tools/build_dyn.py` —
`.dyn` súbory sú generované, needituj v nich Python ručne. CI kontroluje, že
vygenerované grafy sedia so zdrojmi.
