#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GRAPHQL_URL = "https://api.github.com/graphql"
OUTPUT_DIR = Path("assets")

PROFILE = {
    "name": "KOH TOM HAN",
    "headline": "CYBERSECURITY UNDERGRADUATE // REVERSE ENGINEERING",
    "identity": [
        "Founder @ CYNX (CyberNexus)",
        "Vice President @ APU FSEC-SS",
        "CTF Player + Challenge Creator",
    ],
    "focus": [
        "Reverse Engineering & Malware Analysis",
        "Digital Forensics & Attack Simulation",
        "Practical Cybersecurity Research",
    ],
    "stack": "Windows / Kali / VMware ESXi / IDA / x64dbg / Python",
    "achievements": [
        "BATxAPU Cyber Kampung 2025 ... 1st Runner-up",
        "APU Internal CTF 2025 ........ 2nd Runner-up",
        "BATxAPU Cyber Tradition ...... Top 5",
        "Sunway CTF 2025 .............. Top 10",
        "Barqsec System Override ...... Top 10",
        "Curtin CTF 2025 .............. Top 16",
        "UMCS CTF 2026 ................ Finalist",
    ],
    "ctf_challenges": 7,
    "ctf_results": 8,
    "languages": 4,
    "graduation": date(2026, 9, 1),
}


@dataclass(frozen=True)
class GitHubStats:
    username: str
    public_repositories: int
    stars: int
    followers: int
    contributions_ytd: int
    account_created: date


PALETTES = {
    "dark": {
        "background": "#090b0e",
        "panel": "#10141a",
        "panel_alt": "#0d1117",
        "border": "#30363d",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "accent": "#ff4d6d",
        "accent_2": "#7ee787",
        "grid": "#21262d",
    },
    "light": {
        "background": "#f6f8fa",
        "panel": "#ffffff",
        "panel_alt": "#f6f8fa",
        "border": "#d0d7de",
        "text": "#1f2328",
        "muted": "#59636e",
        "accent": "#8b0000",
        "accent_2": "#1a7f37",
        "grid": "#d8dee4",
    },
}


def graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "koh-tom-han-profile-readme",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to reach GitHub API: {exc.reason}") from exc

    if result.get("errors"):
        messages = "; ".join(error.get("message", "Unknown GraphQL error") for error in result["errors"])
        raise RuntimeError(f"GitHub GraphQL error: {messages}")

    return result["data"]


