# -*- coding: utf-8 -*-
"""Generator ikon tlacidiel pre pyRevit.

Ikony sa kreslia kodom, nie v grafickom editore, aby sa dali kedykolvek
prekreslit - zmenit farbu, velkost alebo tvar - bez toho, aby niekto musel
otvarat binarny subor. Kresli sa 4x zvacsene a potom zmensi, tym vznikne
hladky okraj bez toho, aby sme potrebovali graficku kniznicu.

Spustenie:  python3 tools/make_icons.py
"""

import os
import struct
import zlib

SIZE = 96          # vysledna velkost ikony v px
SCALE = 4          # kreslime SIZE*SCALE a potom priemerujeme

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "pyrevit", "SheetPilot.extension", "SheetPilot.tab",
                     "Export.panel")

TEAL = (0x0B, 0x6E, 0x7A)          # hlavna farba, svetly pas
TEAL_SOFT = (0x8F, 0xC2, 0xC8)     # vyplne a druhoradé tvary
TEAL_LIGHT = (0x5A, 0xC4, 0xD2)    # hlavna farba na tmavom pase
TEAL_LIGHT_SOFT = (0x2E, 0x6B, 0x74)


# --- tvary: kazdy vrati funkciu (x, y) -> True, ak bod lezi vnutri ---------

def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1


def polygon(points):
    def inside(x, y):
        crossings, count = False, len(points)
        j = count - 1
        for i in range(count):
            xi, yi = points[i]
            xj, yj = points[j]
            if (yi > y) != (yj > y) and \
                    x < (xj - xi) * (y - yi) / float(yj - yi) + xi:
                crossings = not crossings
            j = i
        return crossings
    return inside


def union(*shapes):
    return lambda x, y: any(s(x, y) for s in shapes)


# --- kreslenie -------------------------------------------------------------

def draw(layers):
    """Vykresli zoznam (tvar, farba) do RGBA buffra vo velkosti SIZE."""
    big = SIZE * SCALE
    buffer = [[(0, 0, 0, 0)] * big for _ in range(big)]

    for shape, color in layers:
        for y in range(big):
            row = buffer[y]
            py = (y + 0.5) / SCALE
            for x in range(big):
                if shape((x + 0.5) / SCALE, py):
                    row[x] = (color[0], color[1], color[2], 255)

    # zmensenie priemerovanim - odtial pochadza hladky okraj
    out = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            r = g = b = a = 0
            for dy in range(SCALE):
                for dx in range(SCALE):
                    pr, pg, pb, pa = buffer[y * SCALE + dy][x * SCALE + dx]
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            if a:
                row.append((r // a, g // a, b // a, a // (SCALE * SCALE)))
            else:
                row.append((0, 0, 0, 0))
        out.append(row)
    return out


def write_png(path, pixels):
    raw = b""
    for row in pixels:
        raw += b"\x00" + b"".join(struct.pack("BBBB", *px) for px in row)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)
    return path


# --- konkretne ikony -------------------------------------------------------

def sheet_layers(strong, soft):
    """Jeden vykres s ohnutym rohom a tromi riadkami textu.

    Na pase sa ikona zobrazuje okolo 32 px, takze plati: cim menej tvarov,
    tym citatelnejsie. Vykres drzi lavu polovicu, symbol pravu, neprekryvaju
    sa - inak by na malej velkosti splynuli.
    """
    body = polygon([(8, 12), (38, 12), (50, 24), (50, 84), (8, 84)])
    fold = polygon([(38, 12), (50, 24), (38, 24)])

    lines = [rect(16, 36, 42, 42), rect(16, 50, 42, 56), rect(16, 64, 32, 70)]
    return [(body, strong), (fold, soft), (union(*lines), (255, 255, 255))]


def export_icon(strong, soft):
    """Vykres + sipka von = davkovy export."""
    arrow = polygon([(58, 43), (76, 43), (76, 32), (92, 50), (76, 68),
                     (76, 57), (58, 57)])
    return sheet_layers(strong, soft) + [(arrow, strong)]


def quick_icon(strong, soft):
    """Vykres + blesk = spustenie ulozeneho profilu bez otazok."""
    bolt = polygon([(82, 22), (60, 54), (72, 54), (66, 82), (90, 48),
                    (77, 48), (86, 22)])
    return sheet_layers(strong, soft) + [(bolt, strong)]


ICONS = [
    ("ExportSheets.pushbutton", export_icon),
    ("QuickExport.pushbutton", quick_icon),
]


def main():
    for folder, builder in ICONS:
        target = os.path.join(PANEL, folder)
        if not os.path.isdir(target):
            raise SystemExit("Priecinok tlacidla neexistuje: %s" % target)
        print("zapisane: %s" % write_png(os.path.join(target, "icon.png"),
                                         draw(builder(TEAL, TEAL_SOFT))))
        print("zapisane: %s" % write_png(
            os.path.join(target, "icon.dark.png"),
            draw(builder(TEAL_LIGHT, TEAL_LIGHT_SOFT))))


if __name__ == "__main__":
    main()
