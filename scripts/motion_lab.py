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
STRIDE_SPRITE = SPRITE[:6] + (
    "...TTTTTT...",
    "..WW.TTTWW..",
    ".....TT.....",
    "....CCCT....",
    "....CC.CC...",
    ".....CC..CC.",
    ".....WCC..W.",
    "....WW...WW.",
)

POSE_LINKS = (
    ("head", "shoulder", "hip"),
    ("wrist_back", "elbow_back", "shoulder", "elbow_front", "wrist_front"),
    ("ankle_back", "knee_back", "hip", "knee_front", "ankle_front"),
)
RUN_JOINTS = {
    "head": (6, 2), "shoulder": (6, 6), "hip": (5, 9),
    "elbow_back": (3, 6), "wrist_back": (2, 7),
    "elbow_front": (8, 7), "wrist_front": (10, 8),
    "knee_back": (3, 11), "ankle_back": (2, 13),
    "knee_front": (8, 11), "ankle_front": (10, 13),
}
STRIDE_JOINTS = dict(
    RUN_JOINTS, elbow_front=(8, 6), wrist_front=(9, 7),
    knee_back=(6, 12), ankle_back=(5, 13), knee_front=(8, 10),
)


def pixel_runner(x, y, size, colors, pose=SPRITE):
    palette = {"Y": colors["amber"], "W": colors["ink"], "T": colors["teal"], "C": colors["coral"]}
    pixels = []
    for row, line in enumerate(pose):
        for col, char in enumerate(line):
            if char != ".":
                pixels.append(f'<rect x="{col * size}" y="{row * size}" width="{size}" height="{size}" fill="{palette[char]}"/>')
    return f'<g transform="translate({x} {y})" shape-rendering="crispEdges">{"".join(pixels)}</g>'


def pose_overlay(x, y, size, joints):
    """Draw the landmarks in the same pixel coordinates as the stride sprite."""
    points = {
        name: (x + (col + .5) * size, y + (row + .5) * size)
        for name, (col, row) in joints.items()
    }
    paths = " ".join(
        "M" + " ".join(f"{px:g},{py:g}" for px, py in (points[name] for name in chain))
        for chain in POSE_LINKS
    )
    dots = "".join(
        f'<circle cx="{px:g}" cy="{py:g}" r="1.45"/>'
        for px, py in points.values()
    )
    return f'''<g class="pose-scan" opacity="0" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="{paths}" stroke="#0a1722" stroke-width="2.6"/>
  <path d="{paths}" stroke="#9df7ee" stroke-width="1.15"/>
  <g fill="#c8fff6" stroke="#0a1722" stroke-width=".65">{dots}</g>
</g>'''


def terminal_frame(colors, height, label):
    return f'''
<rect x=".5" y=".5" width="899" height="{height-1}" rx="10" fill="{colors["body"]}" stroke="{colors["edge"]}"/>
<path d="M10 1H890Q899 1 899 10V34H1V10Q1 1 10 1Z" fill="{colors["bar"]}"/>
<path d="M1 34H899" stroke="{colors["edge"]}"/>
<rect x="16" y="15" width="6" height="6" fill="{colors["coral"]}"/>
<rect x="28" y="15" width="6" height="6" fill="{colors["amber"]}"/>
<rect x="40" y="15" width="6" height="6" fill="{colors["teal"]}"/>
<text x="59" y="22" font-size="13" fill="{colors["muted"]}">{escape(label)}</text>'''


def footstep_light(x, y, delay, color):
    """Leave a lit tile under the planted shoe and send a pulse down the lane."""
    return f'''<g transform="translate({x:.2f} {y:g})" fill="{color}" style="--beat-delay:{delay:.6f}s">
  <g class="beat-contact" opacity="0">
    <rect x="-8" y="-1" width="16" height="5" opacity=".24"/>
    <rect x="-4.5" y="0" width="9" height="2.5"/>
    <path d="M-7-3h2v2h-2zM5-3h2v2H5z" opacity=".66"/>
  </g>
  <g class="beat-ray" opacity="0">
    <path d="M-6 11h10v2H-6zM7 11h6v2H7zM16 11h3v2h-3z"/>
    <path d="M-7 13h28v1H-7z" opacity=".3"/>
  </g>
</g>'''


