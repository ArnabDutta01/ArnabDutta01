#!/usr/bin/env python3
"""Render assets/duel.gif: an anime-style energy fight drawn as a glyph matrix.

Each frame is drawn as a hidden high-resolution scene (Pillow), averaged down to one value per cell,
then every cell becomes a glyph (0 1 X > $ / and solid blocks) on a dim dot grid.
Two original fighters: power-up -> dash -> clash -> rapid teleport exchange -> beam struggle -> explosion.

  python3 assets/src/duel_gif.py          # needs Pillow and numpy; writes assets/duel.gif
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

COLS, ROWS = 112, 44          # glyph grid
CW, CH = 8, 10                # output pixels per cell
SSX, SSY = 4, 5               # hidden-canvas pixels per cell (same 4:5 shape as an output cell)
CWID, CHEI = COLS * SSX, ROWS * SSY
FRAMES, FRAME_MS = 100, 70
SEED = 7

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

PALETTE = [
    (8, 9, 12),       # 0 background
    (30, 33, 42),     # 1 dot grid
    (62, 66, 78),     # 2 dim glyph
    (128, 133, 146),  # 3 mid glyph
    (220, 223, 230),  # 4 bright glyph
    (255, 255, 255),  # 5 white block
    (40, 104, 255),   # 6 blue block      (hero energy)
    (138, 180, 255),  # 7 light blue glyph
    (139, 92, 246),   # 8 violet block    (rival energy)
    (196, 181, 253),  # 9 light violet glyph
    (232, 235, 242),  # 10 flash background
    (26, 28, 34),     # 11 flash glyph
]
GLYPHS = ["dot", "/", ".", "'", "$", ">", "0", "1", "X", "block"]
G = {g: i for i, g in enumerate(GLYPHS)}

# Poses: joint positions, x forward (towards the opponent), y up is negative, feet at y=0.
POSES = {
    "stance": dict(head=(4, -88), neck=(2, -77), hip=(-2, -46), eA=(14, -64), hA=(24, -72), eB=(-4, -60), hB=(8, -62),
                   kA=(12, -24), fA=(20, 0), kB=(-12, -22), fB=(-20, 0)),
    "charge": dict(head=(0, -90), neck=(0, -79), hip=(0, -46), eA=(15, -62), hA=(17, -47), eB=(-15, -62), hB=(-17, -47),
                   kA=(10, -22), fA=(16, 0), kB=(-10, -22), fB=(-16, 0)),
    "dash": dict(head=(26, -72), neck=(18, -66), hip=(-14, -48), eA=(36, -66), hA=(52, -66), eB=(4, -56), hB=(-6, -50),
                 kA=(-30, -40), fA=(-48, -36), kB=(-26, -30), fB=(-44, -22)),
    "punch": dict(head=(8, -86), neck=(4, -76), hip=(-4, -46), eA=(24, -74), hA=(44, -74), eB=(-10, -62), hB=(-2, -56),
                  kA=(14, -24), fA=(26, -2), kB=(-14, -22), fB=(-24, 0)),
    "kick": dict(head=(-8, -84), neck=(-6, -74), hip=(0, -46), eA=(4, -62), hA=(14, -68), eB=(-16, -60), hB=(-24, -66),
                 kA=(22, -52), fA=(46, -62), kB=(-6, -22), fB=(-12, 0)),
    "hit": dict(head=(-14, -80), neck=(-8, -72), hip=(2, -46), eA=(4, -80), hA=(-6, -92), eB=(-18, -62), hB=(-28, -70),
                kA=(12, -22), fA=(18, 0), kB=(-6, -22), fB=(-4, 0)),
    "beam": dict(head=(6, -78), neck=(2, -68), hip=(-8, -40), eA=(18, -60), hA=(34, -58), eB=(16, -55), hB=(32, -53),
                 kA=(14, -20), fA=(26, 0), kB=(-22, -18), fB=(-36, 0)),
}
HAIR = [(-10, 2), (-24, -4), (-12, -7), (-21, -19), (-6, -13), (-4, -26), (4, -13), (13, -21), (10, -6), (14, 1)]

HERO_X, RIVAL_X, HOME_Y = 92, CWID - 92, 188


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in(t):
    return t * t


def ease_out(t):
    return 1 - (1 - t) ** 2


class Canvas:
    """Hidden scene: body (white), two energy colours, motion trails and a white-hot layer."""

    def __init__(self):
        self.layers = {k: Image.new("L", (CWID, CHEI), 0) for k in ("body", "blue", "violet", "trail", "hot")}
        self.draw = {k: ImageDraw.Draw(v) for k, v in self.layers.items()}

    def fighter(self, layer, pose, x, y, face, value=255, s=1.0):
        d = self.draw[layer]
        P = {k: (x + face * px * s, y + py * s) for k, (px, py) in POSES[pose].items()}

        def limb(a, b, w):
            w = max(1, int(w * s))
            d.line([P[a], P[b]], fill=value, width=w)
            bx, by = P[b]
            d.ellipse([bx - w / 2, by - w / 2, bx + w / 2, by + w / 2], fill=value)

        sh = (P["neck"][0], P["neck"][1] + 4 * s)
        P["sh"] = sh
        limb("neck", "hip", 15)
        d.ellipse([sh[0] - 11 * s, sh[1] - 5 * s, sh[0] + 11 * s, sh[1] + 9 * s], fill=value)  # chest
        for e, h in (("eA", "hA"), ("eB", "hB")):
            limb("sh", e, 7)
            limb(e, h, 6)
            hx, hy = P[h]
            d.ellipse([hx - 4.5 * s, hy - 4.5 * s, hx + 4.5 * s, hy + 4.5 * s], fill=value)  # fist
        for k, f in (("kA", "fA"), ("kB", "fB")):
            limb("hip", k, 9)
            limb(k, f, 8)
        hx, hy = P["head"]
        d.ellipse([hx - 9 * s, hy - 10 * s, hx + 9 * s, hy + 9 * s], fill=value)
        d.polygon([(hx + face * px * s, hy + py * s) for px, py in HAIR], fill=value)
        return P

    def burst(self, layer, cx, cy, r, value=255, rays=10, rng=None):
        d = self.draw[layer]
        rng = rng or random
        for i in range(rays):
            a = i * 2 * math.pi / rays + rng.uniform(-0.2, 0.2)
            ln = r * rng.uniform(0.6, 1.4)
            d.line([(cx, cy), (cx + math.cos(a) * ln, cy + math.sin(a) * ln)], fill=value, width=3)
        d.ellipse([cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35], fill=value)

    def ring(self, layer, cx, cy, r, value=255, width=4):
        self.draw[layer].ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], outline=value, width=width)

    def disc(self, layer, cx, cy, r, value=255):
        self.draw[layer].ellipse([cx - r, cy - r, cx + r, cy + r], fill=value)

    def beam(self, layer, x0, x1, y, w, core_w):
        lo, hi = min(x0, x1), max(x0, x1)
        self.draw[layer].rectangle([lo, y - w / 2, hi, y + w / 2], fill=210)
        self.draw["hot"].rectangle([lo, y - core_w / 2, hi, y + core_w / 2], fill=255)

    def speed_lines(self, x, y, face, rng, n=7):
        for _ in range(n):
            yy = y - rng.uniform(10, 90)
            ln = rng.uniform(30, 90)
            x0 = x - face * rng.uniform(15, 40)
            self.draw["trail"].line([(x0, yy), (x0 - face * ln, yy)], fill=150, width=2)

    def aura(self, layer, body_layer_img, strength, f, rng):
        """Rising flame field around the silhouette in `body_layer_img`."""
        if strength <= 0:
            return
        m = body_layer_img.filter(ImageFilter.MaxFilter(13))
        arr = np.asarray(m, dtype=np.float32) / 255
        acc = arr.copy()
        for k in range(1, 6):
            acc = np.maximum(acc, np.roll(arr, -6 * k, axis=0) * (1 - k * 0.15))
        noise = np.asarray(
            Image.fromarray((np.random.default_rng(SEED + f).random((CHEI // 8, CWID // 6)) * 255).astype(np.uint8))
            .resize((CWID, CHEI), Image.BILINEAR), dtype=np.float32) / 255
        flame = acc * (noise > 0.45) * strength * 200
        cur = np.asarray(self.layers[layer], dtype=np.float32)
        self.layers[layer] = Image.fromarray(np.maximum(cur, flame).astype(np.uint8))
        self.draw[layer] = ImageDraw.Draw(self.layers[layer])

    def cells(self):
        out = {}
        for k, img in self.layers.items():
            if k in ("blue", "violet", "hot"):
                glow = img.filter(ImageFilter.GaussianBlur(3))
                img = Image.fromarray(np.maximum(np.asarray(img), (np.asarray(glow) * 0.9).astype(np.uint8)))
            out[k] = np.asarray(img.resize((COLS, ROWS), Image.BOX), dtype=np.float32) / 255
        return out


def scene(f, rng, state):
    """Draw frame f. Returns (canvas, effects dict)."""
    c = Canvas()
    fx = dict(shake=(0, 0), lift=0.0, invert=False)
    contact = (CWID / 2, HOME_Y - 74)

    def solo(pose, x, y, face):
        img = Image.new("L", (CWID, CHEI), 0)
        tmp = Canvas()
        tmp.layers["body"] = img
        tmp.draw["body"] = ImageDraw.Draw(img)
        P = tmp.fighter("body", pose, x, y, face)
        return img, P

    def particles_step():
        alive = []
        for p in state["parts"]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += p.get("g", 0)
            p["life"] -= 1
            if p["life"] > 0 and 0 <= p["x"] < CWID and 0 <= p["y"] < CHEI:
                sz = p.get("sz", 2)
                c.draw[p["layer"]].rectangle([p["x"], p["y"], p["x"] + sz, p["y"] + sz], fill=255)
                alive.append(p)
        state["parts"] = alive

    def spawn(x, y, n, layer, speed=6, life=8, g=0.0, sz=2):
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            v = rng.uniform(0.3, 1) * speed
            state["parts"].append(dict(x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v * 0.7,
                                       life=rng.randint(life // 2, life), layer=layer, g=g, sz=sz))

    if f < 15:  # power-up
        a = ease_out(f / 14)
        for x, face, en in ((HERO_X, 1, "blue"), (RIVAL_X, -1, "violet")):
            img, _ = solo("charge", x, HOME_Y, face)
            c.aura(en, img, a, f, rng)
            c.fighter("body", "charge", x, HOME_Y, face)
            if rng.random() < 0.7:
                state["parts"].append(dict(x=x + rng.uniform(-25, 25), y=HOME_Y - rng.uniform(0, 40), vx=0,
                                           vy=-rng.uniform(4, 8), life=6, layer=en))
        if f >= 10:
            fx["shake"] = (rng.choice((-1, 1)), 0)
        if f == 14:
            fx["lift"] = 0.15

    elif f < 23:  # dash with afterimages
        t = ease_in((f - 15) / 7)
        hx, rx = lerp(HERO_X, contact[0] - 52, t), lerp(RIVAL_X, contact[0] + 52, t)
        y = lerp(HOME_Y, HOME_Y - 6, t)
        for k in (1, 2, 3):
            tk = ease_in(max(0, (f - 15 - k) / 7))
            c.fighter("trail", "dash", lerp(HERO_X, contact[0] - 52, tk), y, 1, value=200 - 45 * k)
            c.fighter("trail", "dash", lerp(RIVAL_X, contact[0] + 52, tk), y, -1, value=200 - 45 * k)
        c.fighter("body", "dash", hx, y, 1)
        c.fighter("body", "dash", rx, y, -1)
        c.speed_lines(hx, y, 1, rng)
        c.speed_lines(rx, y, -1, rng)

    elif f < 27:  # clash
        k = f - 23
        c.fighter("body", "punch", contact[0] - 46, HOME_Y, 1)
        c.fighter("body", "punch", contact[0] + 46, HOME_Y, -1)
        if k == 0:
            fx["invert"] = True
            spawn(*contact, 45, "hot", speed=14, life=12, g=0.4)
        c.burst("hot", *contact, 34 - 6 * k, rng=rng)
        c.ring("trail", *contact, 18 + 30 * k, value=220, width=5)
        c.ring("blue", contact[0] - 4, contact[1], 10 + 26 * k, value=180, width=3)
        c.ring("violet", contact[0] + 4, contact[1], 8 + 24 * k, value=180, width=3)
        fx["shake"] = ((-2, 1), (2, -1), (-1, 1), (1, 0))[k]
        fx["lift"] = 0.2 if k == 1 else 0.0

    elif f < 47:  # rapid teleport exchange
        i, sub = divmod(f - 27, 4)
        if "hits" not in state:
            hrng = random.Random(SEED)
            state["hits"] = [(hrng.uniform(150, 300), hrng.uniform(80, 125)) for _ in range(5)]
        cx, cy = state["hits"][i]
        attacker = "hero" if i % 2 == 0 else "rival"
        move = ("punch", "kick")[i % 3 == 2]
        afce = 1 if attacker == "hero" else -1
        hand = POSES[move]["fA" if move == "kick" else "hA"]
        ax, ay = cx - afce * hand[0], cy - hand[1]
        dx, dy = cx + afce * 16, cy + 80
        layer = "trail" if sub == 3 else "body"
        val = 120 if sub == 3 else 255
        c.fighter(layer, move, ax, ay, afce, value=val)
        c.fighter(layer, "hit", dx, dy, -afce, value=val)
        if sub == 0:
            px, py = state["hits"][i - 1] if i else contact
            c.draw["trail"].line([(px, py), (cx, cy)], fill=170, width=10)
            c.burst("hot", cx, cy, 30, rng=rng)
            spawn(cx, cy, 20, "hot", speed=10, life=8)
            fx["lift"] = 0.18
            fx["shake"] = (rng.choice((-1, 1)), rng.choice((-1, 1)))
        elif sub == 1:
            c.ring("hot", cx, cy, 22, value=230, width=3)
            c.burst("blue" if attacker == "hero" else "violet", cx, cy, 20, value=200, rng=rng)

    elif f < 59:  # knockback, then charge beams
        t = (f - 47) / 11
        hx, rx = lerp(contact[0] - 70, HERO_X - 12, ease_out(t)), lerp(contact[0] + 70, RIVAL_X + 12, ease_out(t))
        y = lerp(HOME_Y - 20, HOME_Y, ease_out(t))
        pose = "hit" if f < 50 else "beam"
        for x, face, en in ((hx, 1, "blue"), (rx, -1, "violet")):
            if pose == "beam":
                img, P = solo("beam", x, y, face)
                c.aura(en, img, 0.6, f, rng)
                ox, oy = P["hA"][0] + face * 6, P["hA"][1] + 2
                r = 3 + 11 * (f - 50) / 8
                c.disc(en, ox, oy, r)
                c.disc("hot", ox, oy, r * 0.45)
                for _ in range(3):  # sparks pulled into the orb
                    a = rng.uniform(0, 2 * math.pi)
                    state["parts"].append(dict(x=ox + math.cos(a) * 40, y=oy + math.sin(a) * 30, vx=-math.cos(a) * 9,
                                               vy=-math.sin(a) * 7, life=4, layer=en))
            else:
                c.fighter("trail", "hit", x - face * 18, y, face, value=140)
            c.fighter("body", pose, x, y, face)
        state["beam_y"] = y

    elif f < 81:  # beam struggle
        y = HOME_Y
        k = f - 59
        _, Ph = solo("beam", HERO_X - 12, y, 1)
        _, Pr = solo("beam", RIVAL_X + 12, y, -1)
        hpx, hpy = Ph["hA"][0] + 6, Ph["hA"][1] + 2
        rpx, rpy = Pr["hA"][0] - 6, Pr["hA"][1] + 2
        mx = CWID / 2 + 22 * math.sin(max(0, k - 5) / 3.2)
        ext = min(1, k / 4)
        w = 13 + 4 * math.sin(f * 1.7)
        c.beam("blue", hpx, lerp(hpx, mx, ext), hpy, w, 4)
        c.beam("violet", rpx, lerp(rpx, mx, ext), rpy, w + 2 * math.cos(f * 1.3), 4)
        for x, face, en in ((HERO_X - 12, 1, "blue"), (RIVAL_X + 12, -1, "violet")):
            img, _ = solo("beam", x, y, face)
            c.aura(en, img, 0.75, f, rng)
            c.fighter("body", "beam", x, y, face)
        if ext >= 1:
            r = 16 + 7 * abs(math.sin(f * 0.9))
            c.disc("blue", mx - 4, hpy, r + 4)
            c.disc("violet", mx + 4, hpy, r + 2)
            c.disc("hot", mx, hpy, r * 0.7)
            spawn(mx, hpy, 6, "hot", speed=12, life=7)
            c.burst("hot", mx, hpy, r * 1.8, value=200, rays=8, rng=rng)
            fx["shake"] = (rng.choice((-1, 0, 1)), rng.choice((-1, 0, 1)))
            if k % 5 == 0:
                fx["lift"] = 0.15
        state["mx"], state["my"] = mx, hpy

    elif f < 89:  # explosion
        k = f - 81
        mx, my = state.get("mx", CWID / 2), state.get("my", HOME_Y - 56)
        if k == 0:
            fx["invert"] = True
            spawn(mx, my, 60, "hot", speed=18, life=14, g=0.3, sz=3)
        r = 22 + 26 * k
        c.disc("hot", mx, my, r, value=max(60, 255 - 22 * k))
        c.ring("trail", mx, my, r + 22, value=230, width=8)
        c.ring("blue", mx, my, r + 8, value=200, width=5)
        c.ring("violet", mx, my, r + 14, value=200, width=5)
        if k < 3:
            c.fighter("trail", "hit", HERO_X - 20 - 8 * k, HOME_Y, 1, value=160)
            c.fighter("trail", "hit", RIVAL_X + 20 + 8 * k, HOME_Y, -1, value=160)
        fx["lift"] = 0.0 if k == 0 else max(0, 0.2 - 0.04 * k)
        fx["shake"] = (rng.choice((-2, 2)), rng.choice((-1, 1))) if k < 5 else (0, 0)

    else:  # smoke clears back to the grid
        k = f - 89
        lo = np.random.default_rng(SEED).random((ROWS // 4 + 2, COLS // 6 + 2)) * 255
        blob = np.asarray(Image.fromarray(lo.astype(np.uint8)).resize((COLS + 12, ROWS + 8), Image.BILINEAR),
                          dtype=np.float32) / 255
        blob = blob[8 - min(8, k):8 - min(8, k) + ROWS, k:k + COLS]          # drift up and sideways
        yy, xx = np.mgrid[0:ROWS, 0:COLS]
        mx, my = state.get("mx", CWID / 2) / SSX, state.get("my", HOME_Y - 56) / SSY
        fall = np.clip(1 - np.hypot((xx - mx) / 40, (yy - my) / 18), 0, 1)
        state["smoke"] = np.clip(blob * 1.6 - 0.5, 0, 1) * fall
        state["smoke_level"] = max(0.0, 0.8 - 0.08 * k)

    particles_step()
    return c, fx


def glyph_tiles():
    font = ImageFont.truetype(FONT, 10)
    tiles = []
    for g in GLYPHS:
        im = Image.new("1", (CW, CH), 0)
        d = ImageDraw.Draw(im)
        if g == "dot":
            d.point((CW // 2, CH // 2), fill=1)
        elif g == "block":
            d.rectangle([1, 2, CW - 2, CH - 2], fill=1)
        else:
            d.text((CW / 2, CH / 2), g, font=font, fill=1, anchor="mm")
        tiles.append(np.asarray(im, dtype=bool))
    return np.stack(tiles)


def shift(a, dy, dx):
    """Move a grid by (dy, dx) cells without wrapping around the edges."""
    out = np.zeros_like(a)
    h, w = a.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
    return out


def to_glyphs(cells, fx, choice, rng_np, state):
    body, blue, violet, trail, hot = (cells[k] for k in ("body", "blue", "violet", "trail", "hot"))
    v = np.maximum.reduce([body, blue, violet, hot, trail * 0.55])
    if "smoke" in state and state.get("smoke_level", 0) > 0:
        v = np.maximum(v, state["smoke"] * state["smoke_level"])
    jitter = rng_np.normal(0, 0.06, v.shape)
    v = np.clip(v + jitter * (v > 0.05), 0, 1)
    if fx["lift"] and not fx["invert"]:
        v = np.clip(v + fx["lift"] * rng_np.random(v.shape) ** 3 * 1.6, 0, 1)
    dy, dx = fx["shake"]
    v = shift(v, dy, dx)
    blue_d = shift((blue > body) & (blue >= violet) & (blue > hot * 0.8), dy, dx)
    violet_d = shift((violet > body) & (violet > blue) & (violet > hot * 0.8), dy, dx)

    glyph = np.full(v.shape, G["dot"])
    color = np.full(v.shape, 1)
    sets = [
        (0.07, 0.20, ["/", ".", "'", "/"], 2, 2, 2),
        (0.20, 0.40, ["$", "/", ">", "$"], 3, 7, 9),
        (0.40, 0.66, ["0", "1", "X", ">"], 4, 7, 9),
        (0.66, 1.01, ["block", "block", "block", "0", "X", "1"], 5, 6, 8),
    ]
    for lo, hi, chars, cn, cb, cv in sets:
        m = (v >= lo) & (v < hi)
        idx = (choice * len(chars)).astype(int) % len(chars)
        ids = np.array([G[ch] for ch in chars])[idx]
        glyph = np.where(m, ids, glyph)
        col = np.where(blue_d, cb, np.where(violet_d, cv, cn))
        color = np.where(m, col, color)
    # light glyphs on energy: blocks keep the strong colour, characters use the light one
    color = np.where((glyph != G["block"]) & (color == 6), 7, color)
    color = np.where((glyph != G["block"]) & (color == 8), 9, color)
    bg = 0
    if fx["invert"]:
        bg = 10
        color = np.where(np.isin(color, (6, 7, 8, 9)), color, 11)
        color = np.where(glyph == G["dot"], 3, color)
    return glyph, color, bg


def main():
    rng = random.Random(SEED)
    rng_np = np.random.default_rng(SEED)
    tiles = glyph_tiles()
    choice = rng_np.random((ROWS, COLS))
    state = {"parts": []}
    pal = sum(PALETTE, ()) + (0, 0, 0) * (256 - len(PALETTE))
    frames = []
    for f in range(FRAMES):
        reroll = rng_np.random((ROWS, COLS)) < 0.3
        choice = np.where(reroll, rng_np.random((ROWS, COLS)), choice)
        canvas, fx = scene(f, rng, state)
        glyph, color, bg = to_glyphs(canvas.cells(), fx, choice, rng_np, state)
        mask = tiles[glyph]                                   # ROWS, COLS, CH, CW
        pix = np.where(mask, color[:, :, None, None], bg).astype(np.uint8)
        pix = pix.transpose(0, 2, 1, 3).reshape(ROWS * CH, COLS * CW)
        im = Image.fromarray(pix, "P")
        im.putpalette(pal)
        frames.append(im)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "duel.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0, disposal=1, optimize=False)
    print(f"wrote {os.path.normpath(out)}: {COLS * CW}x{ROWS * CH}, {FRAMES} frames, {os.path.getsize(out) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
