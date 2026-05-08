import requests
import os
from datetime import datetime

GITHUB_USER  = os.environ.get("GITHUB_USER", "Sam-Dev-161127")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── Fetch contributions ──────────────────────────────────────────────────────
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
                "date":  day["date"],
                "count": day["contributionCount"],
                "color": day["color"],
            })
        grid.append(col)
    return grid

# ── Layout constants ─────────────────────────────────────────────────────────
CELL    = 10
GAP     = 3
STEP    = CELL + GAP
MX      = 16
MY      = 28
ROWS    = 7

def cx(col): return MX + col * STEP + CELL // 2
def cy(row): return MY + row * STEP + CELL // 2

# ── Snake path: boustrophedon zigzag col by col ──────────────────────────────
def make_path(num_cols):
    path = []
    for c in range(num_cols):
        rows = range(ROWS) if c % 2 == 0 else range(ROWS - 1, -1, -1)
        for r in rows:
            path.append((c, r))
    return path

# ── Simulate growing snake ───────────────────────────────────────────────────
def simulate(path, food_cells, init_len=4):
    frames = []
    body   = []
    eaten  = set()
    for pos in path:
        body.insert(0, pos)
        if pos in food_cells and pos not in eaten:
            eaten.add(pos)
        else:
            max_len = init_len + len(eaten)
            body = body[:max_len]
        frames.append(list(body))
    return frames

# ── Color maps ───────────────────────────────────────────────────────────────
LIGHT_MAP = {
    "#ebedf0": "#ebedf0",
    "#9be9a8": "#9be9a8",
    "#40c463": "#40c463",
    "#30a14e": "#30a14e",
    "#216e39": "#216e39",
}
DARK_MAP = {
    "#ebedf0": "#161b22",
    "#9be9a8": "#0e4429",
    "#40c463": "#006d32",
    "#30a14e": "#26a641",
    "#216e39": "#39d353",
}

def map_color(color, dark):
    return (DARK_MAP if dark else LIGHT_MAP).get(color, color)

# ── Generate SVG ─────────────────────────────────────────────────────────────
def generate_svg(grid, dark=False):
    num_cols = len(grid)
    W = MX * 2 + num_cols * STEP
    H = MY + ROWS * STEP + MX

    bg      = "#0d1117" if dark else "#ffffff"
    txt_col = "#8b949e" if dark else "#57606a"
    empty_c = "#161b22" if dark else "#ebedf0"
    snake_c = "#3fb950" if dark else "#26a641"
    head_c  = "#58e06a" if dark else "#39d353"
    eye_c   = "#0d1117" if dark else "#ffffff"

    path       = make_path(num_cols)
    food_cells = {(c, r) for c, col in enumerate(grid) for r, d in enumerate(col) if d["count"] > 0}
    frames     = simulate(path, food_cells)

    total_frames = len(frames)
    spf          = 0.06
    total_dur    = total_frames * spf

    keyTimes = ";".join(f"{i/(total_frames-1):.5f}" for i in range(total_frames))

    # month labels
    seen, labels = set(), []
    for c, col in enumerate(grid):
        if col:
            m = col[0]["date"][5:7]
            if m not in seen:
                seen.add(m)
                name = datetime.strptime(col[0]["date"], "%Y-%m-%d").strftime("%b")
                labels.append((c, name))

    # when is each food cell eaten?
    eat_frame = {}
    for fi, body in enumerate(frames):
        pos = body[0]
        if pos in food_cells and pos not in eat_frame:
            eat_frame[pos] = fi

    svg = []
    svg.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">')
    svg.append(f'<rect width="{W}" height="{H}" fill="{bg}" rx="6"/>')
    svg.append('''<defs>
  <filter id="hglow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="sglow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>''')

    for c, name in labels:
        svg.append(f'<text x="{MX + c*STEP}" y="{MY-6}" font-size="9" '
                   f'fill="{txt_col}" font-family="monospace">{name}</text>')

    # grid cells
    for c, col in enumerate(grid):
        for r, day in enumerate(col):
            x = MX + c * STEP
            y = MY + r * STEP
            color = map_color(day["color"] if day["count"] > 0 else "#ebedf0", dark)
            if (c, r) in food_cells:
                fi = eat_frame.get((c, r), total_frames)
                t0 = fi / (total_frames - 1)
                t1 = min((fi + 1) / (total_frames - 1), 1.0)
                kts  = f"0;{t0:.5f};{t1:.5f};1"
                vals = "1;1;0;0"
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                    f'<animate attributeName="opacity" dur="{total_dur:.2f}s" repeatCount="indefinite" '
                    f'keyTimes="{kts}" values="{vals}" calcMode="discrete"/>'
                    f'</rect>'
                )
            else:
                svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{empty_c}"/>')

    # snake segments
    max_len = 4 + len(food_cells)
    anim_base = f'dur="{total_dur:.2f}s" repeatCount="indefinite" keyTimes="{keyTimes}" calcMode="discrete"'
    ix, iy = cx(*frames[0][0]), cy(*frames[0][0])

    for seg in range(max_len):
        is_head = seg == 0
        xs, ys, ops, rs = [], [], [], []
        for body in frames:
            if seg < len(body):
                xs.append(str(cx(body[seg][0])))
                ys.append(str(cy(body[seg][1])))
                ops.append("1")
                rs.append("5" if is_head else "4")
            else:
                xs.append(str(cx(body[0][0])))
                ys.append(str(cy(body[0][1])))
                ops.append("0")
                rs.append("5" if is_head else "4")

        fill = head_c if is_head else snake_c
        filt = ' filter="url(#hglow)"' if is_head else ' filter="url(#sglow)"'

        svg.append(
            f'<circle cx="{ix}" cy="{iy}" r="4" fill="{fill}"{filt} opacity="0">'
            f'<animate attributeName="cx" {anim_base} values="{";".join(xs)}"/>'
            f'<animate attributeName="cy" {anim_base} values="{";".join(ys)}"/>'
            f'<animate attributeName="opacity" {anim_base} values="{";".join(ops)}"/>'
            f'<animate attributeName="r" {anim_base} values="{";".join(rs)}"/>'
            f'</circle>'
        )

        # eyes on head
        if is_head:
            for ex_off, ey_off in [(1.5, -1.5), (1.5, 1.5)]:
                exs = [str(cx(b[0][0]) + ex_off) for b in frames]
                eys = [str(cy(b[0][1]) + ey_off) for b in frames]
                svg.append(
                    f'<circle cx="{ix}" cy="{iy}" r="1.2" fill="{eye_c}" opacity="0">'
                    f'<animate attributeName="cx" {anim_base} values="{";".join(exs)}"/>'
                    f'<animate attributeName="cy" {anim_base} values="{";".join(eys)}"/>'
                    f'<animate attributeName="opacity" {anim_base} values="{";".join(ops)}"/>'
                    f'</circle>'
                )

    svg.append('</svg>')
    return "\n".join(svg)


if __name__ == "__main__":
    print(f"Fetching contributions for {GITHUB_USER}...")
    grid = fetch_contributions()
    print(f"  {len(grid)} weeks fetched")
    os.makedirs("dist", exist_ok=True)

    with open("dist/github-contribution-grid-snake.svg", "w") as f:
        f.write(generate_svg(grid, dark=False))
    print("✅ dist/github-contribution-grid-snake.svg")

    with open("dist/github-snake-dark.svg", "w") as f:
        f.write(generate_svg(grid, dark=True))
    print("✅ dist/github-snake-dark.svg")
