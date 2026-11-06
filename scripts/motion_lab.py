#!/usr/bin/env python3
"""Render the Motion Lab header and Beat Runner from profile activity data."""
from argparse import ArgumentParser
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import xml.etree.ElementTree as ET


THEMES = {
    "dark": {
        "body": "#101929", "bar": "#17273a", "ink": "#f0f7ff",
        "muted": "#a6bfd2", "edge": "#314a60", "teal": "#71efd4",
        "coral": "#ff928d", "amber": "#ffd585", "blank": "#1d3043",
        "levels": ("#28566b", "#377c88", "#4eaaab", "#79ead3"),
    },
    "light": {
        "body": "#f0f7f9", "bar": "#dcebf0", "ink": "#142c41",
        "muted": "#465f75", "edge": "#afc8d4", "teal": "#08786f",
        "coral": "#a6404a", "amber": "#855500", "blank": "#d9e7ed",
        "levels": ("#a1d4d0", "#6fb6b5", "#369b94", "#08786f"),
    },
}

SPRITE = (
    ".....YYYY...",
    "....YYYYYY..",
    "....YWWWWW..",
    ".....WW.W...",
    "......WWW...",
    ".....TTT....",
    "..TTTTTTT...",
    ".WW..TTTTT..",
    ".....TT..WW.",
    "....CCCT....",
    "...CCC.CC...",
    "..CCC...CC..",
    ".WWC.....CC.",
    ".WW.......WW",
)


def pixel_runner(x, y, size, colors):
    palette = {"Y": colors["amber"], "W": colors["ink"], "T": colors["teal"], "C": colors["coral"]}
    pixels = []
    for row, line in enumerate(SPRITE):
        for col, char in enumerate(line):
            if char != ".":
                pixels.append(f'<rect x="{col * size}" y="{row * size}" width="{size}" height="{size}" fill="{palette[char]}"/>')
    return f'<g transform="translate({x} {y})" shape-rendering="crispEdges">{"".join(pixels)}</g>'


def terminal_frame(colors, height, label):
    return f'''
<rect x=".5" y=".5" width="899" height="{height-1}" rx="10" fill="{colors["body"]}" stroke="{colors["edge"]}"/>
<path d="M10 1H890Q899 1 899 10V34H1V10Q1 1 10 1Z" fill="{colors["bar"]}"/>
<path d="M1 34H899" stroke="{colors["edge"]}"/>
<rect x="16" y="15" width="6" height="6" fill="{colors["coral"]}"/>
<rect x="28" y="15" width="6" height="6" fill="{colors["amber"]}"/>
<rect x="40" y="15" width="6" height="6" fill="{colors["teal"]}"/>
<text x="59" y="22" font-size="13" fill="{colors["muted"]}">{escape(label)}</text>'''


def hero_svg(theme):
    c = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="274" viewBox="0 0 900 274" role="img" aria-labelledby="hero-title">
<title id="hero-title">taku0193 — Motion. Rhythm. Code.</title>
<defs>
  <pattern id="scene-grid" width="16" height="16" patternUnits="userSpaceOnUse">
    <path d="M16 0H0V16" fill="none" stroke="#22394d" stroke-width="1"/>
  </pattern>
  <pattern id="track" width="32" height="8" patternUnits="userSpaceOnUse">
    <path d="M0 4H16" stroke="#69c8ba" stroke-width="2"/>
  </pattern>
</defs>
<g font-family="ui-monospace, Menlo, Consolas, monospace">
  {terminal_frame(c, 274, "taku0193@github: ~/motion-lab")}
  <text x="32" y="69" font-size="14" font-weight="700" fill="{c["teal"]}">$ whoami</text>
  <text x="30" y="124" font-size="57" font-weight="800" letter-spacing="-2" fill="{c["ink"]}">taku0193</text>
  <text x="32" y="158" font-size="25" font-weight="650" fill="{c["teal"]}">Motion. Rhythm. Code.</text>
  <text x="32" y="193" font-size="14" fill="{c["muted"]}">POSE TRACKING / INTERACTIVE GAMES</text>
  <text x="32" y="215" font-size="14" fill="{c["muted"]}">LIVE HEART-RATE TOOLS</text>
  <path d="M32 237H480" stroke="{c["edge"]}"/>
  <text x="32" y="256" font-size="11" letter-spacing="1.1" fill="{c["muted"]}">MOTION LAB</text>
  <rect x="512" y="51" width="363" height="202" rx="4" fill="#0c1422" stroke="#314a60"/>
  <rect x="513" y="52" width="361" height="182" fill="url(#scene-grid)"/>
  <text x="530" y="76" font-size="11" letter-spacing="1.2" fill="#a6bfd2">STAGE 01 / MOTION TRACK</text>
  <path d="M530 123h36l9-7h9l9 7h24l8 11 13-34 12 31 8-8h31l7-7h9l8 7h24l9 12 13-35 12 30 8-7h78"
        fill="none" stroke="#71efd4" stroke-width="2" opacity=".73"/>
  <path d="M513 223H875" stroke="#31546a" stroke-width="2"/>
  <rect x="513" y="229" width="361" height="8" fill="url(#track)"/>
  <path d="M542 200h36m-27 8h20m239-36h34m-44 8h20" stroke="#427687" stroke-width="2"/>
  <rect x="831" y="195" width="7" height="7" fill="#ffd585"/>
  <rect x="848" y="183" width="7" height="7" fill="#ff928d"/>
  {pixel_runner(683, 143, 5, THEMES["dark"])}