def ballpark_scene():
    """Night baseball park viewed from the near side of the warm-up lane."""
    spectators = []
    crowd_colors = ("#527888", "#7a8f93", "#977b68", "#43667c", "#a1a98d")
    for row in range(3):
        for column in range(59):
            x = 5 + column * 6
            # The bowl drops toward the center of the picture.
            y = 67 + row * 5 + round(13 * ((x - 180) / 180) ** 2)
            if column % 10 != 9 and (column * 3 + row * 7) % 11 < 8:
                color = crowd_colors[(column + row * 2) % len(crowd_colors)]
                spectators.append(f'<rect x="{x}" y="{y}" width="2" height="2" fill="{color}"/>')

    return f'''<defs>
      <linearGradient id="ballpark-sky" x2="0" y2="1">
        <stop stop-color="#0b1527"/><stop offset="1" stop-color="#20394b"/>
      </linearGradient>
      <radialGradient id="ballpark-lamp-glow">
        <stop stop-color="#e8f4c4" stop-opacity=".34"/>
        <stop offset="1" stop-color="#e8f4c4" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="ballpark-beam" x2="0" y2="1">
        <stop stop-color="#f0f3d1" stop-opacity=".17"/>
        <stop offset="1" stop-color="#f0f3d1" stop-opacity="0"/>
      </linearGradient>
      <path id="ballpark-turf" d="M0 109 37 98 83 90 132 85 180 84 229 85 278 90 324 98 361 109V154H0Z"/>
      <clipPath id="ballpark-grass-clip"><use href="#ballpark-turf"/></clipPath>
      <g id="ballpark-light-tower" shape-rendering="crispEdges">
        <path d="M-12 49 -3 7H3l9 42Z" fill="#223f4d"/>
        <path d="M-7 38H7M-5 29H5M-4 20H4M-7 38l11-18M7 38-4 20" fill="none" stroke="#406071"/>
        <rect x="-17" y="-6" width="34" height="13" fill="#182d3d" stroke="#70858a"/>
        <path d="M-14-3h4v3h-4zm6 0h4v3h-4zm6 0h4v3h-4zm6 0h4v3H4zm6 0h4v3h-4zM-14 2h4v2h-4zm6 0h4v2h-4zm6 0h4v2h-4zm6 0h4v2H4zm6 0h4v2h-4z" fill="#f2f1c9"/>
      </g>
    </defs>
    <rect width="361" height="200" fill="url(#ballpark-sky)"/>
    <path d="M120 40h2v2h-2zm33-6h1v1h-1zm44 11h2v1h-2zm22-13h1v2h-1zm46 10h2v2h-2z" fill="#a5bbc3" opacity=".49"/>
    <circle cx="278" cy="24" r="7" fill="#d7ddbc"/>
    <circle cx="281" cy="21" r="7" fill="#0d172a"/>

    <ellipse cx="47" cy="42" rx="43" ry="27" fill="url(#ballpark-lamp-glow)"/>
    <ellipse cx="315" cy="41" rx="43" ry="27" fill="url(#ballpark-lamp-glow)"/>
    <use href="#ballpark-light-tower" x="47" y="42"/>
    <use href="#ballpark-light-tower" x="315" y="41"/>

    <path d="M0 75 36 66 86 58 134 55 181 54 228 55 276 58 326 66 361 75V113H0Z" fill="#152938"/>
    <path d="M0 76 36 67 86 60 134 57 181 56 228 57 276 60 326 67 361 76" fill="none" stroke="#3c5968" stroke-width="2"/>
    <path d="M0 83Q180 51 361 83M0 88Q180 56 361 88M0 93Q180 61 361 93M0 98Q180 66 361 98" fill="none" stroke="#36505e" stroke-width="1.15"/>
    <g shape-rendering="crispEdges" opacity=".72">{"".join(spectators)}</g>
    <path d="M0 102 37 91 83 82 132 78 180 77 229 78 278 82 324 91 361 102v9l-37-10-46-9-49-5-49-1-48 1-49 5-46 9-37 10z" fill="#264744"/>
    <path d="M0 102 37 91 83 82 132 78 180 77 229 78 278 82 324 91 361 102" fill="none" stroke="#79a293" stroke-width="1.35"/>
    <path d="M37 92v6m46-15v7m49-11v6m48-7v6m49-5v6m49-2v7m46 2v6" stroke="#5a7b74"/>

    <use href="#ballpark-turf" fill="#284337"/>
    <g clip-path="url(#ballpark-grass-clip)" fill="#355747">
      <path d="M-5 91 38 84 2 154h-61zM74 84h38l-9 70H56zM148 82h30l26 72h-48zM212 82h34l62 72h-52zM288 83l36 6 71 65h-49z"/>
    </g>
    <path d="M109 120 136 100 157 94 180 92 204 94 225 100 251 120 195 150h-29z" fill="#724d37"/>
    <path d="m180 107 42 17-42 18-42-18z" fill="#345646"/>
    <path d="m180 142 11 5-1 7h-20l-1-7z" fill="#80553b"/>
    <path d="M22 84 180 148 339 84" fill="none" stroke="#e0cda6" stroke-width="1.15" opacity=".85"/>
    <ellipse cx="180" cy="124" rx="9" ry="3.6" fill="#8b6546"/>
    <path d="M177.5 123h5v1h-5z" fill="#f1dec0"/>
    <path d="m180 98 4 2-4 2-4-2zm-55 23 5 2-5 2-5-2zm110 0 5 2-5 2-5-2zm-58 24h6v2l-3 2-3-2z" fill="#fff2d7"/>

    <path d="M32 45H62l86 107H0ZM301 44h29l31 108h-148z" fill="url(#ballpark-beam)"/>
    <rect y="154" width="361" height="46" fill="#302521"/>
    <path d="M0 154.5H361" stroke="#886549"/>
    <path d="M0 160H361" stroke="#a3856a" stroke-opacity=".55"/>
    <path d="M0 189.5H361" stroke="#564132"/>
    <path d="M12 164h2m10 21h3m56-22h3m18 24h4m16-20h2m35 16h2m43-17h3m47 20h2m34-20h3m30 17h2m28-20h3" stroke="#8b6a53" stroke-opacity=".5"/>'''


