# -*- coding: utf-8 -*-
"""Skladanie nazvov suborov zo sablony s tokenmi.

Sablona sa pise podobne ako v DiRoots ProSheets, napr.:

    {Sheet Number} - {Sheet Name}
    {Project Number}_{Sheet Number}_R{Current Revision|00}
    {Sheet Number}-{Sheet Name:slug}

Syntax tokenu:  {Nazov parametra[|nahradna hodnota][:modifikator]}

Modifikatory: upper, lower, title, slug, trim, nospace
"""

import re
import unicodedata

TOKEN = re.compile(r"\{([^{}]+)\}")

# Znaky zakazane v nazve suboru na Windows + riadiace znaky.
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Nazvy rezervovane Windowsom - samotne alebo s priponou.
RESERVED = set(["CON", "PRN", "AUX", "NUL"] +
               ["COM%d" % i for i in range(1, 10)] +
               ["LPT%d" % i for i in range(1, 10)])

MAX_LENGTH = 180        # rezerva na cestu k adresaru a priponu


def _slug(text):
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = u"".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_only).strip("-")


MODIFIERS = {
    "upper": lambda value: value.upper(),
    "lower": lambda value: value.lower(),
    "title": lambda value: value.title(),
    "trim": lambda value: value.strip(),
    "nospace": lambda value: re.sub(r"\s+", "", value),
    "slug": _slug,
}


class NamingError(ValueError):
    """Chybna sablona nazvu."""


def parse_token(raw):
    """'Sheet Name|bez nazvu:upper' -> ('Sheet Name', 'bez nazvu', 'upper')."""
    body, modifier = raw, None
    if ":" in body:
        body, _, modifier = body.rpartition(":")
        modifier = modifier.strip().lower()
        if modifier not in MODIFIERS:
            # Dvojbodka nebola modifikator, ale sucast nazvu parametra.
            body, modifier = raw, None
    name, fallback = body, ""
    if "|" in body:
        name, _, fallback = body.partition("|")
    return name.strip(), fallback, modifier


def tokens_in(template):
    """Zoznam nazvov parametrov pouzitych v sablone."""
    return [parse_token(match)[0] for match in TOKEN.findall(template or "")]


def validate_template(template):
    """Overi sablonu; vrati zoznam varovani (prazdny = v poriadku)."""
    if not template or not template.strip():
        raise NamingError("Sablona nazvu je prazdna.")
    if template.count("{") != template.count("}"):
        raise NamingError("Nesparovane zatvorky v sablone: %s" % template)
    warnings = []
    if not TOKEN.search(template):
        warnings.append("Sablona neobsahuje ziadny token - vsetky subory by mali "
                        "rovnaky nazov.")
    for raw in TOKEN.findall(template):
        if not parse_token(raw)[0]:
            raise NamingError("Token bez nazvu parametra: {%s}" % raw)
    return warnings


