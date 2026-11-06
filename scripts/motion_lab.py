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
    trace = "M530 123h36l9-7h9l9 7h24l8 11 13-34 12 31 8-8h31l7-7h9l8 7h24l9 12 13-35 12 30 8-7h78"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="274" viewBox="0 0 900 274" role="img" aria-labelledby="hero-title">
<title id="hero-title">taku0193 — Motion. Rhythm. Code.</title>
<style>
.trace-light {{stroke-dasharray:11 89; animation:trace 2.8s linear infinite}}
.pulse-stride {{animation:stride 2.8s steps(1,end) infinite}}
@keyframes trace {{to {{stroke-dashoffset:-100}}}}
@keyframes stride {{
  0%, 44%, 79%, 100% {{transform:translateY(0)}}
  34% {{transform:translateY(-4px)}}
  69% {{transform:translateY(-3px)}}
}}
@media (prefers-reduced-motion: reduce) {{
  .trace-light {{display:none}}
  .pulse-stride {{animation:none}}
}}
</style>
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
  <path d="{trace}" fill="none" stroke="#71efd4" stroke-width="2" opacity=".53"/>
  <path class="trace-light" d="{trace}" pathLength="100" fill="none" stroke="#9effec" stroke-width="3"/>
  <path d="M513 223H875" stroke="#31546a" stroke-width="2"/>
  <rect x="513" y="229" width="361" height="8" fill="url(#track)"/>
  <path d="M542 200h36m-27 8h20m239-36h34m-44 8h20" stroke="#427687" stroke-width="2"/>
  <rect x="831" y="195" width="7" height="7" fill="#ffd585"/>
  <rect x="848" y="183" width="7" height="7" fill="#ff928d"/>
  <g class="pulse-stride">{pixel_runner(683, 143, 5, THEMES["dark"])}</g>
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


def drink(x, y, color, rim):
    return f'''<g transform="translate({x:.2f} {y:.2f})" shape-rendering="crispEdges">
<path d="M1 0h5v1h1v7H6v1H1V8H0V1h1z" fill="{color}"/>
<path d="M1 0h5v1H1zm0 8h5v1H1z" fill="{rim}"/>
<path d="M4 2 2 5h2L3 7l3-3H4z" fill="#102138"/>
</g>'''


def ordered_pickups(active_by_week, start_y):
    """Sweep each active week in one direction and finish at the newest day."""
    weeks = [week for week in active_by_week if week]
    if not weeks:
        return []
    # Try both directions per week, including the lane change into the next week.
    choices = [(0, weeks[-1])]
    for week in reversed(weeks[:-1]):
        next_choices = []
        for sweep in (week, week[::-1]):
            cost, rest = min(
                ((cost + abs(sweep[-1][1] - rest[0][1]), rest) for cost, rest in choices),
                key=lambda option: option[0],
            )
            next_choices.append((cost, sweep + rest))
        choices = next_choices
    return min(choices, key=lambda option: option[0] + abs(start_y - option[1][0][1]))[1]