def hero_svg(theme):
    """A night ballpark with a lit scoreboard and a runner warm-up lane."""
    c = THEMES[theme]
    scene_x = 513
    scene_width = 361
    gate_x = 693
    gate_exit = gate_x + 39
    runner_x, runner_y, pixel_size = 466, 170, 3
    road_y = runner_y + len(SPRITE) * pixel_size
    travel, lap_seconds = 438, 8.4
    shoulder_x = runner_x + (RUN_JOINTS["shoulder"][0] + .5) * pixel_size
    scan_enter, scan_lock, scan_release, scan_exit = (
        100 * (gate_x + offset - shoulder_x) / travel
        for offset in (-39, -22, 22, 39)
    )
    gate_local = gate_x - scene_x
    scan_a = pose_overlay(runner_x, runner_y, pixel_size, RUN_JOINTS)
    scan_b = pose_overlay(runner_x, runner_y, pixel_size, STRIDE_JOINTS)
    runner_colors = THEMES["dark"]
    outfits = (
        runner_colors,
        dict(runner_colors, teal="#ffb782", coral="#79d7f7", amber="#f1a9bf"),
        dict(runner_colors, teal="#c6adf4", coral="#ff9b9f", amber="#a1ecc5"),
    )
    runners = []
    runner_styles = []
    footsteps = []
    # Each cadence divides a full pass, so the planted foot and its light stay
    # on the same clock when the runner wraps around the scene.
    for index, (outfit, offset, rest_x, strides) in enumerate(
        zip(outfits, (1.7, 4.5, 7.3), (88, 212, 318), (20, 15, 24)), 1
    ):
        stride_seconds = lap_seconds / strides
        runner_styles.append(
            f".runner-{index} {{--run-offset:-{offset}s;--stride-time:{stride_seconds:g}s;"
            f"transform:translateX({rest_x}px)}}"
        )
        runners.append(f'''<g class="track-runner runner-{index}">
    <rect x="472" y="212" width="26" height="2" fill="#07121c" opacity=".7"/>
    <g class="pulse-stride">
      <g class="step-a">{pixel_runner(runner_x, runner_y, pixel_size, outfit)}{scan_a}</g>
      <g class="step-b">{pixel_runner(runner_x, runner_y, pixel_size, outfit, STRIDE_SPRITE)}{scan_b}</g>
    </g>
  </g>''')
        for step_index in range(2 * strides):
            at = step_index * stride_seconds / 2
            distance = travel * at / lap_seconds
            # The front shoes occupy columns 10–11 in pose A and 9–10 in B.
            foot_col = 11 if step_index % 2 == 0 else 10
            foot_x = runner_x + foot_col * pixel_size + distance
            if shoulder_x + distance >= gate_exit and foot_x < scene_x + scene_width:
                delay = -((offset - at) % lap_seconds)
                footsteps.append(footstep_light(foot_x, road_y, delay, outfit["teal"]))
    runner_css = "\n".join(runner_styles)
    lane_x = gate_exit - scene_x + 5
    lane_tiles = "".join(
        f'<rect x="{x}" y="172" width="7" height="2" fill="#735344"/>'
        for x in range(lane_x, scene_width - 7, 12)
    )
    trace = "M338 205h19l4-3 4 3h10l4 5 6-14 6 16 5-7h13l4-3 4 3h9l4 5 6-14 6 16 5-7h17"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="274" viewBox="0 0 900 274" role="img" aria-labelledby="hero-title hero-desc">