</g></svg>'''


def contribution_grid(days):
    dates = sorted(date.fromisoformat(day) for day in days)
    first, last = dates[0], dates[-1]
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = (last - sunday).days // 7 + 1
    cells = []
    for day in dates:
        offset = (day - sunday).days
        cells.append((offset // 7, offset % 7, day, days[day.isoformat()]))
    return weeks, cells


def runner_svg(data, theme):
    c = THEMES[theme]
    weeks, cells = contribution_grid(data["days"])
    first_x, first_y = 78, 114
    step = 744 / weeks
    rows = []
    for week, weekday, day, count in cells:
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 10 else 4
        color = c["blank"] if not level else c["levels"][level - 1]
        x = first_x + week * step
        y = first_y + weekday * 13
        rows.append(f'<rect x="{x:.2f}" y="{y}" width="{step - 3:.2f}" height="10" rx="1" fill="{color}"><title>{day}: {count} contributions</title></rect>')
    for i, label in ((1, "M"), (3, "W"), (5, "F")):
        rows.append(f'<text x="55" y="{first_y + i * 13 + 9}" font-size="11" fill="{c["muted"]}">{label}</text>')
    months = []
    for week, weekday, day, _ in cells:
        if day.day == 1:
            months.append(f'<text x="{first_x + week * step:.2f}" y="218" font-size="10" fill="{c["muted"]}">{day:%b}</text>')
    last_x = (weeks - 1) * step
    legend = "".join(f'<rect x="{739 + 15 * i}" y="235" width="11" height="10" fill="{color}"/>' for i, color in enumerate((c["blank"], *c["levels"])))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="265" viewBox="0 0 900 265" role="img" aria-labelledby="runner-title">
<title id="runner-title">Beat Runner — an animated pixel runner over {data["year_contributions"]} GitHub contributions</title>
<style>
.runner-scan {{animation: run-across 13s steps({max(1, weeks - 1)}, end) infinite}}
@keyframes run-across {{0% {{transform:translateX(0)}} 94%,100% {{transform:translateX({last_x:.3f}px)}}}}
@media (prefers-reduced-motion: reduce) {{.runner-scan {{animation:none}}}}
</style>
<g font-family="ui-monospace, Menlo, Consolas, monospace">
  {terminal_frame(c, 265, "taku0193@github: ~/contributions")}
  <text x="32" y="68" font-size="14" font-weight="700" fill="{c["teal"]}">$ ./beat-runner</text>
  <text x="868" y="68" text-anchor="end" font-size="13" fill="{c["muted"]}">{data["year_contributions"]:,} contributions / past year</text>
  <path d="M76 107H822" stroke="{c["edge"]}" stroke-width="1"/>
  {"".join(rows)}
  <g class="runner-scan">
    <rect x="{first_x - 1}" y="111" width="{step:.2f}" height="96" rx="2" fill="{c["teal"]}" opacity=".22"/>
    <path d="M{first_x + step/2:.2f} 105V202" stroke="{c["teal"]}" stroke-width="1" opacity=".65"/>
    {pixel_runner(first_x - 6, 77, 2, c)}
  </g>
  {"".join(months)}
  <text x="32" y="245" font-size="12" fill="{c["muted"]}">Contribution calendar / {data["period_end"]} UTC</text>
  <text x="730" y="244" text-anchor="end" font-size="11" fill="{c["muted"]}">Less</text>
  {legend}
  <text x="823" y="244" font-size="11" fill="{c["muted"]}">More</text>
</g></svg>'''


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('assets'))
    args = parser.parse_args()
    activity = json.loads((args.assets / 'activity-data.json').read_text(encoding='utf-8'))
    files = {}
    for theme in THEMES:
        files[f'header-{theme}.svg'] = hero_svg(theme)
        files[f'beat-runner-{theme}.svg'] = runner_svg(activity, theme)
    for svg in files.values():
        ET.fromstring(svg)
    for name, svg in files.items():
        (args.assets / name).write_text(svg, encoding='utf-8')
    print(f"Rendered Motion Lab and Beat Runner for {activity['period_end']} UTC.")


if __name__ == '__main__':
    main()
