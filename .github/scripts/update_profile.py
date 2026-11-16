#!/usr/bin/env python3
"""Refresh the open-source PR list in README.md and redraw the pixel pet.

Run by .github/workflows/profile.yml. Uses only the standard library.

  GITHUB_TOKEN    token for the search API (the workflow's default token is enough)
  PROFILE_USER    GitHub login (default: ArnabDutta01)
  EXCLUDE_REPOS   comma-separated owner/name list left out of the list and the count

Local preview without touching the network:
  python3 .github/scripts/update_profile.py --pet-only 12   # draw the pet at 12 merged PRs
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

USER = os.environ.get("PROFILE_USER", "ArnabDutta01")
EXCLUDE = {
    r.strip().lower()
    for r in os.environ.get("EXCLUDE_REPOS", "firstcontributions/first-contributions").split(",")
    if r.strip()
}
MAX_ROWS = 6
README = "README.md"
PET_FILE = "assets/pet.svg"
START, END = "<!-- PRS:START -->", "<!-- PRS:END -->"

# --------------------------------------------------------------------------- GitHub


def search(query):
    """Return every issue-search item for `query` (the API caps this at 1000)."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-updater"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    items, page = [], 1
    while True:
        params = urllib.parse.urlencode({"q": query, "per_page": 100, "page": page})
        req = urllib.request.Request("https://api.github.com/search/issues?" + params, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        items += data["items"]
        if not data["items"] or len(items) >= min(data["total_count"], 1000):
            return items
        page += 1


def repo_of(item):
    return item["repository_url"].split("/repos/", 1)[1]


def fetch_prs(state):
    items = search(f"is:pr is:{state} author:{USER} -user:{USER}")
    return [i for i in items if repo_of(i).lower() not in EXCLUDE]


# --------------------------------------------------------------------------- README


def md_escape(text):
    return re.sub(r"([\\`*_\[\]<>|])", r"\\\1", text)


def pr_line(item, when):
    ref = f"{repo_of(item)}#{item['number']}"
    return f"- [{ref}]({item['html_url']}) {md_escape(item['title'])}{when}"


def render_block(merged, open_):
    merged.sort(key=lambda i: i["pull_request"]["merged_at"] or i["closed_at"], reverse=True)
    open_.sort(key=lambda i: i["created_at"], reverse=True)
    projects = len({repo_of(i) for i in merged})
    lines = [
        START,
        f"**{len(merged)} merged** across {projects} project{'s' if projects != 1 else ''}"
        f" · **{len(open_)} in review**",
        "",
        "**Recently merged**",
        "",
    ]
    if merged:
        lines += [
            pr_line(i, f" · merged {(i['pull_request']['merged_at'] or i['closed_at'])[:10]}")
            for i in merged[:MAX_ROWS]
        ]
    else:
        lines.append("_Nothing yet._")
    lines += ["", "**In review**", ""]
    if open_:
        lines += [pr_line(i, f" · opened {i['created_at'][:10]}") for i in open_[:MAX_ROWS]]
    else:
        lines.append("_Nothing open right now._")
    lines.append(END)
    return "\n".join(lines)


def update_readme(block):
    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"{README}: markers {START} / {END} not found")
    new = pattern.sub(lambda _: block, text, count=1)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)


# --------------------------------------------------------------------------- pixel pet

PET_NAME = "PATCH"

# (merged PRs needed, stage name). Thresholds follow the playbook milestones.
STAGES = [(0, "Egg"), (1, "Cracked egg"), (5, "Hatchling"), (10, "Bitling"), (25, "Sprout"), (40, "Legend")]