<title id="hero-title">taku0193 — Motion. Rhythm. Code.</title>
<desc id="hero-desc">A night baseball stadium with taku0193 on its scoreboard. Three runners cross a motion capture gate and send pulses of light down the warm-up lane.</desc>
<style>
.trace-light {{stroke-dasharray:9 91; animation:trace 3.2s linear infinite}}
.track-runner {{animation:pass-through {lap_seconds}s linear infinite;animation-delay:var(--run-offset)}}
{runner_css}
.pose-scan {{animation:scan-pose {lap_seconds}s linear infinite;animation-delay:var(--run-offset)}}
.pulse-stride {{animation:stride var(--stride-time) ease-in-out infinite;animation-delay:var(--run-offset)}}
.step-a {{animation:step-a var(--stride-time) step-end infinite;animation-delay:var(--run-offset)}}
.step-b {{opacity:0;animation:step-b var(--stride-time) step-end infinite;animation-delay:var(--run-offset)}}
.beat-contact {{animation:beat-contact {lap_seconds}s linear infinite;animation-delay:var(--beat-delay)}}
.beat-ray {{animation:beat-ray {lap_seconds}s ease-out infinite;animation-delay:var(--beat-delay)}}
@keyframes pass-through {{from {{transform:translateX(0)}} to {{transform:translateX({travel}px)}}}}
@keyframes scan-pose {{
  0%,{scan_enter:.4f}% {{opacity:0}}
  {scan_lock:.4f}%,{scan_release:.4f}% {{opacity:1}}
  {scan_exit:.4f}%,100% {{opacity:0}}
}}
@keyframes step-a {{0%,100% {{opacity:1}} 50% {{opacity:0}}}}
@keyframes step-b {{0%,100% {{opacity:0}} 50% {{opacity:1}}}}
@keyframes trace {{to {{stroke-dashoffset:-100}}}}
@keyframes stride {{0%,50%,100% {{transform:translateY(0)}} 25%,75% {{transform:translateY(-1px)}}}}
@keyframes beat-contact {{
  0% {{opacity:1}}
  {.19 / lap_seconds * 100:.4f}%,100% {{opacity:0}}
}}
@keyframes beat-ray {{
  0% {{opacity:0;transform:translateX(0)}}
  {.045 / lap_seconds * 100:.4f}% {{opacity:.82;transform:translateX(4px)}}
  {.29 / lap_seconds * 100:.4f}%,100% {{opacity:0;transform:translateX(20px)}}
}}
@media (prefers-reduced-motion: reduce) {{
  .trace-light {{display:none}}
  .track-runner, .pulse-stride, .step-a, .step-b, .pose-scan,
  .beat-contact, .beat-ray {{animation:none}}
}}
</style>
<defs>
  <clipPath id="hero-scene-clip"><rect x="513" y="52" width="361" height="200"/></clipPath>
  <clipPath id="stadium-frame"><rect x="25" y="52" width="849" height="200" rx="5"/></clipPath>
  <clipPath id="runner-track"><rect x="513" y="156" width="361" height="60"/></clipPath>
  <pattern id="scoreboard-leds" width="5" height="5" patternUnits="userSpaceOnUse">
    <rect x="1" y="1" width="1" height="1" fill="#75c1b8" opacity=".14"/>
  </pattern>
</defs>
<g font-family="ui-monospace, Menlo, Consolas, monospace">
  {terminal_frame(c, 274, "taku0193@github: ~/motion-lab")}
  <g clip-path="url(#stadium-frame)">
  <rect x="25" y="52" width="849" height="200" fill="#0c1726"/>
  <path d="M25 127H513V154H25Z" fill="#152938"/>
  <path d="M25 128H513" stroke="#3c5968" stroke-width="2"/>
  <path d="M25 154H513V163H25Z" fill="#264744"/>
  <path d="M25 154H513" stroke="#79a293" stroke-width="1.35"/>
  <path d="M25 163H513V206H25Z" fill="#284337"/>
  <path d="M25 206H513V252H25Z" fill="#302521"/>
  <path d="M25 206.5H513" stroke="#886549"/>
  <path d="M25 212H513" stroke="#a3856a" opacity=".55"/>
  <path d="M25 241.5H513" stroke="#564132"/>
  <g clip-path="url(#hero-scene-clip)"><g transform="translate({scene_x} 52)">
    {ballpark_scene()}
    {lane_tiles}
    <g transform="translate({gate_local} 0)">
      <rect x="-39" y="108" width="78" height="55" fill="#71efd4" opacity=".055"/>
      <path d="M-39 121v-13h11m56 0h11v13m0 29v13h-11m-56 0h-11v-13"
            fill="none" stroke="#71efd4" stroke-width="1.2" opacity=".72"/>
      <path d="M-39 124v24m78-24v24" fill="none" stroke="#71efd4"
            stroke-dasharray="1 4" opacity=".5"/>
      <text x="0" y="193" text-anchor="middle" font-size="8" letter-spacing="1.35" fill="#91d6c9">POSE GATE</text>
    </g>
    <text x="16" y="23" font-size="10" letter-spacing="1.1" fill="#c4d7d8">STAGE 01 / NIGHT GAME</text>
    <text x="345" y="193" text-anchor="end" font-size="8" letter-spacing="1.6" fill="#c0d3c8">BEAT TRACK</text>
  </g></g>
  <g aria-label="Stadium scoreboard">
    <path d="M66 207h13v37H66zm385 0h13v37h-13z" fill="#15252d"/>
    <rect x="37" y="62" width="460" height="167" rx="5" fill="#070e17" stroke="#435964" stroke-width="2"/>
    <rect x="44" y="69" width="446" height="100" rx="2" fill="#101e2a"/>
    <rect x="44" y="69" width="446" height="100" rx="2" fill="url(#scoreboard-leds)"/>
    <path d="M44 174H490M326 181V220" stroke="#34505c"/>
    <rect x="56" y="80" width="4" height="4" fill="#ffd585"/>
    <text x="67" y="85" font-size="10" letter-spacing="1.65" fill="#a6bfd2">MOTION LAB FIELD</text>
    <text x="56" y="133" font-size="53" font-weight="800" letter-spacing="-2" fill="#f0f7ff">taku0193</text>
    <text x="58" y="158" font-size="23" font-weight="650" fill="#89efd6">Motion. Rhythm. Code.</text>
    <text x="56" y="194" font-size="12" fill="#b7cad6">POSE TRACKING / INTERACTIVE GAMES</text>
    <text x="56" y="214" font-size="12" fill="#b7cad6">LIVE HEART-RATE TOOLS</text>
    <path d="{trace}" fill="none" stroke="#5d9e9d" stroke-width="1.4" opacity=".55"/>
    <path class="trace-light" d="{trace}" pathLength="100" fill="none" stroke="#a1f4de" stroke-width="1.7"/>
  </g>
  <g clip-path="url(#hero-scene-clip)" aria-hidden="true">{''.join(footsteps)}</g>
  <g clip-path="url(#runner-track)">{''.join(runners)}</g>
  </g>
  <rect x="25" y="52" width="849" height="200" rx="5" fill="none" stroke="#50616a"/>
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


