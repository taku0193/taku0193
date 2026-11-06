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

def pixel_runner(x, y, size, colors, pose=SPRITE):
    palette = {"Y": colors["amber"], "W": colors["ink"], "T": colors["teal"], "C": colors["coral"]}
    pixels = []
    for row, line in enumerate(pose):
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


def footstep_light(x, y, delay, color, direction):
    """Leave a lit tile under the planted shoe and send a pulse down the lane."""
    return f'''<g transform="translate({x:.2f} {y:g}) scale({.65 * direction:g} .65)" fill="{color}" style="--beat-delay:{delay:.6f}s">
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


def baseball_batter(colors, swing=False):
    """A right-handed batter, anchored at the ground between the cleats."""
    cap, shirt, trim = colors["amber"], colors["teal"], colors["coral"]
    skin, pants = "#f8dcba", "#e5eaf1"
    if swing:
        head = '<path d="M-1-22h6v2h3v2H0v-1h-1z"/><path d="M0-18h6v4H1v-1H0z" fill="#f8dcba"/>'
        bat = '<path d="M6-12 19-15h3v2L7-10z" fill="#e9b978" stroke="#72533a" stroke-width=".55"/>'
        body = f'''
        <path d="M-3-14h7v3H3v4H-4v-5h1z" fill="{shirt}"/>
        <path d="M-1-13h4v1H1v5h-2z" fill="{trim}"/>
        <path d="M2-14h3v2h5v2H5v-1H1z" fill="{skin}"/>
        <path d="M-4-8h7v3H2v3h2v1H0l-2-4-2 2h-2v2h-2v-3l3-2z" fill="{pants}"/>
        <path d="M-9-2h5v2h-6v-1h1zm9 0h4v1h3v1H0z" fill="#19212e"/>'''
    else:
        head = '<path d="M-3-22h6v2h3v2h-9z"/><path d="M-2-18h6v3H2v1h-3v-1h-1z" fill="#f8dcba"/>'
        bat = '<path d="m-6-12-8-11v-3h2l9 13z" fill="#e9b978" stroke="#72533a" stroke-width=".55"/>'
        body = f'''
        <path d="M-3-14h7v3H3v4h-6v-2h-2v-3h2z" fill="{shirt}"/>
        <path d="M-1-13h2v6h-2z" fill="{trim}"/>
        <path d="M0-13v2h-4v-2h-3v-2h4v1h5v1z" fill="{skin}"/>
        <path d="M-4-8h8v3h1v3h2v1H3L1-5h-2l-2 3h-1v1h-3v-2l2-1z" fill="{pants}"/>
        <path d="M-8-2h5v2h-6v-1h1zm11 0h3v1h3v1H3z" fill="#19212e"/>'''
    return f'''<g shape-rendering="crispEdges">
      <ellipse cy=".4" rx="10" ry="1.35" fill="#15232b" opacity=".42"/>
      {bat}<g fill="{cap}">{head}</g>{body}
    </g>'''


def baseball_swing_scan():
    """Match the scan dots to the batter's visible follow-through joints."""
    joints = ((2, -18), (1, -13), (6, -11), (10, -11),
              (-1, -7), (-5, -4), (-7, -1), (1, -4), (3, -1))
    dots = "".join(f'<circle cx="{x}" cy="{y}" r=".85"/>' for x, y in joints)
    return f'''<g fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2-18 1-13-1-7m2-6 5 2h4m-11 4-4 3-2 3m6-6 2 3 2 3"
            stroke="#17343a" stroke-width="1.8"/>
      <path d="M2-18 1-13-1-7m2-6 5 2h4m-11 4-4 3-2 3m6-6 2 3 2 3"
            stroke="#a0f9e6" stroke-width=".8"/>
      <g fill="#c9fff4">{dots}</g>
    </g>'''


def baseball_pitcher(throwing=False):
    """A pitcher facing the plate, anchored at the mound."""
    if throwing:
        limbs = '''
        <path d="M-4-13h-3v2h-5v2h6v-1h4z" fill="#f6d8b4"/>
        <path d="M2-12h4v4H4v-1H2z" fill="#ae7754"/>
        <path d="M-4-8h7v3h4v3H4L1-4h-3l-3 3h-4v-2l4-3z" fill="#cfdeeb"/>
        <path d="M-10-2h6v2h-7v-1h1zm14-1h5v2H4z" fill="#182330"/>'''
    else:
        limbs = '''
        <path d="M-4-13h2v2h5v2h-7v-1h-2v-2h2z" fill="#f6d8b4"/>
        <path d="M1-12h5v4H1z" fill="#ae7754"/>
        <path d="M-4-8h8v3h1v4H2v-3H-1v3h-4v-4h1z" fill="#cfdeeb"/>
        <path d="M-6-2h5v2h-6v-1h1zm8 0h4v1h2v1H2z" fill="#182330"/>'''
    return f'''<g shape-rendering="crispEdges">
      <ellipse cy=".4" rx="9" ry="1.2" fill="#15232b" opacity=".42"/>
      <path d="M-3-20h6v2h2v2h-8z" fill="#ff9b89"/>
      <path d="M-3-16h6v3h-1v1h-4v-1h-1z" fill="#f6d8b4"/>
      <path d="M-3-13h7v2h1v4h-9v-2h-1v-2h2z" fill="#739ed0"/>
      <path d="M-1-12h1v4h-1z" fill="#b9d7ee"/>
      {limbs}
    </g>'''


CROWD_CSS = """
.cheer-fan {animation:crowd-hop 1.16s ease-in-out infinite}
.cheer-group-1 {animation-delay:-.31s}
.cheer-group-2 {animation-delay:-.61s}
.cheer-group-3 {animation-delay:-.88s}
@keyframes crowd-hop {
  0%,43%,100% {transform:translateY(0)}
  22% {transform:translateY(-2.5px)}
}
.cheer-camera {animation:crowd-camera 2.35s ease-out infinite}
@keyframes crowd-camera {
  0%,61%,78%,100% {opacity:0}
  65% {opacity:.8}
}
"""


def crowd_cheer():
    """Raised arms and staggered jumps in the two upper rows of the stands."""
    colors = ("#d4a86f", "#83c7b8", "#628e9c", "#d6bc96", "#84a9a0")
    fans = []
    for row in range(2):
        for column, x in enumerate(range(12 + 5 * row, 351, 11)):
            if (column + 3 * row) % 9 in (3, 8):
                continue
            y = 67 + 7 * row + round(13 * ((x - 180) / 180) ** 2)
            group = (column * 3 + row) % 4
            color = colors[(column + row * 2) % len(colors)]
            fans.append(
                f'<g transform="translate({x} {y})" fill="{color}">'
                f'<use class="cheer-fan cheer-group-{group}" href="#ballpark-raised-arms"/>'
                '</g>'
            )

    cameras = []
    for index, (x, y) in enumerate(((28, 69), (83, 61), (144, 62), (212, 62),
                                    (273, 63), (336, 70))):
        delay = -.37 * index
        cameras.append(
            f'<g transform="translate({x} {y})">'
            f'<path class="cheer-camera" d="M-2 0H2M0-2V2" '
            f'fill="none" stroke="#ffe5a8" opacity="0" style="animation-delay:{delay:g}s"/>'
            '</g>'
        )

    return f'''<defs>
      <g id="ballpark-raised-arms" shape-rendering="crispEdges">
        <path d="M-3-6h1v2h1v1h2v-1h1v-2h1v3H2v1H1.5v2h-3v-2H-2v-1h-1z"/>
        <path d="M-1-6h2v2h-2zM-3-7h1v1h-1zM2-7h1v1H2z" fill="#efd1a0"/>
      </g>
    </defs>
    <g aria-hidden="true">
      {"".join(fans)}
      {"".join(cameras)}
    </g>'''


def baseball_celebration(colors, pose):
    """Draw an expressive pose and its joint overlay at the feet origin."""
    poses = {
        "crouch": {
            "shoulder_y": -12, "hip_y": -7,
            "arms": (((-3, -12), (-7, -10), (-5, -7)),
                     ((3, -12), (7, -10), (5, -7))),
            "legs": (((-2, -7), (-6, -5), (-5, -1)),
                     ((2, -7), (6, -5), (5, -1))),
        },
        "jump": {
            "shoulder_y": -15, "hip_y": -9,
            "arms": (((-3, -15), (-7, -18), (-8, -23)),
                     ((3, -15), (7, -18), (8, -23))),
            "legs": (((-2, -9), (-6, -5), (-8, -3)),
                     ((2, -9), (6, -6), (5, -1))),
        },
        "land": {
            "shoulder_y": -14, "hip_y": -8,
            "arms": (((-3, -14), (-8, -17), (-9, -21)),
                     ((3, -14), (8, -17), (9, -21))),
            "legs": (((-2, -8), (-4, -4), (-5, -1)),
                     ((2, -8), (4, -4), (5, -1))),
        },
    }
    frame = poses[pose]
    shoulder_y, hip_y = frame["shoulder_y"], frame["hip_y"]
    arms, legs = frame["arms"], frame["legs"]
    cap, shirt, trim = colors["amber"], colors["teal"], colors["coral"]
    skin, pants, ink = "#f8dcba", "#e5eaf1", "#19212e"

    def joint_path(chain):
        return "M" + " ".join(f"{x},{y}" for x, y in chain)

    def limbs(chains, color, width):
        paths = " ".join(joint_path(chain) for chain in chains)
        return f'<path d="{paths}" fill="none" stroke="{color}" stroke-width="{width}"/>'

    fists = "".join(
        f'<rect x="{x - 1.5}" y="{y - 1.5}" width="3" height="3" fill="{skin}"/>'
        for _, _, (x, y) in arms
    )
    cleats = "".join(
        f'<rect x="{x - 2}" y="{y}" width="4" height="1" fill="{ink}"/>'
        for _, _, (x, y) in legs
    )
    torso = ((0, shoulder_y - 1), (0, shoulder_y), (0, hip_y))
    scan_chains = (*arms, *legs, torso)
    scan_path = " ".join(joint_path(chain) for chain in scan_chains)
    joints = dict.fromkeys(point for chain in scan_chains for point in chain)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r=".72"/>' for x, y in joints)
    face = "M-1-3h2v1h-2z" if pose == "crouch" else "M-2-3h1v1h2v-1h1v2h-4z"
    return f'''<g>
      <g shape-rendering="crispEdges" stroke-linecap="square" stroke-linejoin="bevel">
        {limbs(legs, pants, 3.3)}
        {cleats}
        {limbs(arms, skin, 2.2)}
        {fists}
        <path d="M-4,{shoulder_y - 1}H4V{hip_y}H-4Z" fill="{shirt}"/>
        <rect x="-4" y="{hip_y - 1}" width="8" height="1" fill="{trim}"/>
        <g transform="translate(0 {shoulder_y})">
          <path d="M-3-8h6v1h1v2h-8v-2h1z" fill="{cap}"/>
          <path d="M-3-5h6v4h-6z" fill="{skin}"/>
          <path d="M-2-5h1v1h-1zm3 0h1v1H1z{face}" fill="{ink}"/>
        </g>
      </g>
      <g fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="{scan_path}" stroke="#162c34" stroke-width="1.45" opacity=".82"/>
        <path d="{scan_path}" stroke="#b5fff0" stroke-width=".58"/>
        <g fill="#e1fff6" stroke="#28535a" stroke-width=".24">{dots}</g>
      </g>
    </g>'''


def baseball_play():
    """Choreograph the pitch, home run and celebration for each batter."""
    turn = 9.6
    pitch, contact, run_start, wall = .88, 1.44, 1.8, 2.35
    first, third, finish, fade = 3.4, 5.8, 7.0, 9.05
    zoom_ready, launch, apex, landing = 7.38, 7.53, 7.8, 8.09
    zoom_release, wide = 8.95, 9.46
    box = (159, 148)
    home = (180, 151)
    zoom = 2.65
    zoom_transform = f"translate({180 - zoom * home[0]:g}px,{145 - zoom * home[1]:g}px) scale({zoom:g})"
    route = (
        (run_start, box), (2.2, home), (first, (235, 123)),
        (4.6, (180, 100)), (third, (125, 123)), (finish, home),
    )
    stride = .4
    shoe_size = 1.6
    gait_delay = run_start % stride - stride

    def pct(seconds, duration=turn):
        return f"{100 * seconds / duration:.5f}%"

    def move_to(point):
        return f"translate({point[0]}px,{point[1]}px)"

    def phase_rule(name, start, end, initial=0):
        frames = [f"0% {{opacity:{initial}}}"]
        if start:
            frames.append(f"{pct(start)} {{opacity:1}}")
        if end < turn:
            frames.append(f"{pct(end)} {{opacity:0}}")
        return (
            f".{name} {{animation:{name} {turn}s step-end infinite}}\n"
            f"@keyframes {name} {{{' '.join(frames)}}}"
        )

    colors = THEMES["dark"]
    outfits = (
        colors,
        dict(colors, teal="#ffb782", coral="#79d7f7", amber="#f1a9bf"),
        dict(colors, teal="#c6adf4", coral="#ff9b9f", amber="#a1ecc5"),
    )
    stride_a = (-6 * shoe_size, -14 * shoe_size, shoe_size)
    stride_landings = []
    for step in range(round((finish - run_start) / (stride / 2))):
        at = round(run_start + step * stride / 2, 4)
        for (start_at, (x0, y0)), (end_at, (x1, y1)) in zip(route, route[1:]):
            if at < end_at:
                progress = (at - start_at) / (end_at - start_at)
                facing = 1 if x1 > x0 else -1
                shoe_x = (5 if step % 2 == 0 else 4) * shoe_size * facing
                stride_landings.append((at, x0 + (x1 - x0) * progress + shoe_x,
                                        y0 + (y1 - y0) * progress, facing))
                break
    batters, styles, indicators, replay_players = [], [], [], []
    for index, outfit in enumerate(outfits):
        order = f"batting-turn-{index + 1}"
        duration = turn * len(outfits)
        delay = -((duration - index * turn) % duration)
        styles.append(
            f".{order} {{animation:batting-turn {duration:g}s step-end infinite;"
            f"animation-delay:{delay:g}s}}"
        )
        lights = "".join(
            footstep_light(x, y, at - turn, outfit["teal"], facing)
            for at, x, y, facing in stride_landings
        )
        swing = baseball_batter(outfit, swing=True) + baseball_swing_scan()
        replay_players.append(f'<g class="{order}" opacity="{int(index == 0)}">{swing}</g>')
        batters.append(f'''<g class="{order}" opacity="{int(index == 0)}">
      <g class="batter-at-plate" transform="translate({box[0]} {box[1]})">
        <g class="batter-set">{baseball_batter(outfit)}</g>
        <g class="batter-hit" opacity="0">{swing}</g>
      </g>
      <g class="basepath-lights" opacity="0">{lights}</g>
      <g class="home-runner" opacity="0">
        <g class="basepath-stride"><g class="basepath-facing">
          <g class="basepath-step-a">{pixel_runner(*stride_a, outfit)}</g>
          <g class="basepath-step-b" opacity="0">{pixel_runner(*stride_a, outfit, STRIDE_SPRITE)}</g>
        </g></g>
        <g class="home-celebration" opacity="0">
          <ellipse cy=".6" rx="7" ry="1.6" fill="#161c24" opacity=".48"/>
          <g class="celebration-lift">
            <g class="celebration-crouch">{baseball_celebration(outfit, "crouch")}</g>
            <g class="celebration-jump" opacity="0">{baseball_celebration(outfit, "jump")}</g>
            <g class="celebration-land" opacity="0">{baseball_celebration(outfit, "land")}</g>
          </g>
        </g>
      </g>
    </g>''')
        indicators.append(f'''<rect x="{320 + 11 * index}" y="181" width="6" height="6" fill="{outfit["teal"]}" opacity=".24"/>
      <rect class="{order}" x="{320 + 11 * index}" y="181" width="6" height="6" fill="{outfit["teal"]}" opacity="{int(index == 0)}"/>''')

    phase_labels = (
        ("play-ready", "AT BAT", 0, pitch),
        ("play-pitch", "PITCH", pitch, contact),
        ("play-contact", "CONTACT", contact, run_start),
        ("play-run", "IN PLAY", run_start, wall),
        ("play-homer", "HOME RUN", wall, finish),
        ("play-home", "BACK HOME", finish, zoom_ready),
        ("play-celebrate", "HOME PLATE / CELEBRATION", zoom_ready, turn),
    )
    for name, _, start, end in phase_labels:
        styles.append(phase_rule(name, start, end, initial=int(start == 0)))
    for name, start, end, initial in (
        ("pitcher-set", 0, pitch, 1),
        ("pitcher-throw", pitch, 1.7, 0),
        ("pitcher-reset", 1.7, turn, 0),
        ("batter-at-plate", 0, run_start, 1),
        ("batter-set", 0, contact, 1),
        ("batter-hit", contact, run_start, 0),
        ("basepath-lights", run_start, finish + .3, 0),
        ("basepath-stride", 0, finish, 1),
        ("home-celebration", finish, turn, 0),
        ("celebration-crouch", 0, launch, 1),
        ("celebration-jump", launch, landing, 0),
        ("celebration-land", landing, turn, 0),
        ("baseball-tail", contact, wall + .15, 0),
    ):
        styles.append(phase_rule(name, start, end, initial))
    phase_css = "\n".join(styles)
    route_css = "\n".join(
        f"  {pct(at)} {{opacity:1;transform:{move_to(point)}}}"
        for at, point in route
    )
    animation = f'''
{phase_css}
{CROWD_CSS}
@keyframes batting-turn {{0% {{opacity:1}} {100 / len(outfits):.6f}%,100% {{opacity:0}}}}
.home-runner {{animation:home-runner {turn}s linear infinite}}
@keyframes home-runner {{
  0%,{pct(run_start - .001)} {{opacity:0;transform:{move_to(box)}}}
{route_css}
  {pct(fade)} {{opacity:1;transform:{move_to(home)}}}
  100% {{opacity:0;transform:{move_to(home)}}}
}}
.basepath-facing {{animation:basepath-facing {turn}s step-end infinite}}
@keyframes basepath-facing {{
  0%,{pct(third)},100% {{transform:scaleX(1)}}
  {pct(first)} {{transform:scaleX(-1)}}
}}
.basepath-step-a {{animation:step-a {stride}s step-end infinite {gait_delay:.4f}s}}
.basepath-step-b {{animation:step-b {stride}s step-end infinite {gait_delay:.4f}s}}
.beat-contact {{animation:beat-contact {turn}s linear infinite;animation-delay:var(--beat-delay)}}
.beat-ray {{animation:beat-ray {turn}s ease-out infinite;animation-delay:var(--beat-delay)}}
@keyframes step-a {{0%,100% {{opacity:1}} 50% {{opacity:0}}}}
@keyframes step-b {{0%,100% {{opacity:0}} 50% {{opacity:1}}}}
@keyframes beat-contact {{0% {{opacity:1}} {pct(.18)},100% {{opacity:0}}}}
@keyframes beat-ray {{
  0% {{opacity:0;transform:translateX(0)}}
  {pct(.045)} {{opacity:.76;transform:translateX(3px)}}
  {pct(.27)},100% {{opacity:0;transform:translateX(15px)}}
}}
.baseball {{animation:baseball-flight {turn}s linear infinite}}
@keyframes baseball-flight {{
  0%,{pct(pitch - .001)} {{opacity:0;transform:translate(169px,114px)}}
  {pct(pitch)} {{opacity:1;transform:translate(169px,114px)}}
  {pct(contact - .17)} {{opacity:1;transform:translate(174px,125px)}}
  {pct(contact)} {{opacity:1;transform:translate(173px,136px)}}
  {pct(1.61)} {{opacity:1;transform:translate(190px,105px)}}
  {pct(1.83)} {{opacity:1;transform:translate(209px,77px)}}
  {pct(2.07)} {{opacity:1;transform:translate(231px,57px)}}
  {pct(wall)} {{opacity:1;transform:translate(254px,53px)}}
  {pct(2.55)} {{opacity:1;transform:translate(271px,60px)}}
  {pct(2.71)},100% {{opacity:0;transform:translate(283px,69px)}}
}}
.swing-flash {{animation:swing-flash {turn}s ease-out infinite}}
@keyframes swing-flash {{
  0%,{pct(contact - .001)} {{opacity:0}}
  {pct(contact)} {{opacity:1}}
  {pct(contact + .24)},100% {{opacity:0}}
}}
.crowd-cheer {{animation:crowd-cheer {turn}s ease-out infinite}}
@keyframes crowd-cheer {{
  0%,{pct(wall)} {{opacity:0}}
  {pct(wall + .16)},{pct(finish + .38)} {{opacity:1}}
  {pct(fade)},100% {{opacity:0}}
}}
.homer-banner {{animation:homer-banner {turn}s ease-out infinite}}
@keyframes homer-banner {{
  0%,{pct(wall)} {{opacity:0;transform:translateY(5px)}}
  {pct(wall + .2)},{pct(finish)} {{opacity:1;transform:translateY(0)}}
  {pct(zoom_ready)},100% {{opacity:0;transform:translateY(-2px)}}
}}
.swing-replay {{animation:swing-replay {turn}s ease-out infinite}}
@keyframes swing-replay {{
  0%,{pct(contact)} {{opacity:0}}
  {pct(contact + .12)},{pct(4.2)} {{opacity:1}}
  {pct(4.48)},100% {{opacity:0}}
}}
.home-camera {{animation:home-camera {turn}s ease-in-out infinite;transform-origin:0 0}}
@keyframes home-camera {{
  0%,{pct(finish)} {{transform:translate(0,0) scale(1)}}
  {pct(zoom_ready)},{pct(zoom_release)} {{transform:{zoom_transform}}}
  {pct(wide)},100% {{transform:translate(0,0) scale(1)}}
}}
.field-pitcher {{animation:field-pitcher {turn}s ease-in-out infinite}}
@keyframes field-pitcher {{
  0%,{pct(finish)} {{opacity:1}}
  {pct(zoom_ready)},{pct(zoom_release)} {{opacity:.22}}
  {pct(wide)},100% {{opacity:1}}
}}
.celebration-lift {{animation:celebration-lift {turn}s linear infinite}}
@keyframes celebration-lift {{
  0%,{pct(launch)} {{transform:translateY(0);animation-timing-function:ease-out}}
  {pct(apex)} {{transform:translateY(-8px);animation-timing-function:ease-in}}
  {pct(landing)},100% {{transform:translateY(0)}}
}}
.pose-camera-hud {{animation:pose-camera-hud {turn}s ease-out infinite}}
@keyframes pose-camera-hud {{
  0%,{pct(finish)} {{opacity:0}}
  {pct(zoom_ready)},{pct(zoom_release)} {{opacity:1}}
  {pct(wide)},100% {{opacity:0}}
}}
'''
    labels = "".join(
        f'<text class="{name}" x="16" y="185" font-size="10" font-weight="700" '
        f'letter-spacing="1.5" fill="#e7d6ac" opacity="{int(start == 0)}">{label}</text>'
        for name, label, start, _ in phase_labels
    )
    set_pitcher = baseball_pitcher()
    scene = f'''<g class="crowd-cheer" opacity="0">{crowd_cheer()}</g>
    <g class="field-pitcher" transform="translate(180 124)">
      <g class="pitcher-set">{set_pitcher}</g>
      <g class="pitcher-throw" opacity="0">{baseball_pitcher(throwing=True)}</g>
      <g class="pitcher-reset" opacity="0">{set_pitcher}</g>
    </g>
    {"".join(batters)}
    <g class="swing-flash" opacity="0" fill="#ffdf97">
      <path d="M172 128h1v5h-1zm0 11h1v5h-1zm-8-4h5v1h-5zm12 0h5v1h-5z"/>
    </g>
    <g class="baseball" opacity="0">
      <path class="baseball-tail" opacity="0" d="M-14 6l10-5 2 1-11 6z" fill="#ffd585"/>
      <circle r="2.35" fill="#fff3d6" stroke="#524030" stroke-width=".7"/>
      <path d="M-.75-1.65q1.5 1.6 0 3.3" fill="none" stroke="#c97969" stroke-width=".65"/>
    </g>'''
    hud = f'''<g class="homer-banner" opacity="0">
      <rect x="94" y="32" width="173" height="24" rx="2" fill="#281f1c" stroke="#b98952"/>
      <path d="M102 44h8m140 0h8" stroke="#ffbc73"/>
      <text x="180.5" y="50" text-anchor="middle" font-size="18" font-weight="800"
            letter-spacing="1.8" fill="#ffe4a4">HOME RUN!</text>
    </g>
    <g class="pose-camera-hud" opacity="0">
      <path d="M127 64V53h12m82 0h12v11m0 81v11h-12m-82 0h-12v-11"
            fill="none" stroke="#a5f1dc" stroke-width="1.4" opacity=".72"/>
      <rect x="275" y="12" width="74" height="16" rx="2" fill="#0c1c27" stroke="#3b6b6c"/>
      <circle cx="285" cy="20" r="2" fill="#a5f1dc"/>
      <text x="292" y="23" font-size="8" letter-spacing=".65" fill="#d0f2ea">POSE CAM</text>
    </g>
    {labels}
    <text x="312" y="187" text-anchor="end" font-size="8" letter-spacing="1.15" fill="#c0d3c8">BATTING ORDER</text>
    {"".join(indicators)}'''
    replay = f'''<g class="swing-replay" opacity="0">
      <rect x="371" y="77" width="109" height="84" rx="3" fill="#0b1822" stroke="#416267"/>
      <path d="M380 99v-5h6m79 0h6v5m0 50v5h-6m-79 0h-6v-5" fill="none" stroke="#5d9e9d"/>
      <text x="425.5" y="89" text-anchor="middle" font-size="8" letter-spacing="1.1" fill="#b3e4d9">SWING REPLAY</text>
      <path d="M387 149h77" stroke="#35585c"/>
      <g transform="translate(420 146) scale(2.25)">{"".join(replay_players)}</g>
    </g>'''
    return animation, scene, hud, replay


def hero_svg(theme):
    """Show a night game next to the profile scoreboard."""
    c = THEMES[theme]
    scene_x = 513
    play_css, play, hud, replay = baseball_play()
    trace = "M338 205h19l4-3 4 3h10l4 5 6-14 6 16 5-7h13l4-3 4 3h9l4 5 6-14 6 16 5-7h17"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="274" viewBox="0 0 900 274" role="img" aria-labelledby="hero-title hero-desc">
<title id="hero-title">taku0193 — Motion. Rhythm. Code.</title>
<desc id="hero-desc">A batter hits a home run and circles the bases as the crowd cheers. At home plate the camera zooms in on a celebration jump with joint landmarks.</desc>
<style>
.trace-light {{stroke-dasharray:9 91; animation:trace 3.2s linear infinite}}
@keyframes trace {{to {{stroke-dashoffset:-100}}}}
{play_css}
@media (prefers-reduced-motion: reduce) {{
  .trace-light {{display:none}}
  * {{animation:none !important}}
}}
</style>
<defs>
  <clipPath id="hero-scene-clip"><rect x="513" y="52" width="361" height="200"/></clipPath>
  <clipPath id="stadium-frame"><rect x="25" y="52" width="849" height="200" rx="5"/></clipPath>
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
    <g class="home-camera">
      {ballpark_scene()}
      {play}
    </g>
    {hud}
    <text x="16" y="23" font-size="10" letter-spacing="1.1" fill="#c4d7d8">STAGE 01 / NIGHT GAME</text>
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
    {replay}
  </g>
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