PALETTE = {
    "o": "#2e1065",  # body outline
    "b": "#a78bfa",  # body
    "h": "#ddd6fe",  # body highlight
    "e": "#1e1b4b",  # eye
    "w": "#ffffff",  # eye shine
    "k": "#f472b6",  # cheek
    "m": "#1e1b4b",  # mouth
    "f": "#7c3aed",  # feet
    "O": "#57534e",  # shell outline
    "s": "#f5f5f4",  # shell
    "H": "#ffffff",  # shell highlight
    "p": "#c4b5fd",  # shell speckle
    "c": "#44403c",  # crack
    "g": "#166534",  # stem
    "l": "#4ade80",  # leaf
    "y": "#fbbf24",  # crown
    "Y": "#b45309",  # crown shade
    "r": "#f43f5e",  # crown jewel
}

EGG = [
    "................",
    "................",
    "......OOOO......",
    ".....OssssO.....",
    "....OsHssssO....",
    "...OsHssssssO...",
    "...OsHsspsssO...",
    "..OssssssssssO..",
    "..OssspssssssO..",
    "..OssssssspssO..",
    "..OssssssssssO..",
    "..OsspsssssssO..",
    "...OssssssssO...",
    "....OssssssO....",
    ".....OOOOOO.....",
    "................",
]