def pickup_animation(pickups, start, week_width):
    """Sweep the calendar, then return to the center for a recharge."""
    if not pickups:
        return "", [], []
    x, y = start
    elapsed = 0.0
    waypoints = []
    arrivals = []

    def move(next_x, next_y, speed):
        nonlocal x, y, elapsed
        distance = abs(next_x - x) + abs(next_y - y)
        if distance:
            elapsed += distance / speed
            x, y = next_x, next_y
            waypoints.append((elapsed, x, y))

    for target_x, target_y, _, _, _ in pickups:
        if target_x > x:
            gate = max(x, target_x - week_width / 2)
            gap = gate - x
            move(gate, y, 105 + min(gap, 400) * .65)
            move(gate, target_y, 125)
        move(target_x, target_y, 115)
        arrivals.append(elapsed)
        elapsed += .10
        waypoints.append((elapsed, x, y))

    play_time = min(35, max(6, elapsed))
    return_time = 1.1 + abs(x - 450) / 500
    recovery_start = play_time + return_time
    recovery_end = recovery_start + 1.65
    duration = recovery_end + .25

    def percent(seconds):
        return 100 * seconds / duration

    def course_percent(seconds):
        return percent(play_time * seconds / elapsed)

    frames = [f"0% {{transform:translate({start[0]}px,{start[1]}px);opacity:0}}", "2% {opacity:1}"]
    for at, x, y in waypoints:
        frames.append(f"{course_percent(at):.4f}% {{transform:translate({x:.2f}px,{y:.2f}px)}}")
    frames.extend([
        f"{percent(play_time + .23):.4f}% {{transform:translate({x:.2f}px,205px)}}",
        f"{percent(recovery_start - .25):.4f}% {{transform:translate(450px,205px)}}",
        f"{percent(recovery_start):.4f}% {{transform:translate(450px,154px)}}",
        f"{percent(recovery_end):.4f}% {{opacity:1}}",
        "100% {transform:translate(450px,154px);opacity:0}",
    ])
    effects, cans, sparks = [], [], []
    for index, ((x, y, color, day, count), at) in enumerate(zip(pickups, arrivals)):
        position = course_percent(at)
        flash_end = min(99, position + (4 if index == len(pickups) - 1 else 1.6))
        effects.extend([
            f".can-{index} {{animation:take-{index} {duration:.4f}s step-end infinite}}",
            f"@keyframes take-{index} {{0% {{opacity:1}} {position:.4f}%,100% {{opacity:0}}}}",
            f".spark-{index} {{animation:flash-{index} {duration:.4f}s linear infinite}}",
            f"@keyframes flash-{index} {{0%,{max(0, position-.02):.4f}% {{opacity:0}} {position:.4f}% {{opacity:1}} {flash_end:.4f}%,100% {{opacity:0}}}}",
        ])
        cans.append(f'<g class="pickup-can can-{index}"><title>{day}: {count} contributions</title>{drink(x-3.5, y-4.5, color, "#b0cadf")}</g>')
        sparks.append(f'<path class="pickup-spark spark-{index}" d="M{x-6:.2f} {y-6:.2f}l-3 -3m14 3 3 -3m-1 14 3 3" fill="none" stroke="#ffd585" stroke-width="1.5" opacity="0"/>')
    recovery_in = percent(recovery_start)
    recovery_visible = percent(recovery_start + .18)
    recovery_out = percent(recovery_end)
    effects.extend([
        f".pickup-runner {{animation:collect-route {duration:.4f}s linear infinite}}",
        f"@keyframes collect-route {{{''.join(frames)}}}",
        f".recovery {{animation:recovery {duration:.4f}s linear infinite}}",
        f"@keyframes recovery {{0%,{recovery_in:.4f}% {{opacity:0}} {recovery_visible:.4f}%,{recovery_out:.4f}% {{opacity:1}} 100% {{opacity:0}}}}",
        f".heal-plus {{animation:heal-plus {duration:.4f}s linear infinite}}",
        f"@keyframes heal-plus {{0%,{recovery_visible:.4f}% {{opacity:0;transform:translateY(4px)}} {percent(recovery_start+.45):.4f}% {{opacity:1}} {percent(recovery_start+1.25):.4f}%,100% {{opacity:0;transform:translateY(-9px)}}}}",
    ])
    for index in range(4):
        fill_at = percent(recovery_start + .36 + .28 * index)
        effects.extend([
            f".charge-{index} {{animation:charge-{index} {duration:.4f}s step-end infinite}}",
            f"@keyframes charge-{index} {{0% {{opacity:0}} {fill_at:.4f}%,100% {{opacity:1}}}}",
        ])
    return "\n".join(effects), cans, sparks