STAND_SPRITE = SPRITE[:6] + (
    '....TTTTT...',
    '...W.TTT.W..',
    '...W.TTT.W..',
    '....CCCCC...',
    '....CC.CC...',
    '....CC.CC...',
    '....WW.WW...',
    '...WWW.WWW..',
)
DRINK_SPRITE = SPRITE[:6] + (
    '....TTTTT...',
    '...W.TTT....',
    '...W.TTT....',
    '....CCCCC...',
    '....CC.CC...',
    '....CC.CC...',
    '....WW.WW...',
    '...WWW.WWW..',
)


def pickup_timeline(pickups, start, week_width):
    """One clock drives the route, pickups, poses and the final pit stop."""
    if not pickups:
        return None
    x, y = start
    elapsed = 0.0
    waypoints = [(0.0, x, y)]
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
            move(gate, y, 105 + min(gate - x, 400) * .65)
            move(gate, target_y, 125)
        move(target_x, target_y, 115)
        arrivals.append(elapsed)
        elapsed += .10
        waypoints.append((elapsed, x, y))

    play = min(38, max(7, elapsed))
    scale = play / elapsed
    waypoints = [(at * scale, px, py) for at, px, py in waypoints]
    arrivals = [at * scale for at in arrivals]
    recovery = play + 1.7 + abs(x - 450) / 550
    waypoints.extend([
        (play + .35, x, 205),
        (recovery - .65, 450, 205),
        (recovery, 450, 162),
    ])
    drink_start = recovery + .30
    drink_end = drink_start + 1.40
    breathe_end = drink_end + 1.55
    ready_end = breathe_end + .65
    duration = ready_end + .45
    waypoints.append((duration, 450, 162))
    return dict(waypoints=waypoints, arrivals=arrivals, play=play,
                recovery=recovery, drink_start=drink_start, drink_end=drink_end,
                breathe_end=breathe_end, ready_end=ready_end, duration=duration,
                return_left=x > 450)


