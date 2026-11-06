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


def hero_svg(theme):
    """A quiet, layered night city with three passing pixel runners."""
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
        f'<rect x="{x}" y="172" width="7" height="2" fill="#294754"/>'
        for x in range(lane_x, scene_width - 7, 12)
    )

    # One seamless 384px city tile, repeated beyond the clipped viewport.
    buildings = []
    blocks = ((4, 26, 36), (39, 34, 49), (88, 22, 62), (125, 44, 42),
              (185, 28, 56), (233, 39, 32), (284, 32, 58), (337, 35, 40))
    for index, (x, width, height) in enumerate(blocks):
        top = 154 - height
        buildings.append(f'<rect x="{x}" y="{top}" width="{width}" height="{height}" fill="{"#173446" if index % 2 else "#1c3d4d"}"/>')
        buildings.append(f'<path d="M{x} {top}h{width}" stroke="#2b5461" stroke-width="1"/>')
        if index in (2, 6):
            buildings.append(f'<path d="M{x+width//2} {top}v-9" stroke="#335d6a" stroke-width="2"/>')
        for row in range(2, height // 9):
            for col in range(1, width // 8):
                lit = (row + col + index) % 4 == 0
                color = "#6bb6a9" if lit else "#294957"
                klass = f' class="window-light window-{index % 3}"' if lit and row == 3 else ""
                buildings.append(f'<rect{klass} x="{x+col*8-2}" y="{top+row*8-4}" width="3" height="4" fill="{color}" opacity="{.8 if lit else .45}"/>')
    # Lamps form a middle-distance layer; their glow is intentionally very small.
    buildings.append('<path d="M165 155v-25h8m151 25v-34h8" fill="none" stroke="#396271" stroke-width="2"/>')
    buildings.append('<path d="M169 130h5m154-9h5" stroke="#a9d8b8" stroke-width="2"/>')
    stars = "".join(
        f'<rect class="star star-{i % 3}" x="{x}" y="{y}" width="{size}" height="{size}" fill="#a4c6ce" opacity=".45"/>'
        for i, (x, y, size) in enumerate(((31, 41, 2), (83, 32, 1.5), (143, 43, 2),
                                        (213, 32, 1.5), (264, 43, 2), (343, 59, 1.5)))
    )
    trace = "M18 70h34l6-4 6 4h26l6 7 8-18 8 20 7-9h38l6-4 6 4h25l7 7 8-18 8 20 7-9h31l6-4 6 4h66"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="274" viewBox="0 0 900 274" role="img" aria-labelledby="hero-title hero-desc">
<title id="hero-title">taku0193 — Motion. Rhythm. Code.</title>
<desc id="hero-desc">Three runners pass through a layered night city. A motion capture gate traces their joints, then each footfall sends a flash of their color along the road.</desc>
<style>
.hero-far {{animation:hero-landscape 100s linear infinite}}
.hero-city {{animation:hero-landscape 38s linear infinite}}
.hero-road {{animation:hero-road 1.05s linear infinite}}
.trace-light {{stroke-dasharray:9 91; animation:trace 3.2s linear infinite}}
.track-runner {{animation:pass-through {lap_seconds}s linear infinite;animation-delay:var(--run-offset)}}
{runner_css}
.pose-scan {{animation:scan-pose {lap_seconds}s linear infinite;animation-delay:var(--run-offset)}}
.pulse-stride {{animation:stride var(--stride-time) ease-in-out infinite;animation-delay:var(--run-offset)}}
.step-a {{animation:step-a var(--stride-time) step-end infinite;animation-delay:var(--run-offset)}}
.step-b {{opacity:0;animation:step-b var(--stride-time) step-end infinite;animation-delay:var(--run-offset)}}
.beat-contact {{animation:beat-contact {lap_seconds}s linear infinite;animation-delay:var(--beat-delay)}}
.beat-ray {{animation:beat-ray {lap_seconds}s ease-out infinite;animation-delay:var(--beat-delay)}}
.star {{animation:star-glow 7s ease-in-out infinite}}
.star-1 {{animation-delay:-2.3s}}
.star-2 {{animation-delay:-4.6s}}
.window-light {{animation:window-glow 9s ease-in-out infinite}}
.window-1 {{animation-delay:-3s}}
.window-2 {{animation-delay:-6s}}
@keyframes hero-landscape {{from {{transform:translateX(0)}} to {{transform:translateX(-384px)}}}}
@keyframes hero-road {{from {{transform:translateX(0)}} to {{transform:translateX(-48px)}}}}
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
@keyframes star-glow {{0%,100% {{opacity:.28}} 50% {{opacity:.64}}}}
@keyframes window-glow {{0%,100% {{opacity:.45}} 45%,65% {{opacity:.85}}}}
@media (prefers-reduced-motion: reduce) {{
  .trace-light {{display:none}}
  .hero-far, .hero-city, .hero-road, .track-runner, .pulse-stride,
  .step-a, .step-b, .star, .window-light, .pose-scan,
  .beat-contact, .beat-ray {{animation:none}}
}}
</style>
<defs>
  <clipPath id="hero-scene-clip"><rect x="513" y="52" width="361" height="200" rx="3"/></clipPath>
  <clipPath id="runner-track"><rect x="513" y="156" width="361" height="60"/></clipPath>
  <g id="hero-hills" shape-rendering="crispEdges">
    <path d="M0 124h20v-7h18v-9h23v-11h20v-7h24v8h17v12h24v9h31v-8h18v-11h22v-7h28v9h21v14h28v6h20v-9h20v-8h27v9h23v40H0Z" fill="#142b3b"/>
    <path d="M0 135h30v-5h19v-6h29v8h24v7h28v-5h30v-7h27v6h18v8h40v-8h22v-8h28v8h24v5h22v-6h26v6h17v16H0Z" fill="#19313f"/>
  </g>
  <g id="hero-buildings" shape-rendering="crispEdges">{''.join(buildings)}</g>
  <pattern id="hero-road-mark" width="48" height="16" patternUnits="userSpaceOnUse"><path d="M0 8h19" stroke="#477b83" stroke-width="2"/></pattern>
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
  <rect x="512" y="51" width="363" height="202" rx="4" fill="#0c1726" stroke="#314a60"/>
  <g clip-path="url(#hero-scene-clip)"><g transform="translate({scene_x} 52)">
    <rect width="361" height="200" fill="#0c1726"/>
    {stars}
    <circle cx="320" cy="42" r="9" fill="#b2cbb9" opacity=".8"/>
    <circle cx="324" cy="38" r="9" fill="#0c1726"/>
    <path d="{trace}" fill="none" stroke="#5d9e9d" stroke-width="1.3" opacity=".32"/>
    <path class="trace-light" d="{trace}" pathLength="100" fill="none" stroke="#86e4cf" stroke-width="1.6" opacity=".65"/>
    <g class="hero-far"><use href="#hero-hills"/><use href="#hero-hills" x="384"/></g>
    <g class="hero-city"><use href="#hero-buildings"/><use href="#hero-buildings" x="384"/></g>
    <rect y="154" width="361" height="46" fill="#102431"/>
    <path d="M0 155H361" stroke="#335664"/>
    <rect y="159" width="361" height="3" fill="#264954"/>
    <path d="M0 160H361" stroke="#73c6b4" stroke-opacity=".3"/>
    <g class="hero-road"><rect x="0" y="166" width="432" height="16" fill="url(#hero-road-mark)"/></g>
    <rect x="{lane_x - 4}" y="166" width="{scene_width - lane_x + 4}" height="16" fill="#102431"/>
    {lane_tiles}
    <path d="M0 189H361" stroke="#294754"/>
    <g transform="translate({gate_local} 0)">
      <rect x="-39" y="108" width="78" height="55" fill="#71efd4" opacity=".055"/>
      <path d="M-39 121v-13h11m56 0h11v13m0 29v13h-11m-56 0h-11v-13"
            fill="none" stroke="#71efd4" stroke-width="1.2" opacity=".72"/>
      <path d="M-39 124v24m78-24v24" fill="none" stroke="#71efd4"
            stroke-dasharray="1 4" opacity=".5"/>
      <text x="0" y="102" text-anchor="middle" font-size="8" letter-spacing="1.35" fill="#91d6c9">POSE GATE</text>
    </g>
    <text x="16" y="23" font-size="10" letter-spacing="1.1" fill="#a6bfd2">STAGE 01 / NIGHT RUN</text>
    <text x="345" y="193" text-anchor="end" font-size="8" letter-spacing="1.6" fill="#91c5c5">BEAT TRACK</text>
  </g></g>
  <g clip-path="url(#hero-scene-clip)" aria-hidden="true">{''.join(footsteps)}</g>
  <g clip-path="url(#runner-track)">{''.join(runners)}</g>
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
