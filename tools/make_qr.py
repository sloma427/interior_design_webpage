#!/usr/bin/env python3
"""Generuje stylizowany kod QR wizytówki RD Studio (kropki, zaokrąglone narożniki, monogram RD).

Użycie (z katalogu repozytorium):
    pip install segno
    python3 tools/make_qr.py https://rdstudiodesign.com/card/a/ card/a/qr-card.svg

Zapisuje SVG; PNG generuje się z niego osobno (np. renderując SVG w przeglądarce).
Korekcja błędów H (30%), bo środek kodu zasłania monogram.
"""
import re
import sys

import segno

COLOR = '#5A4D3B'
BORDER = 4            # margines w modułach
DOT = 0.86            # średnica kropki względem modułu
LOGO_MAX = 11         # największy bok kwadratu na monogram (w modułach, nieparzysty)
LOGO_SHARE = 0.09     # monogram zajmuje najwyżej ~9% kodu (przy większym udziale OpenCV gubił odczyt)

# Monogram RD z logo-clean.svg (viewBox 2606x2314; sam monogram zajmuje x 66–2523, y 23–1655)
LOGO_SVG = 'index_files/logo-clean.svg'
RD_VIEWBOX = '66 23 2457 1632'

# Pozycje środków wzorców wyrównania dla wersji 2–10 (ISO/IEC 18004, tabela E.1)
ALIGNMENT = {2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
             7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}


def rounded_rect(x, y, w, h, r):
    return (f'M{x + r},{y}h{w - 2 * r}a{r},{r} 0 0 1 {r},{r}v{h - 2 * r}a{r},{r} 0 0 1 {-r},{r}'
            f'h{-(w - 2 * r)}a{r},{r} 0 0 1 {-r},{-r}v{-(h - 2 * r)}a{r},{r} 0 0 1 {r},{-r}z')


def main(url, out_path):
    qr = segno.make_qr(url, error='h', boost_error=False)
    n = qr.symbol_size(border=0)[0]
    matrix = [list(row) for row in qr.matrix]
    total = n + 2 * BORDER

    reserved = set()

    def reserve(x0, y0, size):
        for yy in range(y0, y0 + size):
            for xx in range(x0, x0 + size):
                reserved.add((xx, yy))

    finders = [(0, 0), (n - 7, 0), (0, n - 7)]
    for fx, fy in finders:
        reserve(fx, fy, 7)

    aligns = []
    pos = ALIGNMENT.get(qr.version, [])
    for ay in pos:
        for ax in pos:
            if (ax, ay) in reserved:   # nachodzi na wzorzec narożny
                continue
            aligns.append((ax, ay))
            reserve(ax - 2, ay - 2, 5)

    logo_modules = min(LOGO_MAX, int((LOGO_SHARE * n * n) ** 0.5))
    if logo_modules % 2 == 0:
        logo_modules -= 1
    c = n // 2
    half = logo_modules // 2
    reserve(c - half, c - half, logo_modules)

    parts = []
    # kropki danych
    r = DOT / 2
    for y in range(n):
        for x in range(n):
            if matrix[y][x] and (x, y) not in reserved:
                parts.append(f'<circle cx="{x + BORDER + 0.5}" cy="{y + BORDER + 0.5}" r="{r}"/>')
    # wzorce narożne: lekko zaokrąglony pierścień 7x7 + kwadrat 3x3.
    # Większe zaokrąglenie wygląda miękcej, ale część dekoderów (np. OpenCV)
    # przestaje wtedy znajdować narożniki; te promienie przechodziły wszystkie testy.
    for fx, fy in finders:
        x, y = fx + BORDER, fy + BORDER
        parts.append(f'<path fill-rule="evenodd" d="{rounded_rect(x, y, 7, 7, 0.55)}{rounded_rect(x + 1, y + 1, 5, 5, 0.35)}"/>')
        parts.append(f'<path d="{rounded_rect(x + 2, y + 2, 3, 3, 0.25)}"/>')
    # wzorce wyrównania: pierścień 5x5 + kropka
    for ax, ay in aligns:
        x, y = ax - 2 + BORDER, ay - 2 + BORDER
        parts.append(f'<path fill-rule="evenodd" d="{rounded_rect(x, y, 5, 5, 0.4)}{rounded_rect(x + 1, y + 1, 3, 3, 0.25)}"/>')
        parts.append(f'<circle cx="{ax + BORDER + 0.5}" cy="{ay + BORDER + 0.5}" r="0.5"/>')

    # monogram RD w środku
    logo = open(LOGO_SVG, encoding='utf-8').read()
    inner = re.search(r'<g\b.*</g>', logo, re.S).group(0)
    inner = re.sub(r'fill="[^"]*"', f'fill="{COLOR}"', inner)
    box = logo_modules - 2          # 1 moduł światła dookoła monogramu
    lw = box
    lh = box * 1632 / 2457
    lx = c - half + 1 + BORDER
    ly = c + BORDER + 0.5 - lh / 2
    parts.append(f'<svg x="{lx}" y="{ly:.3f}" width="{lw}" height="{lh:.3f}" viewBox="{RD_VIEWBOX}">{inner}</svg>')

    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" width="{total * 10}" height="{total * 10}">'
           f'<rect width="{total}" height="{total}" fill="#FFFFFF"/>'
           f'<g fill="{COLOR}">{"".join(parts)}</g></svg>\n')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f'{out_path}: version {qr.version}, ECC {qr.error.upper()}, {n}x{n} modules, '
          f'logo {logo_modules}x{logo_modules} ({100 * logo_modules ** 2 / n ** 2:.1f}% of symbol)')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