def pickup_animation(pickups, start, week_width):
    timeline = pickup_timeline(pickups, start, week_width)
    if timeline is None:
        return '', [], [], None
    t = timeline
    duration = t['duration']

    def pct(at):
        return f'{100 * at / duration:.5f}%'

    frames = []
    for at, x, y in t['waypoints']:
        easing = ';animation-timing-function:ease-out' if abs(at - (t['recovery'] - .65)) < .0001 else ''
        frames.append(f'{pct(at)} {{transform:translate({x:.3f}px,{y:.3f}px){easing}}}')
    effects = [
        f'.pickup-runner,.trail-route {{animation:collect-route {duration:.5f}s linear infinite}}',
        f'@keyframes collect-route {{{"".join(frames)}}}',
        f'.runner-presence {{animation:runner-presence {duration:.5f}s linear infinite}}',
        f'@keyframes runner-presence {{0% {{opacity:0}} {pct(.18)},{pct(t["ready_end"])} {{opacity:1}} 100% {{opacity:0}}}}',
        f'.trail-window {{animation:trail-window {duration:.5f}s linear infinite}}',
        f'@keyframes trail-window {{0%,{pct(.25)} {{opacity:0}} {pct(.35)},{pct(t["play"])} {{opacity:.16}} {pct(t["play"]+.20)},100% {{opacity:0}}}}',
        '.trail-1 {animation-delay:.10s}.trail-2 {animation-delay:.20s;opacity:.5}',
        f'.run-pose {{animation:run-pose {duration:.5f}s step-end infinite}}',
        f'@keyframes run-pose {{0% {{opacity:1}} {pct(t["recovery"])},100% {{opacity:0}}}}',
        f'.stand-pose {{animation:stand-pose {duration:.5f}s step-end infinite}}',
        f'@keyframes stand-pose {{0% {{opacity:0}} {pct(t["recovery"])} {{opacity:1}} {pct(t["drink_start"])} {{opacity:0}} {pct(t["drink_end"])},100% {{opacity:1}}}}',
        f'.drink-pose {{animation:drink-pose {duration:.5f}s step-end infinite}}',
        f'@keyframes drink-pose {{0% {{opacity:0}} {pct(t["drink_start"])} {{opacity:1}} {pct(t["drink_end"])},100% {{opacity:0}}}}',
        f'.avatar-size {{animation:avatar-size {duration:.5f}s ease-out infinite}}',
        f'@keyframes avatar-size {{0%,{pct(t["recovery"]-.2)} {{transform:scale(1)}} {pct(t["recovery"]+.22)},100% {{transform:scale(1.65)}}}}',
        f'.sip-arm {{transform-origin:2px -13px;animation:sip {duration:.5f}s ease-in-out infinite}}',
        f'@keyframes sip {{0%,{pct(t["drink_start"])} {{transform:rotate(35deg)}} {pct(t["drink_start"]+.38)},{pct(t["drink_end"]-.34)} {{transform:rotate(-6deg)}} {pct(t["drink_end"])},100% {{transform:rotate(35deg)}}}}',
        f'.breathing {{animation:breathing {duration:.5f}s ease-in-out infinite}}',
        f'@keyframes breathing {{0%,{pct(t["drink_end"])} {{transform:scaleY(1)}} {pct(t["drink_end"]+.48)} {{transform:scaleY(1.045)}} {pct(t["drink_end"]+1.05)} {{transform:scaleY(.985)}} {pct(t["breathe_end"])},100% {{transform:scaleY(1)}}}}',
    ]
    if t['return_left']:
        effects.extend([
            f'.runner-facing {{animation:runner-facing {duration:.5f}s step-end infinite}}',
            f'@keyframes runner-facing {{0% {{transform:scaleX(1)}} {pct(t["play"]+.35)} {{transform:scaleX(-1)}} {pct(t["recovery"])},100% {{transform:scaleX(1)}}}}',
        ])
    cans, sparks = [], []
    combo = 0
    for index, ((x, y, color, day, count), at) in enumerate(zip(pickups, t['arrivals'])):
        combo = combo + 1 if index and at - t['arrivals'][index - 1] <= .65 else 1
        strength = 1 + min(combo - 1, 4) * .13
        effects.extend([
            f'.can-{index} {{animation:take-{index} {duration:.5f}s step-end infinite}}',
            f'@keyframes take-{index} {{0% {{opacity:1}} {pct(at)},100% {{opacity:0}}}}',
            f'.spark-{index} {{animation:flash-{index} {duration:.5f}s ease-out infinite}}',
            f'@keyframes flash-{index} {{0%,{pct(max(0,at-.001))} {{opacity:0;transform:scale(.4)}} {pct(at)} {{opacity:1;transform:scale(.55)}} {pct(at+.32)},100% {{opacity:0;transform:scale({strength:.2f})}}}}',
        ])
        cans.append(f'<g class="pickup-can can-{index}"><title>{day}: {count} contributions</title>{drink(x-3.5,y-4.5,color,"#b0cadf")}</g>')
        extra = '<rect x="-1" y="-10" width="2" height="2" fill="#71efd4"/><rect x="8" y="2" width="2" height="2" fill="#71efd4"/>' if combo > 1 else ''
        sparks.append(f'<g transform="translate({x:.3f} {y:.3f})"><g class="pickup-spark spark-{index}" opacity="0" shape-rendering="crispEdges"><path d="M-5-4h2v2h-2zM5-5h2v2H5zM-4 5h2v2h-2z" fill="#ffd585"/>{extra}</g></g>')

    effects.extend([
        f'.recovery {{animation:recovery {duration:.5f}s linear infinite}}',
        f'@keyframes recovery {{0%,{pct(t["recovery"]-.45)} {{opacity:0}} {pct(t["recovery"]-.12)},{pct(t["ready_end"])} {{opacity:1}} 100% {{opacity:0}}}}',
        f'.breath-ring {{transform-origin:450px 148px;animation:breath-ring {duration:.5f}s ease-out infinite}}',
        f'@keyframes breath-ring {{0%,{pct(t["drink_end"])} {{opacity:0;transform:scale(.65)}} {pct(t["drink_end"]+.12)} {{opacity:.35}} {pct(t["breathe_end"])},100% {{opacity:0;transform:scale(1.4)}}}}',
        f'.heal-plus {{animation:heal-plus {duration:.5f}s ease-out infinite}}',
        f'@keyframes heal-plus {{0%,{pct(t["drink_start"]+.35)} {{opacity:0;transform:translateY(3px)}} {pct(t["drink_start"]+.55)} {{opacity:.8}} {pct(t["breathe_end"])},100% {{opacity:0;transform:translateY(-10px)}}}}',
    ])
    for name, begin, end in [('hydrate',t['recovery'],t['drink_end']),('breathe',t['drink_end'],t['breathe_end']),('ready',t['breathe_end'],duration)]:
        effects.extend([
            f'.state-{name} {{animation:state-{name} {duration:.5f}s step-end infinite}}',
            f'@keyframes state-{name} {{0% {{opacity:0}} {pct(begin)} {{opacity:1}} {pct(end)} {{opacity:0}}}}',
        ])
    for index in range(4):
        fill_at = t['drink_start'] + .45 + .55 * index
        effects.extend([
            f'.charge-{index} {{animation:charge-{index} {duration:.5f}s step-end infinite}}',
            f'@keyframes charge-{index} {{0% {{opacity:0}} {pct(fill_at)},100% {{opacity:1}}}}',
        ])
    return '\n'.join(effects), cans, sparks, timeline


