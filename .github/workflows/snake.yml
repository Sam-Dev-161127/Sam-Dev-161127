import requests
import json
import math
import sys
from datetime import datetime, timedelta
import os

GITHUB_USER = os.environ.get("GITHUB_USER", "Sam-Dev-161127")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── Fetch contribution data via GraphQL ──────────────────────────────────────
def fetch_contributions():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
                color
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": GITHUB_USER}},
        headers=headers,
    )
    data = resp.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for week in weeks:
        col = []
        for day in week["contributionDays"]:
            col.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "color": day["color"],
            })
        grid.append(col)
    return grid

# ── Build snake path (BFS/greedy across columns) ────────────────────────────
def build_snake_path(grid):
    """Returns list of (col, row) cells the snake visits in order."""
    path = []
    num_cols = len(grid)
    for c in range(num_cols):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((c, r))
    return path

# ── SVG generation ──────────────────────────────────────────────────────────
CELL = 11        # cell size px
GAP  = 2         # gap between cells
STEP = CELL + GAP
MARGIN_X = 10
MARGIN_Y = 30    # space for month labels

EMPTY_COLOR   = "#161b22"
BORDER_COLOR  = "#30363d"
SNAKE_COLOR   = "#39d353"
SNAKE_HEAD    = "#ffffff"
FOOD_COLOR    = "#f78166"   # contribution squares = food

def cell_center(c, r):
    x = MARGIN_X + c * STEP + CELL // 2
    y = MARGIN_Y + r * STEP + CELL // 2
    return x, y

def generate_svg(grid, dark=False):
    bg      = "#0d1117" if dark else "#ffffff"
    txt_col = "#8b949e" if dark else "#57606a"
    empty   = "#161b22" if dark else "#ebedf0"

    num_cols = len(grid)
    num_rows = 7
    width  = MARGIN_X * 2 + num_cols * STEP
    height = MARGIN_Y + num_rows * STEP + 20

    path = build_snake_path(grid)

    # Which cells have contributions (food)?
    food_cells = set()
    for c, col in enumerate(grid):
        for r, day in enumerate(col):
            if day["count"] > 0:
                food_cells.add((c, r))

    # ── Pre-compute frames ──────────────────────────────────────────────────
    # Snake starts with length 3, grows by 1 each time it eats a food cell
    frames = []          # each frame: list of (c,r) = snake body, head first
    eaten  = set()
    body   = []
    init_len = 3

    for i, pos in enumerate(path):
        body.insert(0, pos)
        if pos in food_cells and pos not in eaten:
            eaten.add(pos)
            # grow: don't trim tail
        else:
            # trim to current max length
            max_len = init_len + len(eaten)
            if len(body) > max_len:
                body = body[:max_len]
        frames.append((list(body), set(eaten)))

    total_frames = len(frames)
    frame_dur    = 0.08   # seconds per frame
    total_dur    = total_frames * frame_dur

    # ── Month labels ────────────────────────────────────────────────────────
    month_labels = []
    seen_months = {}
    for c, col in enumerate(grid):
        if col:
            m = col[0]["date"][5:7]
            if m not in seen_months:
                seen_months[m] = c
                month_name = datetime.strptime(col[0]["date"], "%Y-%m-%d").strftime("%b")
                month_labels.append((c, month_name))

    # ── Build SVG ───────────────────────────────────────────────────────────
    lines = []
    lines.append(f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
                 f'style="background:{bg}; border-radius:6px;">')
    lines.append('<defs>')

    # HEAD glow filter
    lines.append('''  <filter id="glow">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>''')

    lines.append('</defs>')

    # Month labels
    for c, name in month_labels:
        x = MARGIN_X + c * STEP
        lines.append(f'<text x="{x}" y="{MARGIN_Y - 6}" font-size="9" '
                     f'fill="{txt_col}" font-family="monospace">{name}</text>')

    # ── Static grid cells (food/empty) ───────────────────────────────────
    # We'll animate visibility of food cells being eaten
    for c, col in enumerate(grid):
        for r, day in enumerate(col):
            x = MARGIN_X + c * STEP
            y = MARGIN_Y + r * STEP
            color = empty if day["count"] == 0 else (day["color"] if not dark else FOOD_COLOR)
            cell_id = f"c{c}_{r}"

            if (c, r) in food_cells:
                # food cell — animate it disappearing when eaten
                # find frame index when this cell is first in `eaten`
                eat_frame = next(
                    (fi for fi, (_, e) in enumerate(frames) if (c, r) in e),
                    total_frames
                )
                eat_time  = eat_frame * frame_dur
                disappear = f"""
    <animate attributeName="opacity" dur="{total_dur:.2f}s" repeatCount="indefinite"
      keyTimes="0;{eat_time/total_dur:.4f};{min((eat_time+frame_dur)/total_dur,1):.4f};1"
      values="1;1;0;0" calcMode="discrete"/>"""
                lines.append(
                    f'<rect id="{cell_id}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{color}">{disappear}</rect>'
                )
            else:
                lines.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" fill="{color}"/>'
                )

    # ── Animate snake body segments ──────────────────────────────────────
    # We'll create a snake group that moves through key-splines
    # Strategy: animate each body segment position across all frames
    # Max snake length
    max_len = init_len + len(food_cells)

    for seg_idx in range(max_len):
        # For each frame, what is the position of segment seg_idx?
        # seg_idx=0 is head
        xs, ys, ops = [], [], []
        for fi, (body_f, _) in enumerate(frames):
            if seg_idx < len(body_f):
                cx, cy = cell_center(*body_f[seg_idx])
                op = 1
            else:
                # not yet grown — place at head, invisible
                cx, cy = cell_center(*body_f[0])
                op = 0
            xs.append(str(cx))
            ys.append(str(cy))
            ops.append(str(op))

        # Build keyTimes
        kt = ";".join(f"{i/(total_frames-1):.4f}" for i in range(total_frames))
        xv = ";".join(xs)
        yv = ";".join(ys)
        ov = ";".join(ops)

        is_head = seg_idx == 0
        fill    = SNAKE_HEAD if is_head else SNAKE_COLOR
        radius  = 5 if is_head else 4
        filt    = ' filter="url(#glow)"' if is_head else ""

        # Initial position
        ix, iy = cell_center(*frames[0][0][0]) if frames else (0, 0)

        lines.append(
            f'<circle cx="{ix}" cy="{iy}" r="{radius}" fill="{fill}"{filt} opacity="0">'
        )
        lines.append(
            f'  <animate attributeName="cx" dur="{total_dur:.2f}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{xv}" calcMode="discrete"/>'
        )
        lines.append(
            f'  <animate attributeName="cy" dur="{total_dur:.2f}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{yv}" calcMode="discrete"/>'
        )
        lines.append(
            f'  <animate attributeName="opacity" dur="{total_dur:.2f}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{ov}" calcMode="discrete"/>'
        )
        lines.append('</circle>')

    lines.append('</svg>')
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Fetching contributions for {GITHUB_USER}...")
    grid = fetch_contributions()
    print(f"  Got {len(grid)} weeks of data")

    svg_light = generate_svg(grid, dark=False)
    svg_dark  = generate_svg(grid, dark=True)

    os.makedirs("dist", exist_ok=True)
    with open("dist/github-contribution-grid-snake.svg", "w") as f:
        f.write(svg_light)
    with open("dist/github-snake-dark.svg", "w") as f:
        f.write(svg_dark)

    print("✅ dist/github-contribution-grid-snake.svg")
    print("✅ dist/github-snake-dark.svg")