def fetch_stats(username: str, token: str) -> GitHubStats:
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    cursor: str | None = None
    total_stars = 0
    public_repositories = 0
    followers = 0
    contributions_ytd = 0
    account_created = date.today()

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!, $cursor: String) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
        }
        repositories(
          first: 100,
          after: $cursor,
          ownerAffiliations: OWNER,
          orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes {
            isArchived
            isFork
            stargazerCount
          }
        }
      }
    }
    """

    while True:
        data = graphql(
            token,
            query,
            {
                "login": username,
                "from": year_start.isoformat().replace("+00:00", "Z"),
                "to": now.isoformat().replace("+00:00", "Z"),
                "cursor": cursor,
            },
        )
        user = data.get("user")
        if not user:
            raise RuntimeError(f"GitHub user '{username}' was not found.")

        repositories = user["repositories"]
        public_repositories = repositories["totalCount"]
        followers = user["followers"]["totalCount"]
        contributions_ytd = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        account_created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()

        # Count stars on original, non-archived repositories. Remove the filters
        # below if you prefer to include forks and archived repositories.
        for repository in repositories["nodes"]:
            if not repository["isFork"] and not repository["isArchived"]:
                total_stars += repository["stargazerCount"]

        page_info = repositories["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return GitHubStats(
        username=username,
        public_repositories=public_repositories,
        stars=total_stars,
        followers=followers,
        contributions_ytd=contributions_ytd,
        account_created=account_created,
    )


def graduation_status(today: date) -> str:
    graduation = PROFILE["graduation"]
    if today < graduation:
        return "BSc Cybersecurity @ APU // expected Sep 2026"
    return "BSc Computer Science (Cybersecurity) // APU"


def account_age(created: date, today: date) -> str:
    years = today.year - created.year - ((today.month, today.day) < (created.month, created.day))
    return f"{max(years, 0)}y on GitHub"


def format_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 10_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:,}"


def text(x: int, y: int, value: object, css_class: str, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" class="{css_class}" '
        f'text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def metric_card(x: int, y: int, label: str, value: str, palette: dict[str, str]) -> str:
    return f"""
      <rect x="{x}" y="{y}" width="180" height="82" rx="10" fill="{palette['panel_alt']}" stroke="{palette['border']}"/>
      {text(x + 16, y + 31, value, 'metric')}
      {text(x + 16, y + 58, label, 'label')}
    """


def build_svg(stats: GitHubStats, mode: str) -> str:
    p = PALETTES[mode]
    today = date.today()
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status = graduation_status(today)

    metrics = [
        ("PUBLIC REPOS", format_number(stats.public_repositories)),
        ("TOTAL STARS", format_number(stats.stars)),
        (f"CONTRIB {today.year}", format_number(stats.contributions_ytd)),
        ("FOLLOWERS", format_number(stats.followers)),
    ]

    svg_parts = [
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="620" viewBox="0 0 1000 620" role="img" aria-labelledby="title desc">
  <title id="title">Koh Tom Han cybersecurity GitHub profile</title>
  <desc id="desc">Dynamic profile card with GitHub statistics, cybersecurity interests, leadership and CTF achievements.</desc>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; fill: {p['text']}; }}
    .name {{ font-size: 34px; font-weight: 800; letter-spacing: 1.4px; }}
    .headline {{ font-size: 15px; font-weight: 700; fill: {p['accent']}; letter-spacing: 0.7px; }}
    .prompt {{ font-size: 16px; font-weight: 700; fill: {p['accent_2']}; }}
    .body {{ font-size: 15px; }}
    .muted {{ font-size: 13px; fill: {p['muted']}; }}
    .section {{ font-size: 14px; font-weight: 800; fill: {p['accent']}; letter-spacing: 1px; }}
    .metric {{ font-size: 27px; font-weight: 800; }}
    .label {{ font-size: 11px; font-weight: 700; fill: {p['muted']}; letter-spacing: 0.8px; }}
    .tiny {{ font-size: 12px; fill: {p['muted']}; }}
  </style>
  <rect width="1000" height="620" rx="18" fill="{p['background']}"/>
  <rect x="16" y="16" width="968" height="588" rx="14" fill="{p['panel']}" stroke="{p['border']}"/>

  <!-- Terminal title bar -->
  <rect x="16" y="16" width="968" height="45" rx="14" fill="{p['panel_alt']}"/>
  <circle cx="43" cy="38" r="6" fill="{p['accent']}"/>
  <circle cx="63" cy="38" r="6" fill="{p['muted']}"/>
  <circle cx="83" cy="38" r="6" fill="{p['accent_2']}"/>
  {text(500, 43, f'{stats.username}@github: ~/profile', 'tiny', 'middle')}

  <!-- Header -->
  {text(52, 112, PROFILE['name'], 'name')}
  {text(52, 142, PROFILE['headline'], 'headline')}
  <line x1="52" y1="162" x2="948" y2="162" stroke="{p['grid']}"/>

  <!-- Left column -->
  {text(52, 202, '$ whoami', 'prompt')}
  {text(69, 231, PROFILE['identity'][0], 'body')}
  {text(69, 256, PROFILE['identity'][1], 'body')}
  {text(69, 281, PROFILE['identity'][2], 'body')}

  {text(52, 324, '$ focus --current', 'prompt')}
  {text(69, 353, PROFILE['focus'][0], 'body')}
  {text(69, 378, PROFILE['focus'][1], 'body')}
  {text(69, 403, PROFILE['focus'][2], 'body')}

  {text(52, 446, '$ stack', 'prompt')}
  {text(69, 475, PROFILE['stack'], 'body')}

  {text(52, 518, '$ status', 'prompt')}
  {text(69, 547, status, 'body')}
  {text(69, 572, f'{PROFILE["ctf_challenges"]} CTF Competitions Contributed // {PROFILE["ctf_results"]} Ranked Results // {PROFILE["languages"]} Languages', 'muted')}

  <!-- Divider -->
  <line x1="520" y1="188" x2="520" y2="576" stroke="{p['grid']}"/>

  <!-- Right column stats -->
  {text(550, 202, 'GITHUB TELEMETRY', 'section')}
'''
    ]

    positions = [(550, 220), (748, 220), (550, 316), (748, 316)]
    for (label, value), (x, y) in zip(metrics, positions):
        svg_parts.append(metric_card(x, y, label, value, p))

    svg_parts.append(f'''
  {text(550, 432, 'FIELD NOTES', 'section')}
  {text(550, 463, PROFILE['achievements'][0], 'body')}
  {text(550, 490, PROFILE['achievements'][1], 'body')}
  {text(550, 517, PROFILE['achievements'][2], 'body')}

  <line x1="550" y1="544" x2="928" y2="544" stroke="{p['grid']}"/>
  {text(550, 570, f'{account_age(stats.account_created, today)} // updated {updated}', 'tiny')}
  <rect x="931" y="558" width="9" height="14" fill="{p['accent_2']}">
    <animate attributeName="opacity" values="1;0;1" dur="1.2s" repeatCount="indefinite"/>
  </rect>
</svg>
''')
    return "".join(svg_parts)


def preview_stats() -> GitHubStats:
    return GitHubStats(
        username=os.getenv("GITHUB_USERNAME", "YOUR_GITHUB_USERNAME"),
        public_repositories=14,
        stars=23,
        followers=18,
        contributions_ytd=287,
        account_created=date(2022, 1, 1),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate sample cards without calling GitHub.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    username = os.getenv("GITHUB_USERNAME", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()

    if args.preview:
        stats = preview_stats()
    else:
        if not username:
            print("error: GITHUB_USERNAME is required", file=sys.stderr)
            return 2
        if not token:
            print("error: GITHUB_TOKEN is required", file=sys.stderr)
            return 2
        stats = fetch_stats(username, token)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for mode in PALETTES:
        output = OUTPUT_DIR / f"profile-{mode}.svg"
        output.write_text(build_svg(stats, mode), encoding="utf-8")
        print(f"wrote {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
