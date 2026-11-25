"""Render a 495x190 contribution activity card that matches the github-readme-stats cards.

Usage: GITHUB_TOKEN=... python activity.py <username> <output.svg>
"""

import datetime as dt
import json
import os
import sys
import urllib.request

DAYS = 30
W, H = 495, 190
BG, BORDER = "#0d1117", "#30363d"
TITLE, TEXT, MUTED, GRID = "#c792ea", "#c0caf5", "#7aa2f7", "#21262d"
LINE, POINT = "#c792ea", "#ffd866"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"


def fetch(user: str, token: str) -> list[tuple[dt.date, int]]:
    end = dt.datetime.now(dt.timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
    start = (end - dt.timedelta(days=DAYS - 1)).replace(hour=0, minute=0, second=0)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
      contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {"login": user, "from": start.isoformat(), "to": end.isoformat()}})
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body.encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return sorted(days)[-DAYS:]


def smooth_path(pts: list[tuple[float, float]], floor: float) -> str:
    """Catmull-Rom spline through the points, clamped so it never dips below the baseline."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(p1[1] + (p2[1] - p0[1]) / 6, floor))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(p2[1] - (p3[1] - p1[1]) / 6, floor))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def render(days: list[tuple[dt.date, int]]) -> str:
    total = sum(c for _, c in days)
    peak = max([c for _, c in days] + [1])
    left, right, top, bottom = 45, W - 25, 72, H - 38
    step = (right - left) / (len(days) - 1)
    pts = [(left + i * step, bottom - (c / peak) * (bottom - top)) for i, (_, c) in enumerate(days)]
    line = smooth_path(pts, bottom)
    area = f"{line} L{right:.1f},{bottom} L{left},{bottom} Z"

    grid, labels = [], []
    for v in sorted({0, (peak + 1) // 2, peak}):
        y = bottom - (v / peak) * (bottom - top)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID}" stroke-dasharray="3 3"/>')
        labels.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" class="axis">{v}</text>')
    for i, (day, _) in enumerate(days):
        if (len(days) - 1 - i) % 7 == 0:
            labels.append(f'<text x="{pts[i][0]:.1f}" y="{bottom + 18}" text-anchor="middle" class="axis">{day.strftime("%b %-d")}</text>')
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{POINT}"/>' for (x, y), (_, c) in zip(pts, days) if c
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">Contribution Activity: {total} contributions in the last {DAYS} days</title>
<style>
  .title {{ font: 600 18px {FONT}; fill: {TITLE}; }}
  .sub {{ font: 400 12px {FONT}; fill: {TEXT}; opacity: .8; }}
  .axis {{ font: 400 10px {FONT}; fill: {MUTED}; }}
</style>
<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{LINE}" stop-opacity=".35"/><stop offset="1" stop-color="{LINE}" stop-opacity="0"/>
</linearGradient></defs>
<rect x="0.5" y="0.5" rx="4.5" width="{W - 1}" height="{H - 1}" fill="{BG}" stroke="{BORDER}"/>
<text x="25" y="35" class="title">Contribution Activity</text>
<text x="25" y="54" class="sub">{total} contributions in the last {DAYS} days</text>
{''.join(grid)}
<path d="{area}" fill="url(#fill)"/>
<path d="{line}" fill="none" stroke="{LINE}" stroke-width="2" stroke-linecap="round"/>
{dots}
{''.join(labels)}
</svg>
"""


if __name__ == "__main__":
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(render(fetch(user, os.environ["GITHUB_TOKEN"])))