def runner_svg(data, theme):
    c = THEMES[theme]
    weeks, cells = contribution_grid(data['days'])
    first_x, first_y = 78, 114
    step = 744 / weeks
    rows = []
    active_by_week = [[] for _ in range(weeks)]
    for week, weekday, day, count in cells:
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 10 else 4
        x = first_x + week * step
        y = first_y + weekday * 13
        rows.append(f'<rect x="{x:.2f}" y="{y}" width="{step-3:.2f}" height="10" rx="1" fill="{c["blank"]}"><title>{day}: {count} contributions</title></rect>')
        if level:
            active_by_week[week].append((x+(step-3)/2,y+5,c['levels'][level-1],day,count))
    start = (first_x-13,first_y+5)
    route = ordered_pickups(active_by_week,start[1])
    animation,cans,sparks,timeline = pickup_animation(route,start,step)
    for i,label in ((1,'M'),(3,'W'),(5,'F')):
        rows.append(f'<text x="55" y="{first_y+i*13+9}" font-size="11" fill="{c["muted"]}">{label}</text>')
    months = []
    for week,weekday,day,_ in cells:
        if day.day == 1:
            months.append(f'<text x="{first_x+week*step:.2f}" y="218" font-size="10" fill="{c["muted"]}">{day:%b}</text>')
    legend = ''.join(f'<rect x="{739+15*i}" y="235" width="11" height="10" fill="{color}"/>' for i,color in enumerate((c['blank'],*c['levels'])))
    charge = ''.join(f'<rect x="{424+i*14}" y="175" width="12" height="6" rx="1" fill="{c["blank"]}"/><rect class="charge-{i}" x="{424+i*14}" y="175" width="12" height="6" rx="1" fill="{c["teal"]}" opacity="0"/>' for i in range(4))
    avatar = pixel_runner(-8.4,-19.6,1.4,c)
    stride = pixel_runner(-8.4,-19.6,1.4,c,STRIDE_SPRITE)
    stand = pixel_runner(-8.4,-19.6,1.4,c,STAND_SPRITE)
    sipping = pixel_runner(-8.4,-19.6,1.4,c,DRINK_SPRITE)
    motion = '' if timeline is None else f'''
  <g class="trail-window" opacity="0"><g class="trail-route trail-2">{avatar}</g><g class="trail-route trail-1">{avatar}</g></g>
  <g class="recovery" opacity="0">
    <rect x="382" y="99" width="136" height="103" rx="6" fill="{c['body']}" stroke="{c['edge']}"/>
    <path d="M390 125V119H510V125M390 165H510" fill="none" stroke="{c['teal']}" stroke-width="2"/>
    <text x="450" y="113" text-anchor="middle" font-size="9" letter-spacing="1" fill="{c['teal']}">PIT STOP</text>
    <path d="M397 139h12v23h-12zM395 137h16v3h-16z" fill="{c['blank']}"/>
    <path d="M400 143h6v12h-6z" fill="{c['teal']}" opacity=".6"/>
    <path d="M492 148h12v14h-12zM490 146h16v3h-16z" fill="{c['blank']}"/>
    <g transform="translate(494 137)">{drink(0,0,c['teal'],c['muted'])}</g>
    <ellipse cx="450" cy="163" rx="19" ry="3" fill="{c['blank']}"/>
    <circle class="breath-ring" cx="450" cy="148" r="17" fill="none" stroke="{c['teal']}" opacity="0"/>
    <g class="heal-plus" fill="{c['teal']}" opacity="0"><path d="M424 133h2v3h3v2h-3v3h-2v-3h-3v-2h3zM477 128h2v3h3v2h-3v3h-2v-3h-3v-2h3z"/></g>
    {charge}
    <g text-anchor="middle" font-size="8" letter-spacing="1" fill="{c['muted']}"><text class="state-hydrate" x="450" y="194" opacity="0">HYDRATE</text><text class="state-breathe" x="450" y="194" opacity="0">BREATHE</text><text class="state-ready" x="450" y="194" fill="{c['teal']}" opacity="0">READY TO RUN</text></g>
  </g>'''
    pose_markup = f'''<g class="avatar-size"><g class="run-pose"><g class="jog"><g class="step-a">{avatar}</g><g class="step-b" opacity="0">{stride}</g></g></g>
    <g class="stand-pose" opacity="0"><g class="breathing">{stand}</g></g>
    <g class="drink-pose" opacity="0">{sipping}<g class="sip-arm"><path d="M1-13h4v-4h5" fill="none" stroke="{c['ink']}" stroke-width="2.8"/><g transform="translate(7 -22) scale(.65)">{drink(0,0,c['teal'],c['ink'])}</g></g></g></g>''' if timeline else stand
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="265" viewBox="0 0 900 265" role="img" aria-labelledby="runner-title runner-desc">
<title id="runner-title">Beat Runner — {data['year_contributions']} contributions, energy pickups and a recovery pit stop</title>
<desc id="runner-desc">One drink for each active day. A runner collects them, returns to the center, drinks and catches their breath before the next lap.</desc>
<style>
{animation}
.step-a {{animation:step-a .38s step-end infinite}} .step-b {{animation:step-b .38s step-end infinite}}
.jog {{animation:jog .38s ease-in-out infinite}}
@keyframes step-a {{0%,100% {{opacity:1}} 50% {{opacity:0}}}}
@keyframes step-b {{0%,100% {{opacity:0}} 50% {{opacity:1}}}}
@keyframes jog {{0%,50%,100% {{transform:translateY(0)}} 25%,75% {{transform:translateY(-1.4px)}}}}
@media (prefers-reduced-motion: reduce) {{* {{animation:none !important}}}}
</style>
<g font-family="ui-monospace, Menlo, Consolas, monospace">
  {terminal_frame(c,265,'taku0193@github: ~/contributions')}
  <text x="32" y="68" font-size="14" font-weight="700" fill="{c['teal']}">$ ./beat-runner</text>
  <text x="868" y="68" text-anchor="end" font-size="13" fill="{c['muted']}">{data['year_contributions']:,} contributions / past year</text>
  <path d="M76 107H822" stroke="{c['edge']}"/>
  {''.join(rows)}{''.join(cans)}{''.join(sparks)}{motion}
  <g class="runner-presence"><g class="pickup-runner" style="transform:translate({start[0]}px,{start[1]}px)"><g class="runner-facing">{pose_markup}</g></g></g>
  {''.join(months)}
  <text x="32" y="245" font-size="12" fill="{c['muted']}">Contribution calendar / {data['period_end']} UTC</text>
  <text x="455" y="245" text-anchor="middle" font-size="11" fill="{c['muted']}">1 active day = 1 can</text>
  <text x="730" y="244" text-anchor="end" font-size="11" fill="{c['muted']}">Less</text>{legend}
  <text x="823" y="244" font-size="11" fill="{c['muted']}">More</text>
</g></svg>'''


def still_svg(svg):
    """Keep the authored resting poses; disable animation in the asset itself."""
    return svg.replace('</style>', '* {animation:none !important}\n</style>')



def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('assets'))
    args = parser.parse_args()
    activity = json.loads((args.assets / 'activity-data.json').read_text(encoding='utf-8'))
    files = {}
    for theme in THEMES:
        files[f'header-{theme}.svg'] = hero_svg(theme)
        files[f'beat-runner-{theme}.svg'] = runner_svg(activity, theme)
        for name in ('header', 'beat-runner'):
            files[f'{name}-{theme}-still.svg'] = still_svg(files[f'{name}-{theme}.svg'])
    for svg in files.values():
        ET.fromstring(svg)
    for name, svg in files.items():
        (args.assets / name).write_text(svg, encoding='utf-8')
    print(f"Rendered Motion Lab and Beat Runner for {activity['period_end']} UTC.")


if __name__ == '__main__':
    main()
