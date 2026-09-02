# -*- coding: utf-8 -*-
"""Skladanie nazvov suborov zo sablony s tokenmi.

Sablona sa pise podobne ako v ProSheets, napr.:

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
