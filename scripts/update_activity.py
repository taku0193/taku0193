#!/usr/bin/env python3
"""Refresh the contribution pulse and annual overview from GitHub aggregate data.

GITHUB_TOKEN=... python3 scripts/update_activity.py --out assets
The display uses GitHub's UTC calendar day; update timestamps are shown in JST.
Only aggregate counts and calendar days are saved, never repository details.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

JST = timezone(timedelta(hours=9))
QUERY = """query($login:String!,$to:DateTime!){
  user(login:$login){ contributionsCollection(to:$to){
    startedAt endedAt totalCommitContributions totalIssueContributions
    totalPullRequestContributions totalPullRequestReviewContributions
    totalRepositoryContributions restrictedContributionsCount
    contributionCalendar { totalContributions weeks { contributionDays {
      date weekday contributionCount contributionLevel
    } } }
  } }
}"""
FIELDS = [
    ('commits', 'Commits', 'totalCommitContributions'),
    ('pull_requests', 'Pull requests', 'totalPullRequestContributions'),
    ('reviews', 'Code reviews', 'totalPullRequestReviewContributions'),
    ('issues', 'Issues', 'totalIssueContributions'),
    ('repositories', 'Repositories created', 'totalRepositoryContributions'),
    ('private', 'Private · count only', 'restrictedContributionsCount'),
]


def nonnegative_int(value):
    if type(value) is not int or value < 0:
        raise ValueError('A contribution count is not a nonnegative integer')
    return value


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone is required for an activity timestamp')
    return result.astimezone(timezone.utc)


def pulse_parameters(count):
    count = nonnegative_int(count)
    intensity = count / (count + 12)
    return {
        'intensity': intensity,
        'amplitude': 0.0 if count == 0 else 6 + 44 * intensity,
        'period_seconds': 2.6 - 2.0 * intensity,
        'stroke_width': 2.0 + 1.2 * intensity,
        'ring_length': 380 * intensity,
    }


def summarize(payload, username):
    if payload.get('errors'):
        raise ValueError('GitHub GraphQL returned an error; existing assets are preserved')
    collection = payload['data']['user']['contributionsCollection']
    as_of = instant(collection['endedAt'])
    today = as_of.date()
    calendar = collection['contributionCalendar']
    total = nonnegative_int(calendar['totalContributions'])
    days = {}
    for week in calendar['weeks']:
        for item in week['contributionDays']:
            key = date.fromisoformat(item['date']).isoformat()
            if key in days:
                raise ValueError('Duplicate date in contribution calendar')
            days[key] = nonnegative_int(item['contributionCount'])
    if today.isoformat() not in days:
        raise ValueError('The current UTC day is missing; do not replace it with a false zero')
    if sum(days.values()) != total:
        raise ValueError('Calendar day counts do not match the annual total')
    mix = [{'key': key, 'label': label, 'count': nonnegative_int(collection[field])}
           for key, label, field in FIELDS]
    remainder = total - sum(item['count'] for item in mix)
    if remainder < 0:
        raise ValueError('Activity categories exceed the calendar total')
    if remainder:
        mix.append({'key': 'other', 'label': 'Other contributions', 'count': remainder})
    start = instant(collection['startedAt']).date()
    eligible = {key: value for key, value in days.items() if start <= date.fromisoformat(key) <= today}
    longest = run = 0
    previous = None
    for key, value in sorted(eligible.items()):
        day = date.fromisoformat(key)
        run = run + 1 if value and previous == day - timedelta(days=1) else int(value > 0)
        longest = max(longest, run)
        previous = day
    return {
        'schema_version': 1,
        'username': username,
        'source': 'https://api.github.com/graphql',
        'calendar_timezone': 'UTC',
        'updated_at': as_of.isoformat().replace('+00:00', 'Z'),
        'period_start': start.isoformat(),
        'period_end': today.isoformat(),
        'today_date': today.isoformat(),
        'today_contributions': days[today.isoformat()],
        'year_contributions': total,
        'last_7_days': sum(days.get((today - timedelta(days=i)).isoformat(), 0) for i in range(7)),
        'active_days': sum(value > 0 for value in eligible.values()),
        'longest_streak': longest,
        'mix': mix,
        'days': days,
    }


def colors(theme):
    return (
        ('#0b141b', '#f0f6fc', '#93a7b6', '#62e4d1', '#1b303a', '#2a3e48')
        if theme == 'dark' else
        ('#f6f9fc', '#172b3e', '#526579', '#087f8c', '#e1ebf0', '#d9e3ed')
    )


def pulse_svg(data, theme):
    count = nonnegative_int(data['today_contributions'])
    params = pulse_parameters(count)
    amplitude, period = params['amplitude'], params['period_seconds']
    bg, ink, muted, accent, grid, border = colors(theme)
    baseline = 113
    p, q, r, s, t = (baseline - amplitude * .15, baseline + amplitude * .2,
                      baseline - amplitude, baseline + amplitude * .65, baseline - amplitude * .4)
    path = f'M0 113H17C22 113 22 {p:.3f} 27 {p:.3f}S32 113 38 113H47L52 {q:.3f}L59 {r:.3f}L66 {s:.3f}L73 113H85Q96 113 100 {t:.3f}Q108 {t:.3f} 115 113H140'
    cycles = ''.join(f'<path transform="translate({i * 140} 0)" d="{path}"/>' for i in range(6))
    formatted = f'{count:,}'
    font_size = 49 if len(formatted) <= 3 else 39 if len(formatted) <= 5 else 29
    updated = instant(data['updated_at']).astimezone(JST).strftime('%m/%d %H:%M JST')
    signal_label = 'No contributions yet · calm signal' if count == 0 else 'More contributions. Stronger pulse.'
    animation = 'none' if count == 0 else f'beat {period:.6f}s ease-out infinite'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="230" viewBox="0 0 900 230" role="img" aria-labelledby="pulse-title pulse-desc">
<title id="pulse-title">{count} contributions today — {data['today_date']} UTC</title>
<desc id="pulse-desc">The count is from today's GitHub contribution calendar. The waveform grows taller and moves faster as contributions increase. Updated {escape(updated)}.</desc>
<defs>
  <pattern id="pulse-grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" stroke="{grid}" stroke-width=".7" fill="none"/></pattern>
  <clipPath id="pulse-window"><rect x="276" y="60" width="592" height="112" rx="5"/></clipPath>
  <linearGradient id="pulse-fade"><stop stop-color="white" stop-opacity=".12"/><stop offset=".08" stop-color="white"/><stop offset=".92" stop-color="white"/><stop offset="1" stop-color="white" stop-opacity=".12"/></linearGradient>
  <mask id="pulse-mask"><rect x="276" y="60" width="592" height="112" fill="url(#pulse-fade)"/></mask>
</defs>
<style>
  .wave{{animation:{'none' if count == 0 else f'trace {period:.6f}s linear infinite'}}}
  .heart{{transform-box:fill-box;transform-origin:center;animation:{animation}}}
  .meter{{animation:{'none' if count == 0 else f'meter {period:.6f}s ease-out infinite'}}}
  @keyframes trace{{to{{transform:translateX(-140px)}}}}
  @keyframes beat{{0%,45%,100%{{transform:scale(1)}}10%{{transform:scale(1.2)}}23%{{transform:scale(1)}}31%{{transform:scale(1.09)}}}}
  @keyframes meter{{0%,45%,100%{{opacity:.55}}10%,30%{{opacity:1}}}}
  @media(prefers-reduced-motion:reduce){{.wave,.heart,.meter{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="899" height="229" rx="14" fill="{bg}" stroke="{border}"/>
<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">
  <text x="28" y="33" font-size="12" font-weight="650" letter-spacing="1.6" fill="{accent}">CONTRIBUTION PULSE</text>
  <text x="868" y="32" text-anchor="end" font-size="11" font-weight="600" fill="{muted}">TODAY (UTC) · {data['today_date']}</text>
  <path d="M239 59V196" stroke="{border}"/>
  <circle cx="120" cy="130" r="64" stroke="{border}" stroke-width="4" fill="none"/>
  <circle cx="120" cy="130" r="74" stroke="{border}" stroke-width="3" stroke-dasharray="1 10.6" fill="none"/>
  <circle class="meter" cx="120" cy="130" r="64" stroke="{accent}" stroke-width="4" stroke-dasharray="{params['ring_length']:.3f} 403" stroke-linecap="round" transform="rotate(128 120 130)" fill="none"/>
  <path class="heart" d="M120 99L112 91C105 84 113 76 120 84C127 76 135 84 128 91Z" fill="{accent}"/>
  <text x="120" y="143" text-anchor="middle" font-size="{font_size}" font-weight="650" letter-spacing="-1.5" fill="{ink}">{formatted}</text>
  <text x="120" y="160" text-anchor="middle" font-size="9" font-weight="600" letter-spacing="1.2" fill="{muted}">TODAY'S</text>
  <text x="120" y="175" text-anchor="middle" font-size="9.5" font-weight="650" letter-spacing=".5" fill="{muted}">CONTRIBUTIONS</text>
  <rect x="276" y="60" width="592" height="112" rx="5" fill="url(#pulse-grid)"/>
  <path d="M276 113H868" stroke="{accent}" stroke-opacity=".15" fill="none"/>
  <g clip-path="url(#pulse-window)" mask="url(#pulse-mask)"><g transform="translate(276 0)"><g class="wave" fill="none" stroke="{accent}" stroke-width="{params['stroke_width']:.3f}" stroke-linecap="round" stroke-linejoin="round">{cycles}</g></g></g>
  <text x="276" y="198" font-size="11" fill="{muted}">{signal_label}</text>
  <text x="868" y="198" text-anchor="end" font-size="10" fill="{muted}">Updated {updated}</text>
</g></svg>'''


def overview_svg(data, theme):
    bg, ink, muted, accent, grid, border = colors(theme)
    total = data['year_contributions']
    palette = [accent, '#4b9be8', '#b497ec', '#d9a241', '#8499ac', '#48b59b', '#a0a9b1']
    rows = []
    spacing = 29 if len(data['mix']) <= 6 else 25
    for i, item in enumerate(data['mix']):
        y = 80 + i * spacing
        width = 240 * item['count'] / total if total else 0
        rows.append(f'''<text x="356" y="{y + 4}" font-size="12" fill="{muted}">{escape(item['label'])}</text>
<rect x="510" y="{y - 5}" width="240" height="7" rx="3.5" fill="{grid}"/>
<rect x="510" y="{y - 5}" width="{width:.3f}" height="7" rx="3.5" fill="{palette[i]}"/>
<text x="853" y="{y + 4}" text-anchor="end" font-size="14" font-weight="600" fill="{ink}">{item['count']:,}</text>''')
    updated = instant(data['updated_at']).astimezone(JST).strftime('%m/%d %H:%M JST')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300" role="img" aria-labelledby="overview-title overview-desc">
<title id="overview-title">Activity summary — {total} contributions in the past year</title>
<desc id="overview-desc">{'; '.join(f"{escape(x['label'])}: {x['count']}" for x in data['mix'])}. Public activity and anonymized private counts. Bars show shares of all contributions.</desc>
<rect x=".5" y=".5" width="899" height="299" rx="14" fill="{bg}" stroke="{border}"/>
<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">
<text x="28" y="33" font-size="12" font-weight="650" letter-spacing="1.6" fill="{accent}">ACTIVITY SUMMARY</text>
<text x="868" y="32" text-anchor="end" font-size="11" font-weight="600" fill="{muted}">PAST YEAR</text>
<text x="32" y="119" font-size="59" font-weight="650" letter-spacing="-2" fill="{ink}">{total:,}</text>
<text x="34" y="145" font-size="11" font-weight="650" letter-spacing="1.4" fill="{muted}">TOTAL CONTRIBUTIONS</text>
<text x="34" y="183" font-size="13" fill="{muted}">Last 7 days</text><text x="285" y="183" text-anchor="end" font-size="15" font-weight="600" fill="{ink}">{data['last_7_days']:,}</text>
<text x="34" y="211" font-size="13" fill="{muted}">Active days</text><text x="285" y="211" text-anchor="end" font-size="15" font-weight="600" fill="{ink}">{data['active_days']}</text>
<text x="34" y="239" font-size="13" fill="{muted}">Longest streak</text><text x="285" y="239" text-anchor="end" font-size="15" font-weight="600" fill="{ink}">{data['longest_streak']} days</text>
<path d="M322 61V250" stroke="{border}"/>
{''.join(rows)}
<path d="M28 263H872" stroke="{border}"/>
<text x="28" y="284" font-size="10" fill="{muted}">{data['period_start']} — {data['period_end']} (UTC) · Includes anonymized private counts</text>
<text x="868" y="284" text-anchor="end" font-size="10" fill="{muted}">Updated {updated}</text>
</g></svg>'''


def write_assets(data, destination):
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for theme in ('light', 'dark'):
        files[f'pulse-{theme}.svg'] = pulse_svg(data, theme)
        files[f'overview-{theme}.svg'] = overview_svg(data, theme)
    for svg in files.values():
        ET.fromstring(svg)
    files['activity-data.json'] = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    for name, content in files.items():
        temporary = destination / (name + '.tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(destination / name)


def fetch_activity(username):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError('GITHUB_TOKEN is required to refresh activity')
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    request = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': username, 'to': now}}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': f'{username}-profile-readme'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('assets'))
    parser.add_argument('--username', default='taku0193')
    parser.add_argument('--from-response', type=Path, help='Render a previously saved GraphQL response offline')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]+', args.username):
        raise ValueError('Invalid GitHub username')
    payload = json.loads(args.from_response.read_text()) if args.from_response else fetch_activity(args.username)
    data = summarize(payload, args.username)
    write_assets(data, args.out)
    print(f"Updated {args.username}: {data['today_contributions']} contributions on {data['today_date']} UTC; {data['year_contributions']} in the past year.")


if __name__ == '__main__':
    main()