def sanitize(name, replacement="_"):
    """Odstrani znaky zakazane vo Windows nazvoch suborov."""
    cleaned = ILLEGAL.sub(replacement, name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")           # Windows nedovoli koncovu bodku/medzeru
    if not cleaned:
        cleaned = "bez-nazvu"
    if cleaned.split(".")[0].upper() in RESERVED:
        cleaned = "_" + cleaned
    if len(cleaned) > MAX_LENGTH:
        cleaned = cleaned[:MAX_LENGTH].rstrip(". ")
    return cleaned


def render(template, resolver, missing=None):
    """Zlozi nazov suboru zo sablony.

    `resolver` je funkcia nazov_parametra -> hodnota (alebo None, ak parameter
    neexistuje). Do zoznamu `missing` sa zapisu tokeny, ktore sa nepodarilo
    vyhodnotit - volajuci ich moze reportovat pouzivatelovi.
    """
    def substitute(match):
        name, fallback, modifier = parse_token(match.group(1))
        try:
            value = resolver(name)
        except Exception:
            value = None
        if value is None or value == "":
            if missing is not None and not fallback:
                missing.append(name)
            value = fallback
        value = u"%s" % value
        if modifier:
            value = MODIFIERS[modifier](value)
        return value

    return sanitize(TOKEN.sub(substitute, template))


def deduplicate(names):
    """Zabezpeci jedinecnost nazvov v davke: 'A', 'A' -> 'A', 'A_2'.

    Porovnava sa bez ohladu na velkost pismen, lebo Windows subory tiez
    nerozlisuje - inak by druhy export prepisal prvy.
    """
    seen, result = {}, []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen[key] = 1
            result.append(name)
            continue
        seen[key] += 1
        candidate = "%s_%d" % (name, seen[key])
        while candidate.lower() in seen:
            seen[key] += 1
            candidate = "%s_%d" % (name, seen[key])
        seen[candidate.lower()] = 1
        result.append(candidate)
    return result


# --- Skladanie sablony z casti (pre klikacie rozhranie) ---------------------
#
# Cast (segment) je jeden usek nazvu: parameter obaleny prefixom a suffixom.
# Segment bez parametra je cisty text - hodi sa na oddelovace.
#
#   {"parameter": "Sheet Number", "prefix": "",    "suffix": ""}
#   {"parameter": "Sheet Name",   "prefix": " - ", "suffix": ""}
#   {"parameter": "",             "prefix": "_v2", "suffix": ""}
#
# Segmenty su ulozene v profile a `build_template` z nich zlozi tu istu
# sablonu, aku by pouzivatel napisal rucne. Sablona zostava jedinym
# formatom, ktoremu rozumie `render`.

SEGMENT_KEYS = ("parameter", "prefix", "suffix", "fallback", "modifier")


def _literal(text):
    """Text okolo tokenu - zatvorky by rozbili sablonu, tak ich vyhodime."""
    return (text or "").replace("{", "").replace("}", "")


def build_template(segments, prefix="", suffix=""):
    """Zlozi sablonu nazvu zo zoznamu casti a celkoveho prefixu/suffixu."""
    parts = [_literal(prefix)]
    for segment in segments or []:
        name = (segment.get("parameter") or "").strip()
        parts.append(_literal(segment.get("prefix")))
        if name:
            token = name
            fallback = (segment.get("fallback") or "").strip()
            if fallback:
                token += "|" + _literal(fallback)
            modifier = (segment.get("modifier") or "").strip().lower()
            if modifier in MODIFIERS:
                token += ":" + modifier
            parts.append("{%s}" % token)
        parts.append(_literal(segment.get("suffix")))
    parts.append(_literal(suffix))
    return "".join(parts)


def segments_from_template(template):
    """Rozlozi sablonu spat na casti, aby sa dala upravovat v rozhrani.

    Text pred tokenom sa stane jeho prefixom, text za poslednym tokenom
    suffixom poslednej casti. `build_template(segments_from_template(t)) == t`
    pre kazdu platnu sablonu.
    """
    segments, position = [], 0
    for match in TOKEN.finditer(template or ""):
        name, fallback, modifier = parse_token(match.group(1))
        segments.append({
            "parameter": name,
            "prefix": template[position:match.start()],
            "suffix": "",
            "fallback": fallback,
            "modifier": modifier or "",
        })
        position = match.end()

    trailing = (template or "")[position:]
    if trailing:
        if segments:
            segments[-1]["suffix"] = trailing
        else:
            segments.append({"parameter": "", "prefix": trailing, "suffix": "",
                             "fallback": "", "modifier": ""})
    return segments


def describe_segment(segment):
    """Citatelny popis casti pre zoznam v rozhrani."""
    name = (segment.get("parameter") or "").strip()
    core = "{%s}" % name if name else "(text)"
    fallback = (segment.get("fallback") or "").strip()
    if fallback:
        core += " ak prazdne: '%s'" % fallback
    modifier = (segment.get("modifier") or "").strip()
    if modifier:
        core += " (%s)" % modifier
    prefix, suffix = segment.get("prefix") or "", segment.get("suffix") or ""
    if prefix:
        core = "'%s' + %s" % (prefix, core)
    if suffix:
        core = "%s + '%s'" % (core, suffix)
    return core


def render_segments(segments, resolver, prefix="", suffix="", missing=None):
    """Zlozi nazov priamo z casti, bez medzikroku cez sablonu.

    Rozdiel oproti `render`: ked parameter nema hodnotu a nie je zadana
    nahradna hodnota, **vynecha sa cela cast** vratane svojho prefixu
    a suffixu. Vdaka tomu v nazve nezostanu osamotene oddelovace
    ('A-101__' namiesto 'A-101_02_'). Ak ma na mieste prazdnej hodnoty
    nieco zostat, patri to do `fallback`.
    """
    parts = [_literal(prefix)]
    for segment in segments or []:
        name = (segment.get("parameter") or "").strip()
        before = _literal(segment.get("prefix"))
        after = _literal(segment.get("suffix"))

        if not name:                      # cast bez parametra je cisty text
            parts.append(before + after)
            continue

        try:
            value = resolver(name)
        except Exception:
            value = None

        if value is None or value == "":
            fallback = (segment.get("fallback") or "").strip()
            if not fallback:
                if missing is not None and name not in missing:
                    missing.append(name)
                continue                  # cela cast vypadne
            value = fallback

        value = u"%s" % value
        modifier = (segment.get("modifier") or "").strip().lower()
        if modifier in MODIFIERS:
            value = MODIFIERS[modifier](value)
        parts.append(before + value + after)

    parts.append(_literal(suffix))
    return sanitize(u"".join(parts))
