#!/usr/bin/env python3
"""Normalize GitHub stat card SVGs to identical dimensions.

Each card service emits a different intrinsic size (stats 308x165,
streak 495x195, top-langs 300x135, profile-details 700x200), which makes
a 2x2 grid look uneven. This script rebuilds every card on an identical
canvas (default 440x200): the card's own background rect is replaced by
the common one, and the original content is scaled + centered inside.

Usage: normalize_cards.py [out_dir]
Fetches live SVGs unless CARDS_SRC_DIR is set (uses local *.svg files).
"""
import os, re, sys, urllib.request

TARGET_W, TARGET_H = 440, 200
BG_FILL = "#0d1117"
BG_STROKE = "#30363d"
BG_RX = 6

CARDS = {
    "stats":       "https://github-readme-stats.vercel.app/api?username=repowahyuillahi&show_icons=true&hide_title=true&hide_rank=true&bg_color=0d1117&text_color=c9d1d9&icon_color=58a6ff&border_color=30363d&border_radius=6",
    "streak":      "https://github-readme-streak-stats-eight.vercel.app/?user=repowahyuillahi&theme=dark&background=0d1117&border=30363d&stroke=30363d&ring=58a6ff&fire=58a6ff&currStreakNum=c9d1d9&sideNums=8b949e",
    "top-langs":   "https://github-readme-stats.vercel.app/api/top-langs/?username=repowahyuillahi&layout=compact&bg_color=0d1117&text_color=c9d1d9&border_color=30363d&border_radius=6&hide_title=true",
    "details":     "https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=repowahyuillahi&theme=github_dark",
}

# Regex (DOTALL) matching the card's own background rect per service.
BG_PATTERNS = {
    "stats":     r'<rect[^>]*data-testid="card-bg"[^>]*>\s*',
    "streak":    r"<rect[^>]*fill='#0d1117'[^>]*/>\s*",
    "top-langs": r'<rect[^>]*data-testid="card-bg"[^>]*>\s*',
    "details":   r'<rect[^>]*fill="#0d1117"[^>]*>(?:\s*</rect>)?\s*',
}

def fetch(name, url):
    src = os.environ.get("CARDS_SRC_DIR")
    if src:
        local = {"top-langs": "toplangs.svg"}.get(name, name + ".svg")
        with open(os.path.join(src, local), encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def inner_size(svg):
    m = re.search(r'''<svg[^>]*width=["']([\d.]+)(?:px)?["'][^>]*height=["']([\d.]+)(?:px)?["']''', svg)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r'''viewBox=["'][\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)["']''', svg)
    return float(m.group(1)), float(m.group(2))

def normalize(name, svg):
    w, h = inner_size(svg)
    s = min(TARGET_W / w, TARGET_H / h)
    tx = (TARGET_W - w * s) / 2
    ty = (TARGET_H - h * s) / 2

    # Strip outer <svg ...> ... </svg>, keep inner content.
    inner = re.sub(r'^.*?<svg[^>]*>', '', svg, count=1, flags=re.DOTALL)
    inner = re.sub(r'</svg>\s*$', '', inner, flags=re.DOTALL)

    # Remove the card's own background rect (first match only).
    inner, n = re.subn(BG_PATTERNS[name], '', inner, count=1, flags=re.DOTALL)
    assert n == 1, f"bg rect not found exactly once in {name} (found {n})"

    bg = (f'<rect x="0.5" y="0.5" width="{TARGET_W - 1}" height="{TARGET_H - 1}" '
          f'rx="{BG_RX}" fill="{BG_FILL}" stroke="{BG_STROKE}"/>')
    # Kill entrance animations so content is visible immediately
    # (github-readme-stats uses .stagger{opacity:0}; streak uses inline
    #  opacity:0 + fadein animations with delays).
    no_anim = ('<style>'
               '*{animation:none!important}'
               '.stagger{opacity:1!important}'
               '[style*="opacity:0"],[style*="opacity: 0"]{opacity:1!important}'
               '</style>')
    out = (
        f'<svg width="{TARGET_W}" height="{TARGET_H}" viewBox="0 0 {TARGET_W} {TARGET_H}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg" role="img">\n'
        f'{no_anim}\n'
        f'{bg}\n'
        f'<g transform="translate({tx:.2f},{ty:.2f}) scale({s:.4f})">\n'
        f'{inner}\n'
        f'</g>\n</svg>\n'
    )
    return out

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out_dir, exist_ok=True)
    for name, url in CARDS.items():
        svg = fetch(name, url)
        if "<svg" not in svg:
            raise SystemExit(f"fetch failed for {name}: not SVG")
        norm = normalize(name, svg)
        p = os.path.join(out_dir, f"card-{name}.svg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(norm)
        print(f"wrote {p} ({len(norm)} bytes)")

if __name__ == "__main__":
    main()