CRACK = [  # drawn over EGG
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "....c.c.c.c.c...",
    "...c.c.c.c.c....",
    "........c.......",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

BLOB = [
    "................",
    "................",
    "................",
    ".....oooooo.....",
    "....obbbbbbo....",
    "...obhhbbbbbo...",
    "..obhbbbbbbbbo..",
    "..obbeebbeebbo..",
    "..obbewbbewbbo..",
    "..obkbbbbbbkbo..",
    "..obbbbmmbbbbo..",
    "..obbbbbbbbbbo..",
    "...obbbbbbbbo...",
    "....oooooooo....",
    "....ff....ff....",
    "................",
]

SHELL = [  # bottom eggshell for the hatchling, drawn over BLOB
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "..O.O.O..O.O.O..",
    "..OsOsOOOsOsOO..",
    "..OssspsssssOO..",
    "..OsssssssspsO..",
    "...OssssssssO...",
    "....OOOOOOOO....",
    "................",
]

SPROUT = [
    "........ll......",
    "......llgl......",
    ".......lg.......",
    "........g.......",
] + ["................"] * 12

CROWN = [
    "................",
    ".....y..y..y....",
    ".....yyyyyyy....",
    ".....YYrYYYY....",
] + ["................"] * 12

for _art in (EGG, CRACK, BLOB, SHELL, SPROUT, CROWN):
    assert len(_art) == 16 and all(len(r) == 16 for r in _art), "sprite rows must be 16x16"


def layers_for(stage):
    """Return (sprite rows, animation class) for a stage index."""
    if stage == 0:
        return [EGG], "wobble"
    if stage == 1:
        return [EGG, CRACK], "wobble fast"
    if stage == 2:
        return [BLOB, SHELL], "bob"
    if stage == 3:
        return [BLOB], "bob"
    if stage == 4:
        return [BLOB, SPROUT], "bob"
    return [BLOB, CROWN], "bob"


def pixels(layers, cell, x0, y0):
    grid = [list(r) for r in layers[0]]
    for layer in layers[1:]:
        for y, row in enumerate(layer):
            for x, ch in enumerate(row):
                if ch != ".":
                    grid[y][x] = ch
    body, eyes = [], []
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            rect = (f'<rect x="{x0 + x * cell}" y="{y0 + y * cell}" '
                    f'width="{cell}" height="{cell}" fill="{PALETTE[ch]}"/>')
            (eyes if ch in "ew" else body).append(rect)
    return "".join(body), "".join(eyes)


def stage_of(merged):
    return max(i for i, (need, _) in enumerate(STAGES) if merged >= need)


def render_pet(merged):
    stage = stage_of(merged)
    name = STAGES[stage][1]
    cell, w, h = 7, 480, 150
    sx, sy = 28, 18
    layers, anim = layers_for(stage)
    body, eyes = pixels(layers, cell, sx, sy)

    if stage + 1 < len(STAGES):
        lo, (hi, next_name) = STAGES[stage][0], STAGES[stage + 1]
        filled = round(10 * (merged - lo) / (hi - lo))
        left = hi - merged
        status = f"{left} more merged PR{'s' if left != 1 else ''} to {next_name}"
    else:
        filled, status = 10, "Max level reached"

    bar_x, bar_y = 176, 98
    bar = "".join(
        f'<rect x="{bar_x + i * 22}" y="{bar_y}" width="18" height="12" '
        f'fill="{"#a78bfa" if i < filled else "#21262d"}"/>'
        for i in range(10)
    )
    sparkles = ""
    if stage == len(STAGES) - 1:
        sparkles = "".join(
            f'<rect class="spark" style="animation-delay:{d}s" x="{x}" y="{y}" width="6" height="6" fill="#fbbf24"/>'
            for x, y, d in ((22, 30, 0), (138, 24, 0.6), (140, 104, 1.2))
        )
    shadow = f'<rect x="{sx + 4 * cell}" y="{sy + 15 * cell + 2}" width="{8 * cell}" height="4" fill="#000" opacity=".35"/>'
    plural = "s" if merged != 1 else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" shape-rendering="crispEdges" role="img" aria-label="{PET_NAME}, a pixel pet at stage {name} with {merged} merged pull request{plural}">
<style>
  text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  .bob {{ animation: bob 1.2s infinite steps(1); }}
  .wobble {{ animation: wobble 1.6s infinite steps(1); }}
  .wobble.fast {{ animation-duration: .8s; }}
  .eyes {{ animation: blink 4s infinite steps(1); transform-box: fill-box; transform-origin: center; }}
  .spark {{ animation: twinkle 1.8s infinite steps(1); }}
  @keyframes bob {{ 0% {{ transform: translateY(0) }} 50% {{ transform: translateY(-{cell}px) }} }}
  @keyframes wobble {{ 0% {{ transform: translateX(0) }} 25% {{ transform: translateX(-{cell}px) }} 50% {{ transform: translateX(0) }} 75% {{ transform: translateX({cell}px) }} }}
  @keyframes blink {{ 0% {{ transform: scaleY(1) }} 94% {{ transform: scaleY(.15) }} 98% {{ transform: scaleY(1) }} }}
  @keyframes twinkle {{ 0% {{ opacity: 1 }} 50% {{ opacity: 0 }} }}
  @media (prefers-reduced-motion: reduce) {{ .bob, .wobble, .eyes, .spark {{ animation: none; }} }}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>
{shadow}
<g class="{anim}">{body}<g class="eyes">{eyes}</g></g>
{sparkles}
<text x="176" y="42" font-size="20" font-weight="700" fill="#e6edf3" letter-spacing="2">{PET_NAME}</text>
<text x="176" y="66" font-size="14" fill="#a78bfa">Lv {stage + 1} · {name}</text>
<text x="176" y="88" font-size="13" fill="#8b949e">{merged} merged PR{plural} in open source</text>
{bar}
<text x="176" y="132" font-size="12" fill="#8b949e">{status}</text>
</svg>
"""


def write_pet(merged):
    os.makedirs(os.path.dirname(PET_FILE), exist_ok=True)
    svg = render_pet(merged)
    try:
        with open(PET_FILE, encoding="utf-8") as f:
            if f.read() == svg:
                return
    except FileNotFoundError:
        pass
    with open(PET_FILE, "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--pet-only":
        write_pet(int(sys.argv[2]))
        return
    merged, open_ = fetch_prs("merged"), fetch_prs("open")
    update_readme(render_block(merged, open_))
    write_pet(len(merged))
    print(f"{len(merged)} merged, {len(open_)} open (excluded: {', '.join(sorted(EXCLUDE)) or 'none'})")


if __name__ == "__main__":
    main()
