import requests
import os
from datetime import datetime

GITHUB_USER  = os.environ.get("GITHUB_USER", "Sam-Dev-161127")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

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

CELL = 10
GAP  = 3
STEP = CELL + GAP
MX   = 16
MY   = 28
ROWS = 7

def get_neighbors(c, r, num_cols):
    """Return valid neighbors in grid."""
    result = []
    for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc, nr = c+dc, r+dr
        if 0 <= nc < num_cols and 0 <= nr < ROWS:
            result.append((nc, nr))
    return result

def make_food_path(food_cells, num_cols):
    """
    Snake always starts from (0,0) top-left corner,
    visits all food cells via greedy nearest-neighbor,
    then returns back to (0,0).
    """
    if not food_cells:
        return [(0, 0)]

    start = (0, 0)  # always top-left corner of grid

    # Walk from (0,0) to first nearest food cell
    path = [start]
    remaining = set(food_cells)
    current = start

    while remaining:
        nearest = min(remaining, key=lambda p: abs(p[0]-current[0]) + abs(p[1]-current[1]))

        # Walk step by step to nearest (col first, then row)
        c, r = current
        tc, tr = nearest
        while c != tc:
            c += 1 if tc > c else -1
            path.append((c, r))
        while r != tr:
            r += 1 if tr > r else -1
            path.append((c, r))

        remaining.discard(nearest)
        current = nearest

    # Return to (0,0)
    c, r = current
    while c != 0:
        c -= 1
        path.append((c, r))
    while r != 0:
        r -= 1
        path.append((c, r))

    return path

def simulate(path, food_cells, init_len=4):
    """Simulate snake moving along path, growing when eating food."""
    frames = []
    body   = []
    eaten  = set()

    for pos in path:
        body.insert(0, pos)
        if pos in food_cells and pos not in eaten:
            eaten.add(pos)
            # grow: don't trim
        else:
            body = body[:init_len + len(eaten)]
        frames.append(list(body))

    return frames

def cell_color(count, api_color, dark):
    if count == 0:
        return "#161b22" if dark else "#ebedf0"
    if not dark:
        return api_color
    if count <= 3:   return "#0e4429"
    elif count <= 6: return "#006d32"
    elif count <= 9: return "#26a641"
    else:            return "#39d353"

def generate_svg(grid, dark=False):
    num_cols = len(grid)
    W = MX * 2 + num_cols * STEP
    H = MY + ROWS * STEP + MX

    bg      = "#0d1117" if dark else "#ffffff"
    txt_col = "#8b949e" if dark else "#57606a"
    empty_c = "#161b22" if dark else "#ebedf0"
    snake_c = "#00ffff" if dark else "#00bcd4"
    head_c  = "#00ffff" if dark else "#00bcd4"

    food_cells = {(c, r) for c, col in enumerate(grid) for r, d in enumerate(col) if d["count"] > 0}
    path       = make_food_path(food_cells, num_cols)

    if not path:
        path = [(0, 0)]

    frames = simulate(path, food_cells)

    total_frames = len(frames)
    total_dur    = total_frames * 0.13
    keyTimes     = ";".join(f"{i/(max(total_frames-1,1)):.5f}" for i in range(total_frames))
    anim_base    = f'dur="{total_dur:.2f}s" repeatCount="indefinite" keyTimes="{keyTimes}" calcMode="discrete"'

    # Month labels
    seen, labels = set(), []
    for c, col in enumerate(grid):
        if col:
            m = col[0]["date"][5:7]
            if m not in seen:
                seen.add(m)
                name = datetime.strptime(col[0]["date"], "%Y-%m-%d").strftime("%b")
                labels.append((c, name))

    # When each food cell is first eaten
    eat_frame = {}
    for fi, body in enumerate(frames):
        pos = body[0]
        if pos in food_cells and pos not in eat_frame:
            eat_frame[pos] = fi

    svg = []
    svg.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">')
    svg.append(f'<rect width="{W}" height="{H}" fill="{bg}" rx="6"/>')

    for c, name in labels:
        svg.append(f'<text x="{MX + c*STEP}" y="{MY-6}" font-size="9" '
                   f'fill="{txt_col}" font-family="monospace">{name}</text>')

    # Grid cells — food animates back when snake loops
    for c, col in enumerate(grid):
        for r, day in enumerate(col):
            x = MX + c * STEP
            y = MY + r * STEP
            color = cell_color(day["count"], day["color"], dark)

            if (c, r) in food_cells:
                fi  = eat_frame.get((c, r), total_frames)
                t0  = fi / (total_frames - 1)
                t1  = min((fi + 1) / (total_frames - 1), 1.0)
                # Food disappears when eaten, reappears at start of loop
                kts   = f"0;{t0:.5f};{t1:.5f};1"
                fills = f"{color};{color};{empty_c};{empty_c}"
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                    f'<animate attributeName="fill" dur="{total_dur:.2f}s" repeatCount="indefinite" '
                    f'keyTimes="{kts}" values="{fills}" calcMode="discrete"/>'
                    f'</rect>'
                )
            else:
                svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{empty_c}"/>')

    # Snake body — square segments, tapering toward tail
    max_len = 4 + len(food_cells)

    for seg in range(max_len):
        xs, ys, ops, szs = [], [], [], []

        for body in frames:
            body_len = len(body)
            if seg < body_len:
                bc, br = body[seg]
                # taper: head = CELL, tail = CELL-4
                frac = seg / max(body_len - 1, 1)
                sz   = max(int(CELL - frac * 4), CELL - 4)
                offset = (CELL - sz) // 2
                xs.append(str(MX + bc * STEP + offset))
                ys.append(str(MY + br * STEP + offset))
                ops.append("1")
                szs.append(str(sz))
            else:
                bc, br = body[0]
                xs.append(str(MX + bc * STEP))
                ys.append(str(MY + br * STEP))
                ops.append("0")
                szs.append(str(CELL))

        is_head = seg == 0
        fill    = head_c if is_head else snake_c
        ix = MX + 0 * STEP  # always start at col 0
        iy = MY + 0 * STEP  # always start at row 0

        svg.append(
            f'<rect x="{ix}" y="{iy}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="{ops[0]}">'
            f'<animate attributeName="x" {anim_base} values="{";".join(xs)}"/>'
            f'<animate attributeName="y" {anim_base} values="{";".join(ys)}"/>'
            f'<animate attributeName="width" {anim_base} values="{";".join(szs)}"/>'
            f'<animate attributeName="height" {anim_base} values="{";".join(szs)}"/>'
            f'<animate attributeName="opacity" {anim_base} values="{";".join(ops)}"/>'
            f'</rect>'
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