def runner_svg(data, theme):
    c = THEMES[theme]
    weeks, cells = contribution_grid(data["days"])
    first_x, first_y = 78, 114
    step = 744 / weeks
    rows = []
    active_by_week = [[] for _ in range(weeks)]
    for week, weekday, day, count in cells:
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 10 else 4
        x = first_x + week * step
        y = first_y + weekday * 13
        rows.append(f'<rect x="{x:.2f}" y="{y}" width="{step - 3:.2f}" height="10" rx="1" fill="{c["blank"]}"><title>{day}: {count} contributions</title></rect>')
        if level:
            active_by_week[week].append((x + (step - 3) / 2, y + 5, c["levels"][level - 1], day, count))
    start = (first_x - 13, first_y + 5)
    route = ordered_pickups(active_by_week, start[1])
    animation, cans, sparks = pickup_animation(route, start, step)
    for i, label in ((1, "M"), (3, "W"), (5, "F")):
        rows.append(f'<text x="55" y="{first_y + i * 13 + 9}" font-size="11" fill="{c["muted"]}">{label}</text>')
    months = []
    for week, weekday, day, _ in cells:
        if day.day == 1:
            months.append(f'<text x="{first_x + week * step:.2f}" y="218" font-size="10" fill="{c["muted"]}">{day:%b}</text>')
    legend = "".join(f'<rect x="{739 + 15 * i}" y="235" width="11" height="10" fill="{color}"/>' for i, color in enumerate((c["blank"], *c["levels"])))
    charge = "".join(
        f'<rect x="{427 + i * 12}" y="171" width="10" height="7" rx="1" fill="{c["blank"]}"/>'
        f'<rect class="charge-{i}" x="{427 + i * 12}" y="171" width="10" height="7" rx="1" fill="{c["teal"]}" opacity="0"/>'
        for i in range(4)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="265" viewBox="0 0 900 265" role="img" aria-labelledby="runner-title">
<title id="runner-title">Beat Runner — collect energy drinks and recharge after {data["year_contributions"]} GitHub contributions</title>
<style>
{animation}
@media (prefers-reduced-motion: reduce) {{
  .pickup-runner, .pickup-can, .pickup-spark, .recovery {{animation:none}}
}}
</style>
<g font-family="ui-monospace, Menlo, Consolas, monospace">
  {terminal_frame(c, 265, "taku0193@github: ~/contributions")}
  <text x="32" y="68" font-size="14" font-weight="700" fill="{c["teal"]}">$ ./beat-runner</text>
  <text x="868" y="68" text-anchor="end" font-size="13" fill="{c["muted"]}">{data["year_contributions"]:,} contributions / past year</text>
  <path d="M76 107H822" stroke="{c["edge"]}" stroke-width="1"/>
  {"".join(rows)}
  {"".join(cans)}
  {"".join(sparks)}
  <g class="recovery" opacity="0">
    <rect x="397" y="111" width="106" height="78" rx="7" fill="{c["body"]}" stroke="{c["teal"]}"/>
    <text x="450" y="129" text-anchor="middle" font-size="10" font-weight="700" letter-spacing="1" fill="{c["teal"]}">RECOVERY</text>
    <g class="heal-plus" fill="{c["teal"]}" opacity="0" shape-rendering="crispEdges">
      <path d="M426 145h2v3h3v2h-3v3h-2v-3h-3v-2h3z"/>
      <path d="M474 141h2v3h3v2h-3v3h-2v-3h-3v-2h3z"/>
    </g>
    {charge}
  </g>
  <g class="pickup-runner" style="transform:translate({start[0]}px,{start[1]}px)">{pixel_runner(-9, -16, 1.4, c)}</g>
  {"".join(months)}
  <text x="32" y="245" font-size="12" fill="{c["muted"]}">Contribution calendar / {data["period_end"]} UTC</text>
  <text x="455" y="245" text-anchor="middle" font-size="11" fill="{c["muted"]}">1 active day = 1 can</text>
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
