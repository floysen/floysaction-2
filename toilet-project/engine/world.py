"""How a hole in your yard becomes a toilet - every set and animation, drawn with cairo.

Three sets, all in the reference videos' fixed cut-away view:
  * yard    - outhouse over a pit (paragraphs 0-1)
  * house   - bathroom cut open with the toilet in section, drain under the slab,
              street and sewer main, vent stack through the roof (most of the video)
  * rooftop - outside view of the roof with the vent pipe (paragraph 12)
"""
import math
import os
import random
import sys

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import shotplan as SP  # noqa: E402
from draw import (W, H, Cam, smooth, lin, pop, lerp, mix, keyed, hexc, shade, alpha, clamp,  # noqa: E402
                  path_poly, fill_poly, set_src, lgrad, rgrad, rounded_rect, sphere, ellipse,
                  cylinder_v, pipe, polyline_point, round_corners, arrow, soft_shadow, ao_strip,
                  box3d, haze, gloss, soil_texture, lawn_texture, cloud_sprite, concrete_texture,
                  tile_texture, wood_texture, asphalt_texture, paint_surface)

E = SP.E
RNDS = random.Random

C = {
    "sky_top": hexc("#6fa8e0"), "sky_low": hexc("#dce9f3"),
    "lawn": hexc("#5c9a2c"), "lawn2": hexc("#4d8a24"),
    "dirt": hexc("#7a5030"), "concrete": hexc("#c8c5bd"), "conc_dark": hexc("#9a968e"),
    "house": hexc("#efe2c8"), "trim": hexc("#b8946a"), "glass": hexc("#3a5f80"), "wood": hexc("#7a4a26"),
    "wall": hexc("#e2cfa9"), "palm": hexc("#3f7a2a"), "trunk": hexc("#8a6a44"),
    "porcelain": hexc("#f6f8fa"), "porc_shade": hexc("#c9d1d9"), "water": hexc("#7fd0f0"), "water_deep": hexc("#2f9ad0"),
    "pvc": hexc("#eef2f5"), "waste": hexc("#6b4423"), "gas": hexc("#8fd14f"), "white": hexc("#ffffff"),
    "tile": hexc("#eef2f5"), "paint": hexc("#dfe9ef"), "band": hexc("#2f6fa8"), "floor1": hexc("#e9ecef"), "floor2": hexc("#9aa5b1"),
    "asphalt": hexc("#2e3136"), "gravel": hexc("#9b958a"), "red": hexc("#e0483a"), "rubber": hexc("#c8352b"),
    "brass": hexc("#d9a440"), "outline": hexc("#1d2733"),
}

_TEX = {}


def tex(name):
    if name not in _TEX:
        f = {"soil": lambda: soil_texture(1200, 1400, seed=3), "lawn": lambda: lawn_texture(800, 400, seed=5),
             "concrete": lambda: concrete_texture(400, 400, seed=9), "tile": lambda: tile_texture(480, 480, tile=60),
             "wood": lambda: wood_texture(300, 400, seed=2), "asphalt": lambda: asphalt_texture(600, 200, seed=4)}
        if name.startswith("cloud"):
            _TEX[name] = cloud_sprite(520, 220, seed=int(name[5:]))
        else:
            _TEX[name] = f[name]()
    return _TEX[name]


def clip_poly(ctx, pts):
    path_poly(ctx, pts)
    ctx.clip()


def tex_fill(ctx, pts, base, name, a=0.5):
    fill_poly(ctx, pts, base)
    ctx.save()
    clip_poly(ctx, pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    paint_surface(ctx, tex(name), min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2, alpha_=a)
    ctx.restore()


def subpath(pts, u0, u1, n=40):
    u0, u1 = clamp(u0), clamp(u1)
    if u1 <= u0:
        return []
    return [polyline_point(pts, lerp(u0, u1, i / n)) for i in range(n + 1)]


# =============================================================== shared scenery
def draw_sky(ctx, t, night=0.0):
    ctx.rectangle(-W, -H, 3 * W, 3 * H)
    ctx.set_source(lgrad(0, 0, 0, 900, [(0, C["sky_top"]), (1, C["sky_low"])]))
    ctx.fill()
    for i, (x, y, s) in enumerate(((120, 120, 1.0), (640, 60, 1.25), (930, 230, 0.8), (380, 290, 0.7), (-300, 200, 1.0), (1400, 150, 1.1))):
        xx = (x + t * (5 + 3 * (i % 3))) % (W + 1600) - 800
        paint_surface(ctx, tex(f"cloud{i % 4}"), xx - 260 * s, y - 110 * s, 520 * s, 220 * s, alpha_=0.95)


def draw_palm(ctx, base, height, sway=0.0, scale=1.0):
    bx, by = base
    top = (bx + 18 * scale + sway * 6, by - height)
    soft_shadow(ctx, bx + 25 * scale, by + 2, 70 * scale, 10 * scale, 0.25)
    ctx.set_source(lgrad(bx - 10 * scale, 0, bx + 10 * scale, 0, [(0, shade(C["trunk"], 0.7)), (0.4, shade(C["trunk"], 1.2)), (1, shade(C["trunk"], 0.55))]))
    path_poly(ctx, [(bx - 9 * scale, by), (top[0] - 6 * scale, top[1]), (top[0] + 6 * scale, top[1]), (bx + 9 * scale, by)])
    ctx.fill()
    for k in range(10):
        yy, xx = lerp(by, top[1], (k + 0.5) / 10), lerp(bx, top[0], (k + 0.5) / 10)
        ctx.move_to(xx - 8 * scale, yy)
        ctx.line_to(xx + 8 * scale, yy - 3 * scale)
        ctx.set_source_rgba(0.25, 0.17, 0.08, 0.5)
        ctx.set_line_width(2 * scale)
        ctx.stroke()
    for k in range(11):
        a = -math.pi / 2 + (k - 5) * 0.36 + sway * 0.05
        L = 100 * scale * (0.85 + 0.12 * (k % 3))
        tip = (top[0] + math.cos(a) * L, top[1] + math.sin(a) * L * 0.55 + abs(k - 5) * 10 * scale)
        mid = (top[0] + math.cos(a) * L * 0.5, top[1] + math.sin(a) * L * 0.5 - 18 * scale)
        nx, ny = -(tip[1] - top[1]), tip[0] - top[0]
        nl = math.hypot(nx, ny) or 1
        nx, ny = nx / nl * 14 * scale, ny / nl * 14 * scale
        ctx.move_to(*top)
        ctx.curve_to(mid[0] + nx, mid[1] + ny, mid[0] + nx, mid[1] + ny, *tip)
        ctx.curve_to(mid[0] - nx, mid[1] - ny, mid[0] - nx, mid[1] - ny, *top)
        ctx.set_source(lgrad(top[0], top[1], tip[0], tip[1], [(0, shade(C["palm"], 0.7)), (0.5, shade(C["palm"], 1.05 + 0.08 * (k % 2))), (1, shade(C["palm"], 1.2))]))
        ctx.fill()
    sphere(ctx, top[0], top[1] + 4, 10 * scale, shade(C["trunk"], 0.8))


def draw_villa(ctx, P, sc_at, yH=15.0, t=0.0, small=False):
    """Saudi villa facade with parapets, arched windows, AC units, planters."""
    x0, x1 = -7.2, 7.2

    def face(xa, xb, za, zb, y, col):
        fill_poly(ctx, [P(xa, y, za), P(xb, y, za), P(xb, y, zb), P(xa, y, zb)], col)
    for a, b in ((-16, x0), (x1, 16)):
        face(a, b, 0, 2.6, yH + 0.5, C["wall"])
        face(a, b, 2.6, 2.85, yH + 0.5, C["trim"])
    # facade with vertical light falloff
    pts = [P(x0, yH, 0), P(x1, yH, 0), P(x1, yH, 6.6), P(x0, yH, 6.6)]
    fill_poly(ctx, pts, lgrad(pts[0][0], 0, pts[1][0], 0, [(0, shade(C["house"], 1.02)), (1, shade(C["house"], 0.9))]))
    face(-4.5, 2.8, 6.6, 10.0, yH + 1.0, shade(C["house"], 0.95))
    for (xa, xb, z, y) in ((x0 - 0.15, x1 + 0.15, 6.6, yH - 0.05), (-4.65, 2.95, 10.0, yH + 0.95)):
        face(xa, xb, z, z + 0.45, y, C["trim"])
        n = int((xb - xa) / 0.7)
        for k in range(n):
            xa2 = xa + k * (xb - xa) / n + 0.12
            face(xa2, xa2 + 0.3, z + 0.45, z + 0.75, y, C["trim"])
        a, b = P(xa, y - 0.02, z), P(xb, y - 0.02, z)
        ao_strip(ctx, a, b, (0, 1), 18, 0.25)
    for wx in (-5.4, -2.4, 2.4, 5.4):
        for wz, hgt in ((1.0, 2.0), (3.9, 1.8)):
            a, b = P(wx - 0.6, yH - 0.02, wz), P(wx + 0.6, yH - 0.02, wz + hgt)
            x, y, w, h = a[0], b[1], b[0] - a[0], a[1] - b[1]
            ctx.new_path()
            ctx.move_to(x, y + w / 2)
            ctx.arc(x + w / 2, y + w / 2, w / 2, math.pi, 0)
            ctx.line_to(x + w, y + h)
            ctx.line_to(x, y + h)
            ctx.close_path()
            ctx.set_source(lgrad(x, y, x + w, y + h, [(0, shade(C["glass"], 1.5)), (0.45, C["glass"]), (1, shade(C["glass"], 0.75))]))
            ctx.fill_preserve()
            set_src(ctx, C["trim"])
            ctx.set_line_width(max(1.5, w * 0.07))
            ctx.stroke()
            ao_strip(ctx, (x, y + h), (x + w, y + h), (0, 1), h * 0.12, 0.2)
    a, b = P(-0.85, yH - 0.03, 0), P(0.85, yH - 0.03, 2.7)
    rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 4)
    ctx.set_source(lgrad(a[0], 0, b[0], 0, [(0, shade(C["wood"], 0.8)), (0.5, shade(C["wood"], 1.15)), (1, shade(C["wood"], 0.7))]))
    ctx.fill()
    fill_poly(ctx, [P(-7.6, yH - 2.2, 0.02), P(7.6, yH - 2.2, 0.02), P(7.6, yH, 0.02), P(-7.6, yH, 0.02)], hexc("#d9c9ad"))
    ao_strip(ctx, P(-7.2, yH - 0.02, 0.02), P(7.2, yH - 0.02, 0.02), (0, 1), 10, 0.25)
    sway = math.sin(t * 1.3)
    for (px, py, ht, s) in ((-9.8, 13.5, 7.5, 1.15), (9.6, 13.8, 6.6, 1.05), (-12.0, 9.0, 6.0, 1.2), (12.2, 9.5, 6.2, 1.25)):
        b = P(px, py, 0)
        k = sc_at(py)
        draw_palm(ctx, b, ht * k, sway, scale=s * k / 30)


def draw_far(ctx, P, y=26):
    rnd = RNDS(4)
    y0 = P(0, y, 0)[1]
    for i in range(44):
        x = -W + i * 75 + rnd.uniform(-20, 20)
        r = rnd.uniform(40, 70)
        for k in range(3):
            sphere(ctx, x + rnd.uniform(-25, 25), y0 - r * 0.9 - k * r * 0.45, r * rnd.uniform(0.7, 1.0),
                   mix(hexc("#5f8a4a"), hexc("#7aa05e"), rnd.random()), light=(-0.2, -0.5))


def draw_lawn(ctx, P, x0, x1, y0, y1):
    pts = [P(x0, y0, 0), P(x1, y0, 0), P(x1, y1, 0), P(x0, y1, 0)]
    ytop, ybot = P(0, y1, 0)[1], P(0, y0, 0)[1]
    ctx.set_source(lgrad(0, ytop, 0, ybot, [(0, shade(C["lawn"], 0.88)), (1, shade(C["lawn"], 1.08))]))
    path_poly(ctx, pts)
    ctx.fill()
    ctx.save()
    clip_poly(ctx, pts)
    for k in range(int(x0) - 6, int(x1) + 6, 2):
        fill_poly(ctx, [P(k, y0, 0), P(k + 1, y0, 0), P(k + 7, y1, 0), P(k + 6, y1, 0)], alpha(C["lawn2"], 0.5))
    paint_surface(ctx, tex("lawn"), -W, ytop, 3 * W, ybot - ytop, alpha_=0.35)
    ctx.restore()


def draw_soil(ctx, P, top_z=0.0, holes=(), x0=-40, x1=40):
    top = P(0, 0, top_z)[1]
    ctx.save()
    ctx.rectangle(-W * 2, top, W * 5, H * 3)
    for h in holes:
        path_poly(ctx, [P(x, 0, z) for x, z in h])
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.clip()
    for ox in (-2 * W, -W, 0, W, 2 * W):
        paint_surface(ctx, tex("soil"), ox - 60, top - 10, W + 120, H * 1.4)
    ctx.rectangle(-W * 2, top, W * 5, 34)
    ctx.set_source(lgrad(0, top, 0, top + 34, [(0, (0.22, 0.14, 0.06, 0.85)), (1, (0.22, 0.14, 0.06, 0))]))
    ctx.fill()
    ctx.restore()


def grass_lip(ctx, P, x0, x1, seed=2):
    rnd = RNDS(seed)
    a, b = P(x0, 0, 0), P(x1, 0, 0)
    x = a[0]
    while x < b[0]:
        h = rnd.uniform(8, 20)
        ctx.move_to(x, a[1] + 4)
        ctx.line_to(x + rnd.uniform(-5, 5), a[1] - h)
        ctx.line_to(x + 6, a[1] + 4)
        set_src(ctx, shade(C["lawn"], rnd.uniform(0.75, 1.2)))
        ctx.fill()
        x += 8


def stink(ctx, base_pts, t, a, col=None, height=320, amp=18):
    col = col or (0.62, 0.82, 0.25)
    for i, (bx, by) in enumerate(base_pts):
        pts = []
        for k in range(28):
            u = k / 27
            pts.append((bx + amp * math.sin(u * 9 + t * 6 + i * 1.7), by - u * height - (t * 90 + i * 37) % 50))
        path_poly(ctx, pts, close=False)
        ctx.set_source_rgba(*col, 0.9 * a)
        ctx.set_line_width(7)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()


def flies(ctx, cx, cy, t, n, a, spread=160):
    rnd = RNDS(9)
    for i in range(n):
        ph, r1, r2, sp = rnd.random() * 6.28, rnd.uniform(0.4, 1.0), rnd.uniform(0.3, 0.8), rnd.uniform(2, 4)
        x = cx + math.cos(t * sp + ph) * spread * r1 + math.sin(t * 7 + i) * 6
        y = cy + math.sin(t * sp * 1.3 + ph) * spread * 0.5 * r2
        for s in (-1, 1):
            ellipse(ctx, x + s * 5, y - 5, 6, 3.5 + 2 * abs(math.sin(t * 60 + i)))
            ctx.set_source_rgba(0.85, 0.92, 1, 0.7 * a)
            ctx.fill()
        sphere(ctx, x, y, 5, (0.1, 0.1, 0.12, a))


def bucket(ctx, x, y, s, tilt, pour=0.0, t=0.0, target=None):
    """Metal bucket at screen (x, y), size s px, tilted by `tilt` radians; optional pouring stream."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(tilt)
    path_poly(ctx, [(-0.5 * s, -0.5 * s), (0.5 * s, -0.5 * s), (0.38 * s, 0.5 * s), (-0.38 * s, 0.5 * s)])
    ctx.set_source(lgrad(-0.5 * s, 0, 0.5 * s, 0, [(0, hexc("#7a8088")), (0.35, hexc("#e6eaee")), (1, hexc("#6a7078"))]))
    ctx.fill()
    for k in (-0.2, 0.15):
        ctx.move_to(-0.48 * s, k * s)
        ctx.line_to(0.48 * s, k * s)
        ctx.set_source_rgba(0, 0, 0, 0.18)
        ctx.set_line_width(3)
        ctx.stroke()
    ellipse(ctx, 0, -0.5 * s, 0.5 * s, 0.12 * s)
    set_src(ctx, hexc("#4fb6e3"))
    ctx.fill()
    ctx.arc(0, -0.45 * s, 0.6 * s, math.pi * 1.1, math.pi * 1.9)
    ctx.set_source_rgba(0.3, 0.32, 0.36, 1)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.restore()
    if pour > 0 and target:
        lx = x + 0.5 * s * math.cos(tilt) + 0.5 * s * math.sin(tilt)
        ly = y + 0.5 * s * math.sin(tilt) - 0.5 * s * math.cos(tilt)
        tx, ty = target
        ctx.move_to(lx, ly)
        ctx.curve_to(lx + 40, ly + 10, tx, ly + (ty - ly) * 0.3, tx, ty)
        ctx.set_source_rgba(0.55, 0.85, 1, 0.85 * pour)
        ctx.set_line_width(14 * pour + 2)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        rnd = RNDS(int(t * 30))
        for i in range(10):
            ctx.arc(tx + rnd.uniform(-30, 30), ty - rnd.uniform(0, 30), rnd.uniform(3, 7), 0, 2 * math.pi)
            ctx.set_source_rgba(0.8, 0.95, 1, 0.8 * pour)
            ctx.fill()


# =============================================================== SET 1: yard + outhouse
CY = Cam(dist=11.0, height=3.2, pitch_deg=10.0, focal=1420.0, horizon_y=780.0)
PY = CY.p
PIT = (-0.6, 0.6, -1.9)


def yard_pit_depth(t):
    return smooth(t, E["dig"], E["build"] - 0.1)


def draw_yard(ctx, t):
    draw_sky(ctx, t)
    draw_far(ctx, PY, 26)
    draw_villa(ctx, PY, CY.scale_at, 15.0, t)
    haze(ctx, 0, PY(0, 12, 0)[1] + 40, amount=0.28)
    draw_lawn(ctx, PY, -40, 40, 0, 16)
    d = yard_pit_depth(t)
    # dirt pile
    s = smooth(t, E["dig"], E["build"])
    if s > 0:
        b = PY(-3.2, 1.6, 0)
        k = CY.scale_at(1.6)
        rx, ry = 1.2 * k * s, 0.7 * k * s
        soft_shadow(ctx, b[0] + 10, b[1] + 4, rx * 1.15, ry * 0.35, 0.35)
        ctx.move_to(b[0] - rx, b[1])
        ctx.curve_to(b[0] - rx * 0.6, b[1] - ry * 1.4, b[0] + rx * 0.6, b[1] - ry * 1.4, b[0] + rx, b[1])
        ctx.close_path()
        ctx.set_source(rgrad(b[0] - rx * 0.3, b[1] - ry, 5, rx * 1.4, [(0, shade(C["dirt"], 1.3)), (1, shade(C["dirt"], 0.65))]))
        ctx.fill()
    # pit seen from above (dark hole) + soil cut face with the pit section
    x0, x1, zb = PIT
    if d > 0:
        hole_top = [PY(x0, 0, 0), PY(x1, 0, 0), PY(x1, 1.1, 0), PY(x0, 1.1, 0)]
        fill_poly(ctx, hole_top, shade(C["dirt"], 0.45))
    draw_soil(ctx, PY, 0, [[(x0, 0), (x1, 0), (x1, zb * d), (x0, zb * d)]] if d > 0 else [])
    if d > 0:
        # inside of the pit (back wall + floor), darker toward the bottom
        back = [PY(x0, 1.1, 0), PY(x1, 1.1, 0), PY(x1, 1.1, zb * d), PY(x0, 1.1, zb * d)]
        a, b = PY(x0, 0, 0), PY(x1, 0, zb * d)
        ctx.save()
        ctx.rectangle(a[0], a[1], b[0] - a[0], b[1] - a[1])
        ctx.clip()
        ctx.rectangle(a[0], a[1] - 200, b[0] - a[0], b[1] - a[1] + 200)
        ctx.set_source(lgrad(0, a[1], 0, b[1], [(0, shade(C["dirt"], 0.75)), (1, shade(C["dirt"], 0.35))]))
        ctx.fill()
        fill_poly(ctx, back, alpha(shade(C["dirt"], 0.55), 0.6))
        # waste level rising
        lvl = keyed(t, [(E["build"], zb * 0.92), (E["problem"], zb * 0.75), (E["fill"], zb * 0.6), (E["fill"] + 1.4, -0.12)])
        if t > E["build"]:
            ly = PY(0, 0, lvl)[1]
            ctx.rectangle(a[0], ly, b[0] - a[0], b[1] - ly)
            ctx.set_source(lgrad(0, ly, 0, b[1], [(0, hexc("#7a5a2c")), (1, hexc("#3e2a12"))]))
            ctx.fill()
            for i in range(8):
                bx = a[0] + (i + 0.5) * (b[0] - a[0]) / 8
                r = 3 + 3 * abs(math.sin(t * 2 + i))
                ctx.arc(bx, ly + 4 + 4 * math.sin(t * 3 + i), r, 0, 2 * math.pi)
                ctx.set_source_rgba(0.75, 0.62, 0.35, 0.6)
                ctx.fill()
        ctx.restore()
        ao_strip(ctx, PY(x0, 0, 0), PY(x0, 0, zb * d), (1, 0), 22, 0.35)
        ao_strip(ctx, PY(x1, 0, 0), PY(x1, 0, zb * d), (-1, 0), 22, 0.35)
    grass_lip(ctx, PY, -40, x0 - 0.05, 2)
    grass_lip(ctx, PY, x1 + 0.05, 40, 3)
    # shovel stuck in the pile
    if E["dig"] < t < E["problem"]:
        b = PY(-2.6, 1.7, 0.4)
        k = CY.scale_at(1.7)
        ctx.save()
        ctx.translate(*b)
        ctx.rotate(0.35)
        ctx.rectangle(-3, -1.5 * k, 6, 1.5 * k)
        set_src(ctx, C["wood"])
        ctx.fill()
        rounded_rect(ctx, -0.15 * k, 0, 0.3 * k, 0.4 * k, 6)
        ctx.set_source(lgrad(-0.15 * k, 0, 0.15 * k, 0, [(0, hexc("#8d9399")), (0.5, hexc("#e2e6ea")), (1, hexc("#7a8086"))]))
        ctx.fill()
        ctx.restore()
    # outhouse assembles over the pit
    if t >= E["build"]:
        draw_outhouse(ctx, t)
    if t > E["smell"] - 0.2:
        a = smooth(t, E["smell"] - 0.2, E["smell"] + 0.4)
        bx, by = PY(0, 0.6, 2.6)
        stink(ctx, [(bx - 120, by), (bx - 40, by - 20), (bx + 50, by - 5), (bx + 130, by + 10)], t, a, height=260)
    if t > E["flies"] - 0.2:
        a = smooth(t, E["flies"] - 0.2, E["flies"] + 0.4)
        bx, by = PY(0, 0.4, 1.6)
        flies(ctx, bx, by, t, 9, a, 190)


def draw_outhouse(ctx, t):
    k = [smooth(t, E["build"] + i * 0.18, E["build"] + i * 0.18 + 0.35) for i in range(5)]
    x0, x1, y0, y1 = -0.75, 0.75, 0.0, 1.3
    sc = CY.scale_at(0)
    # shadow on the lawn
    c = PY(0.3, 1.0, 0)
    soft_shadow(ctx, c[0] + 30, c[1] - 6, 1.3 * sc, 0.32 * sc, 0.45 * k[0])
    # floor platform
    if k[0] > 0:
        box3d(ctx, CY, x0 - 0.1, x1 + 0.1, y0, y1 + 0.1, -0.05 + (1 - k[0]) * 2, 0.12 + (1 - k[0]) * 2, hexc("#8a5a33"))
    # walls (front face uses wood planks texture)
    if k[1] > 0:
        dz = (1 - k[1]) * 3
        box3d(ctx, CY, x0, x1, y0, y1, 0.12 + dz, 2.3 + dz, hexc("#8e5f36"), faces=("left", "right", "top"))
        front = [PY(x0, y0, 0.12 + dz), PY(x1, y0, 0.12 + dz), PY(x1, y0, 2.3 + dz), PY(x0, y0, 2.3 + dz)]
        tex_fill(ctx, front, hexc("#8e5f36"), "wood", 0.9)
        # door frame and crescent moon window
        if k[2] > 0:
            a, b = PY(x0 + 0.18, y0 - 0.01, 0.2 + dz), PY(x1 - 0.18, y0 - 0.01, 2.05 + dz)
            rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 4)
            ctx.set_source_rgba(0.25, 0.14, 0.06, 0.35 * k[2])
            ctx.set_line_width(5)
            ctx.stroke()
            mx, my = (a[0] + b[0]) / 2, b[1] + (a[1] - b[1]) * 0.18
            r = 0.16 * sc
            ctx.arc(mx, my, r, 0, 2 * math.pi)
            ctx.arc_negative(mx + r * 0.45, my - r * 0.2, r * 0.85, 2 * math.pi, 0)
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            ctx.set_source_rgba(0.08, 0.05, 0.02, k[2])
            ctx.fill()
            ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
            sphere(ctx, b[0] - 14, (a[1] + b[1]) / 2, 5, C["brass"])
        ao_strip(ctx, PY(x0, y0, 2.3 + dz), PY(x1, y0, 2.3 + dz), (0, 1), 26, 0.35)
    # slanted roof
    if k[3] > 0:
        dz = (1 - k[3]) * 3
        r0, r1 = 2.35 + dz, 2.6 + dz
        fill_poly(ctx, [PY(x0 - 0.2, y0 - 0.25, r0), PY(x1 + 0.2, y0 - 0.25, r0), PY(x1 + 0.2, y1 + 0.2, r1), PY(x0 - 0.2, y1 + 0.2, r1)], hexc("#5a3a20"))
        fill_poly(ctx, [PY(x0 - 0.2, y0 - 0.25, r0 - 0.1), PY(x1 + 0.2, y0 - 0.25, r0 - 0.1), PY(x1 + 0.2, y0 - 0.25, r0), PY(x0 - 0.2, y0 - 0.25, r0)], hexc("#3e2814"))
    if k[4] > 0 and t > E["toilet0"]:
        # little sparkle when "you've got a toilet"
        u = lin(t, E["toilet0"], E["toilet0"] + 0.6)
        if u < 1:
            c = PY(0, 0, 2.6)
            for i in range(8):
                a = i * math.pi / 4
                r = 60 + 120 * u
                ctx.move_to(c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6)
                ctx.line_to(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r)
                ctx.set_source_rgba(1, 0.9, 0.4, 1 - u)
                ctx.set_line_width(6)
                ctx.stroke()


# =============================================================== SET 2: house cut-away
CH = Cam(dist=10.5, height=1.7, pitch_deg=3.0, focal=1900.0, horizon_y=843.0)
PH = CH.p
RX0, RX1 = -2.2, 2.0          # room inner walls (x)
WALL = 0.25
RD = 3.0                      # room depth (back wall at y = RD)
RZ = 2.8                      # ceiling height
SLAB = 0.35
ROOF = 0.35
TX = RX0 + 0.04               # toilet origin (back of tank touches the left wall)
TS = 1.6                      # toilet drawing scale (larger than life for readability, like the references)
SEWER = (5.6, -2.2, 0.55)     # sewer main centre x, z and radius
ROAD_X = 3.5


def T(u, v):
    """Toilet local (u right, v up, metres) -> world (x, z) in the section plane."""
    return TX + u * TS, v * TS


def TP(u, v, y=0.0):
    x, z = T(u, v)
    return PH(x, y, z)


# toilet profile (local units)
BODY = [(0.30, 0.0), (0.68, 0.0), (0.66, 0.10), (0.74, 0.18), (0.86, 0.30), (0.90, 0.40), (0.90, 0.45),
        (0.18, 0.45), (0.18, 0.40), (0.22, 0.30), (0.27, 0.16), (0.29, 0.06)]
BASIN = [(0.84, 0.42), (0.80, 0.32), (0.70, 0.22), (0.56, 0.15), (0.46, 0.12), (0.40, 0.13), (0.36, 0.20), (0.31, 0.32), (0.27, 0.42)]
TRAP_S = [(0.44, 0.13), (0.37, 0.16), (0.31, 0.22), (0.27, 0.29), (0.22, 0.31), (0.19, 0.26), (0.21, 0.15), (0.30, 0.04), (0.40, 0.0)]
TRAP_0 = [(0.44, 0.13), (0.435, 0.12), (0.43, 0.11), (0.425, 0.09), (0.42, 0.075), (0.415, 0.06), (0.41, 0.04), (0.405, 0.02), (0.40, 0.0)]
CREST_I = 4
SEAL_V = 0.235               # still-water level in the bowl (just below the trap crest)


def trap_shape(t):
    k = smooth(t, E["bend"], E["S"] + 0.4)
    return [(lerp(a[0], b[0], k), lerp(a[1], b[1], k)) for a, b in zip(TRAP_0, TRAP_S)], k


def drain_path():
    ox, oz = T(0.40, 0.0)
    return [(ox, oz), (ox, -0.8), (ox + 0.35, -1.0), (SEWER[0] - 0.9, SEWER[1] + 0.25), (SEWER[0] - SEWER[2] + 0.05, SEWER[1] + 0.05)]


def drain_screen():
    return round_corners([PH(x, 0, z) for x, z in drain_path()], 30)


VENT_X = RX0 - WALL / 2


def vent_screen():
    ox, _ = T(0.40, 0.0)
    pts = [(ox, -0.75), (VENT_X, -0.75), (VENT_X, RZ + ROOF + 0.9)]
    return round_corners([PH(x, 0, z) for x, z in pts], 22)


def bowl_level(t):
    """Water level in the bowl (local v) and trap state."""
    if t < E["bend"]:
        return None
    lv = keyed(t, [(E["seal"] - 0.3, 0.06), (E["seal"] + 0.6, SEAL_V),
                   (E["bigflush"], SEAL_V), (E["bigflush"] + 0.5, 0.36), (E["rush"], 0.36),
                   (E["empty"], 0.08), (E["gurgle"] + 0.2, 0.06), (E["air"] + 0.8, SEAL_V),
                   (E["lift"], SEAL_V), (E["lift"] + 0.6, 0.34), (E["float"], 0.10), (E["full"], SEAL_V),
                   (E["rush2"], SEAL_V), (E["suckair"] + 0.2, SEAL_V), (E["dry"], 0.02), (E["vent"], 0.02),
                   (E["air_in"], SEAL_V)])
    return lv


def siphon_on(t):
    return (E["rush"] - 0.1 < t < E["gurgle"] + 0.1) or (E["lift"] + 0.3 < t < E["float"] + 0.2) or (E["suckair"] - 0.2 < t < E["dry"] + 0.1)


def draw_room(ctx, t):
    """Bathroom interior (back wall, floor, side walls, ceiling) in perspective."""
    # back wall: tiles below, paint above, blue band
    bw = [PH(RX0, RD, 0), PH(RX1, RD, 0), PH(RX1, RD, RZ), PH(RX0, RD, RZ)]
    fill_poly(ctx, bw, C["paint"])
    tiles = [PH(RX0, RD, 0), PH(RX1, RD, 0), PH(RX1, RD, 1.3), PH(RX0, RD, 1.3)]
    tex_fill(ctx, tiles, C["tile"], "tile", 1.0)
    band = [PH(RX0, RD, 1.3), PH(RX1, RD, 1.3), PH(RX1, RD, 1.42), PH(RX0, RD, 1.42)]
    fill_poly(ctx, band, C["band"])
    # window with daylight
    wa, wb = PH(-0.5, RD - 0.01, 1.55), PH(0.5, RD - 0.01, 2.45)
    ctx.rectangle(wa[0], wb[1], wb[0] - wa[0], wa[1] - wb[1])
    ctx.set_source(lgrad(wa[0], wb[1], wb[0], wa[1], [(0, hexc("#e8f4ff")), (1, hexc("#9cc8ea"))]))
    ctx.fill_preserve()
    set_src(ctx, hexc("#ffffff"))
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.move_to((wa[0] + wb[0]) / 2, wb[1])
    ctx.line_to((wa[0] + wb[0]) / 2, wa[1])
    ctx.move_to(wa[0], (wa[1] + wb[1]) / 2)
    ctx.line_to(wb[0], (wa[1] + wb[1]) / 2)
    ctx.set_line_width(5)
    ctx.stroke()
    # floor: checker tiles in perspective
    n = 12
    for i in range(n):
        for j in range(6):
            xa = RX0 + i * (RX1 - RX0) / n
            xb = xa + (RX1 - RX0) / n
            ya, yb = j * RD / 6, (j + 1) * RD / 6
            fill_poly(ctx, [PH(xa, ya, 0), PH(xb, ya, 0), PH(xb, yb, 0), PH(xa, yb, 0)],
                      C["floor1"] if (i + j) % 2 else C["floor2"], seam=True)
    # side walls (inner faces)
    lw = [PH(RX0, 0, 0), PH(RX0, RD, 0), PH(RX0, RD, RZ), PH(RX0, 0, RZ)]
    fill_poly(ctx, lw, shade(C["paint"], 1.03))
    lt = [PH(RX0, 0, 0), PH(RX0, RD, 0), PH(RX0, RD, 1.3), PH(RX0, 0, 1.3)]
    tex_fill(ctx, lt, shade(C["tile"], 1.02), "tile", 0.9)
    fill_poly(ctx, [PH(RX0, 0, 1.3), PH(RX0, RD, 1.3), PH(RX0, RD, 1.42), PH(RX0, 0, 1.42)], C["band"])
    rw = [PH(RX1, 0, 0), PH(RX1, RD, 0), PH(RX1, RD, RZ), PH(RX1, 0, RZ)]
    fill_poly(ctx, rw, shade(C["paint"], 0.86))
    rt = [PH(RX1, 0, 0), PH(RX1, RD, 0), PH(RX1, RD, 1.3), PH(RX1, 0, 1.3)]
    tex_fill(ctx, rt, shade(C["tile"], 0.86), "tile", 0.9)
    fill_poly(ctx, [PH(RX1, 0, 1.3), PH(RX1, RD, 1.3), PH(RX1, RD, 1.42), PH(RX1, 0, 1.42)], shade(C["band"], 0.85))
    # ceiling
    fill_poly(ctx, [PH(RX0, 0, RZ), PH(RX1, 0, RZ), PH(RX1, RD, RZ), PH(RX0, RD, RZ)], shade(C["paint"], 0.92))
    # corner ambient occlusion
    for a, b, nrm in ((PH(RX0, RD, 0), PH(RX0, RD, RZ), (1, 0)), (PH(RX1, RD, 0), PH(RX1, RD, RZ), (-1, 0)),
                      (PH(RX0, RD, 0), PH(RX1, RD, 0), (0, -1)), (PH(RX0, RD, RZ), PH(RX1, RD, RZ), (0, 1))):
        ao_strip(ctx, a, b, nrm, 26, 0.22)
    # ceiling lamp glow
    lp = PH(0.0, RD * 0.5, RZ - 0.02)
    ctx.arc(lp[0], lp[1] + 8, 160, 0, 2 * math.pi)
    ctx.set_source(rgrad(lp[0], lp[1] + 8, 5, 160, [(0, (1, 0.98, 0.85, 0.55)), (1, (1, 0.98, 0.85, 0))]))
    ctx.fill()
    ellipse(ctx, lp[0], lp[1] + 6, 34, 12)
    set_src(ctx, hexc("#fffbe8"))
    ctx.fill()
    # sink on the back wall + mirror
    sa = PH(1.3, RD - 0.02, 0.85)
    sc = CH.scale_at(RD)
    rounded_rect(ctx, sa[0] - 0.35 * sc, sa[1] - 0.12 * sc, 0.7 * sc, 0.18 * sc, 10)
    ctx.set_source(lgrad(0, sa[1] - 0.12 * sc, 0, sa[1] + 0.06 * sc, [(0, C["porcelain"]), (1, C["porc_shade"])]))
    ctx.fill()
    ctx.rectangle(sa[0] - 0.05 * sc, sa[1] + 0.06 * sc, 0.1 * sc, 0.75 * sc)
    set_src(ctx, C["porc_shade"])
    ctx.fill()
    ma, mb = PH(1.0, RD - 0.02, 1.6), PH(1.6, RD - 0.02, 2.3)
    rounded_rect(ctx, ma[0], mb[1], mb[0] - ma[0], ma[1] - mb[1], 12)
    ctx.set_source(lgrad(ma[0], mb[1], mb[0], ma[1], [(0, hexc("#dff0fa")), (0.5, hexc("#a8c8dd")), (1, hexc("#d8ecf7"))]))
    ctx.fill()
    # bath mat
    fill_poly(ctx, [PH(0.3, 0.6, 0.01), PH(1.3, 0.6, 0.01), PH(1.3, 1.6, 0.01), PH(0.3, 1.6, 0.01)], hexc("#7fcfc4"))


def draw_outside(ctx, t):
    """Street side: lawn strip, sidewalk, road, far houses and palms."""
    draw_sky(ctx, t)
    draw_far(ctx, PH, 40)
    draw_villa(ctx, lambda x, y, z: PH(x + 14, y + 16, z), lambda y: CH.scale_at(y + 16), 15.0, t)
    haze(ctx, 0, PH(0, 25, 0)[1] + 30, amount=0.3)
    draw_lawn(ctx, PH, RX1, 3.0, 0, 30)
    draw_lawn(ctx, PH, -40, RX0 - WALL, 0, 30)
    fill_poly(ctx, [PH(3.0, 0, 0.1), PH(ROAD_X, 0, 0.1), PH(ROAD_X, 30, 0.1), PH(3.0, 30, 0.1)], hexc("#d8d2c6"))
    road = [PH(ROAD_X, 0, 0), PH(14, 0, 0), PH(14, 30, 0), PH(ROAD_X, 30, 0)]
    tex_fill(ctx, road, C["asphalt"], "asphalt", 1.0)
    for k in range(10):
        y = k * 3
        fill_poly(ctx, [PH(8.9, y, 0.01), PH(9.1, y, 0.01), PH(9.1, y + 1.5, 0.01), PH(8.9, y + 1.5, 0.01)], hexc("#f2f2f2"))
    for (px, py) in ((3.0, 6), (2.8, 14)):
        b = PH(px, py, 0)
        draw_palm(ctx, b, 5.5 * CH.scale_at(py), math.sin(t), scale=CH.scale_at(py) / 30)


def draw_house_section(ctx, t):
    """Cut faces at y = 0: soil, slab, walls, roof, road layers, sewer main."""
    sx, sz, sr = SEWER
    sewer_hole = [(sx + sr * math.cos(a), sz + sr * math.sin(a)) for a in [i * math.pi / 24 for i in range(48)]]
    draw_soil(ctx, PH, 0, [sewer_hole])
    # road layers in section
    fill_poly(ctx, [PH(ROAD_X, 0, 0), PH(14, 0, 0), PH(14, 0, -0.18), PH(ROAD_X, 0, -0.18)], C["asphalt"])
    fill_poly(ctx, [PH(ROAD_X, 0, -0.18), PH(14, 0, -0.18), PH(14, 0, -0.6), PH(ROAD_X, 0, -0.6)], C["gravel"])
    rnd = RNDS(3)
    a, b = PH(ROAD_X, 0, -0.2), PH(14, 0, -0.58)
    for i in range(70):
        sphere(ctx, rnd.uniform(a[0], b[0]), rnd.uniform(a[1], b[1]), rnd.uniform(4, 9), hexc("#b5afa4"))
    fill_poly(ctx, [PH(3.0, 0, 0.1), PH(ROAD_X, 0, 0.1), PH(ROAD_X, 0, -0.2), PH(3.0, 0, -0.2)], hexc("#c9c2b4"))
    grass_lip(ctx, PH, RX1 + WALL, 3.0, 5)
    grass_lip(ctx, PH, -40, RX0 - WALL - 0.3, 6)
    # floor slab + footings
    slab = [PH(RX0 - WALL - 0.3, 0, 0), PH(RX1 + WALL + 0.3, 0, 0), PH(RX1 + WALL + 0.3, 0, -SLAB), PH(RX0 - WALL - 0.3, 0, -SLAB)]
    tex_fill(ctx, slab, C["concrete"], "concrete", 0.7)
    for x in (RX0 - WALL / 2, RX1 + WALL / 2):
        ft = [PH(x - 0.35, 0, -SLAB), PH(x + 0.35, 0, -SLAB), PH(x + 0.35, 0, -0.95), PH(x - 0.35, 0, -0.95)]
        tex_fill(ctx, ft, shade(C["concrete"], 0.9), "concrete", 0.7)
    ao_strip(ctx, slab[3], slab[2], (0, -1), 14, 0.25)
    # walls and roof slab with parapet
    for xa, xb in ((RX0 - WALL, RX0), (RX1, RX1 + WALL)):
        wpts = [PH(xa, 0, 0), PH(xb, 0, 0), PH(xb, 0, RZ), PH(xa, 0, RZ)]
        tex_fill(ctx, wpts, shade(C["concrete"], 0.95), "concrete", 0.7)
    roof = [PH(RX0 - WALL - 0.2, 0, RZ), PH(RX1 + WALL + 0.2, 0, RZ), PH(RX1 + WALL + 0.2, 0, RZ + ROOF), PH(RX0 - WALL - 0.2, 0, RZ + ROOF)]
    tex_fill(ctx, roof, shade(C["concrete"], 0.97), "concrete", 0.7)
    for xa in (RX0 - WALL - 0.2, RX1 + 0.05):
        fill_poly(ctx, [PH(xa, 0, RZ + ROOF), PH(xa + 0.2, 0, RZ + ROOF), PH(xa + 0.2, 0, RZ + ROOF + 0.55), PH(xa, 0, RZ + ROOF + 0.55)], C["trim"])
    # exterior plaster strip outside the right wall
    fill_poly(ctx, [PH(RX1 + WALL, 0, 0), PH(RX1 + WALL + 0.04, 0, 0), PH(RX1 + WALL + 0.04, 0, RZ), PH(RX1 + WALL, 0, RZ)], C["house"])
    # sewer main (pipe running along the street, seen end-on)
    c = PH(sx, 0, sz)
    r = sr * CH.scale_at(0)
    ctx.arc(c[0], c[1], r, 0, 2 * math.pi)
    set_src(ctx, hexc("#2a2f35"))
    ctx.fill()
    ctx.save()
    ctx.arc(c[0], c[1], r * 0.84, 0, 2 * math.pi)
    ctx.clip()
    ctx.rectangle(c[0] - r, c[1] - r, 2 * r, 2 * r)
    ctx.set_source(rgrad(c[0], c[1] - r * 0.3, 2, r, [(0, hexc("#4a5058")), (1, hexc("#15181c"))]))
    ctx.fill()
    wl = c[1] + r * (0.15 + 0.04 * math.sin(t * 3))
    ctx.rectangle(c[0] - r, wl, 2 * r, r)
    ctx.set_source(lgrad(0, wl, 0, c[1] + r, [(0, hexc("#7b8d5a")), (1, hexc("#3c4a2a"))]))
    ctx.fill()
    for i in range(6):
        u = (t * 0.6 + i / 6) % 1.0
        ctx.arc(c[0] - r + 2 * r * u, wl + 8 + 6 * (i % 2), 4, 0, 2 * math.pi)
        ctx.set_source_rgba(0.75, 0.82, 0.6, 0.8)
        ctx.fill()
    ctx.restore()
    ctx.arc(c[0], c[1], r, 0, 2 * math.pi)
    ctx.arc_negative(c[0], c[1], r * 0.84, 2 * math.pi, 0)
    ctx.set_source(rgrad(c[0] - r * 0.3, c[1] - r * 0.4, 2, r * 1.2, [(0, hexc("#d9d4ca")), (1, hexc("#8f8a80"))]))
    ctx.fill()


def draw_pipe_contents(ctx, pts, u0, u1, col, width):
    sp = subpath(pts, u0, u1)
    if len(sp) > 1:
        path_poly(ctx, sp, close=False)
        set_src(ctx, col)
        ctx.set_line_width(width)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()


def draw_drain(ctx, t):
    if t < E["pipe"] - 0.05:
        return
    pts = drain_screen()
    w = 0.16 * CH.scale_at(0)
    g = smooth(t, E["pipe"], E["sewer"] + 0.4)
    sp = subpath(pts, 0, g)
    if len(sp) < 2:
        return
    # translucent pipe so the contents read like the references
    pipe(ctx, sp, w, alpha(C["pvc"], 0.95))
    path_poly(ctx, sp, close=False)
    ctx.set_source_rgba(0.80, 0.90, 0.96, 0.85)
    ctx.set_line_width(w * 0.62)
    ctx.stroke()
    # water pushed by the bucket
    if E["bucket"] + 0.3 < t < E["problem2"] + 0.4:
        u = lin(t, E["bucket"] + 0.3, E["push"] + 1.2)
        draw_pipe_contents(ctx, pts, max(0, u - 0.35), u, alpha(C["water"], 0.9), w * 0.55)
    # flushes rushing down the drain
    for a0, a1 in ((E["rush"], E["gurgle"] + 0.4), (E["lift"] + 0.3, E["float"] + 0.6), (E["rush2"], E["dry"] + 0.3)):
        if a0 < t < a1 + 0.8:
            u = lin(t, a0, a1)
            draw_pipe_contents(ctx, pts, max(0, u - 0.6), u, alpha(C["water"], 0.92), w * 0.55)
            for i in range(10):
                uu = (t * 0.9 + i / 10) % 1.0
                if uu < u:
                    p = polyline_point(pts, uu)
                    ctx.arc(p[0], p[1], w * 0.12, 0, 2 * math.pi)
                    ctx.set_source_rgba(1, 1, 1, 0.9)
                    ctx.fill()
    # waste blobs sitting in the pipe, then pushed to the sewer
    if E["still"] - 1.0 < t < E["problem2"]:
        push = smooth(t, E["push"] - 0.2, E["push"] + 1.4)
        for i, u0 in enumerate((0.22, 0.3, 0.38)):
            u = lerp(u0, 1.02, push)
            if u > 1.0:
                continue
            p = polyline_point(pts, u)
            ellipse(ctx, p[0], p[1] + 2, w * 0.24, w * 0.15)
            set_src(ctx, C["waste"])
            ctx.fill()


def draw_toilet(ctx, t, seat=0.0, lid=0.0, tank=0.0):
    k = pop(t, E["seat_in"], 0.45)
    if k <= 0:
        return
    sc = CH.scale_at(0) * TS
    ox, oy = TP(0, 0)
    ctx.save()
    ctx.translate(ox, oy)
    ctx.scale(max(k, 0.02), max(k, 0.02))
    ctx.translate(-ox, -oy)
    # contact shadow on the floor
    a, b = TP(0.28, 0), TP(0.75, 0)
    soft_shadow(ctx, (a[0] + b[0]) / 2 + 10, a[1] - 4, (b[0] - a[0]) * 0.8, 14, 0.4)
    # tank (behind the bowl, against the wall)
    if tank > 0:
        draw_tank(ctx, t, tank)
    # porcelain body
    body = [TP(u, v) for u, v in BODY]
    path_poly(ctx, body)
    ctx.set_source(lgrad(body[0][0], body[7][1], body[4][0], body[0][1], [(0, C["porcelain"]), (0.6, shade(C["porcelain"], 0.97)), (1, C["porc_shade"])]))
    ctx.fill()
    gloss(ctx, body, 0.4)
    path_poly(ctx, body)
    ctx.set_source_rgba(0.55, 0.62, 0.7, 0.7)
    ctx.set_line_width(2.5)
    ctx.stroke()
    # bowl cavity (section)
    basin = [TP(u, v) for u, v in BASIN]
    path_poly(ctx, basin)
    ctx.set_source(lgrad(0, basin[0][1], 0, basin[4][1], [(0, hexc("#e4ebf1")), (1, hexc("#b9c6d2"))]))
    ctx.fill()
    trap, tk = trap_shape(t)
    tw = 0.07 * sc
    # trapway: channel cut through the porcelain
    tp = [TP(u, v) for u, v in trap]
    tp = round_corners(tp, 10, 5)
    path_poly(ctx, tp, close=False)
    set_src(ctx, hexc("#cfd9e2"))
    ctx.set_line_width(tw + 6)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    path_poly(ctx, tp, close=False)
    set_src(ctx, hexc("#e9eff4"))
    ctx.set_line_width(tw)
    ctx.stroke()
    # water: bowl + rising leg of the trap below the level
    lv = bowl_level(t)
    full = siphon_on(t)
    if lv is not None or full:
        y_l = TP(0, lv if lv is not None else 0.3)[1]
        ctx.save()
        ctx.rectangle(-W, y_l, 3 * W, 3 * H)
        ctx.clip()
        path_poly(ctx, basin)
        ctx.set_source(lgrad(0, y_l, 0, basin[4][1], [(0, alpha(C["water"], 0.85)), (1, alpha(C["water_deep"], 0.9))]))
        ctx.fill()
        rising = round_corners([TP(u, v) for u, v in trap[:CREST_I + 1]], 10, 5)
        path_poly(ctx, rising, close=False)
        set_src(ctx, alpha(C["water"], 0.92))
        ctx.set_line_width(tw)
        ctx.stroke()
        ctx.restore()
        if lv is not None:
            a, b = TP(0.30, lv), TP(0.82, lv)
            ctx.move_to(a[0] + 4, a[1])
            ctx.line_to(b[0] - 4, b[1])
            ctx.set_source_rgba(1, 1, 1, 0.9)
            ctx.set_line_width(3)
            ctx.stroke()
    if full:
        path_poly(ctx, tp, close=False)
        set_src(ctx, alpha(C["water"], 0.95))
        ctx.set_line_width(tw)
        ctx.stroke()
    # tank-to-rim flush channel
    if tank > 0.5:
        a = [TP(0.30, 0.66), TP(0.26, 0.52), TP(0.27, 0.43)]
        pipe(ctx, a, 0.05 * sc, alpha(C["porcelain"], 0.95))
    # seat + lid
    if seat > 0:
        dz = (1 - seat) * 0.6
        a, b = TP(0.16, 0.46 + dz), TP(0.88, 0.50 + dz)
        rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 6)
        ctx.set_source(lgrad(0, b[1], 0, a[1], [(0, hexc("#ffffff")), (1, hexc("#c9d2da"))]))
        ctx.fill()
    if lid > 0:
        ang = (1 - lid) * 1.3 + 1.35
        hx, hy = TP(0.18, 0.50)
        ctx.save()
        ctx.translate(hx, hy)
        ctx.rotate(-ang)
        rounded_rect(ctx, 0, -0.045 * sc, 0.72 * sc, 0.045 * sc, 8)
        ctx.set_source(lgrad(0, -0.045 * sc, 0, 0, [(0, hexc("#ffffff")), (1, hexc("#c3ccd5"))]))
        ctx.fill()
        ctx.restore()
    ctx.restore()


def draw_tank(ctx, t, k):
    sc = CH.scale_at(0) * TS
    dz = (1 - k) * 0.8
    u0, u1, v0, v1 = 0.0, 0.46, 0.66 + dz, 1.32 + dz
    a, b = TP(u0, v0), TP(u1, v1)
    # outer shell
    rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 10)
    ctx.set_source(lgrad(a[0], 0, b[0], 0, [(0, C["porc_shade"]), (0.4, C["porcelain"]), (1, shade(C["porc_shade"], 0.95))]))
    ctx.fill()
    # lid
    la, lb = TP(u0 - 0.02, v1), TP(u1 + 0.02, v1 + 0.05)
    rounded_rect(ctx, la[0], lb[1], lb[0] - la[0], la[1] - lb[1], 6)
    set_src(ctx, C["porcelain"])
    ctx.fill()
    if k < 0.98:
        return
    # cut-away interior
    ia, ib = TP(u0 + 0.03, v0 + 0.03), TP(u1 - 0.03, v1 - 0.03)
    ctx.save()
    ctx.rectangle(ia[0], ib[1], ib[0] - ia[0], ia[1] - ib[1])
    ctx.clip()
    ctx.rectangle(ia[0], ib[1], ib[0] - ia[0], ia[1] - ib[1])
    set_src(ctx, hexc("#e8eef3"))
    ctx.fill()
    # tank water: drains when the flapper lifts, refills until the float rises
    tl = keyed(t, [(E["tank"], 0.9), (E["lift"] + 0.1, 0.9), (E["lift"] + 0.8, 0.12), (E["float"], 0.15), (E["full"], 0.9)])
    wy = TP(0, lerp(v0, v1, tl))[1]
    ctx.rectangle(ia[0], wy, ib[0] - ia[0], ia[1] - wy)
    ctx.set_source(lgrad(0, wy, 0, ia[1], [(0, alpha(C["water"], 0.85)), (1, alpha(C["water_deep"], 0.9))]))
    ctx.fill()
    ctx.restore()
    # flush valve opening + rubber flapper (lifts with the handle chain)
    lift = smooth(t, E["lift"], E["lift"] + 0.25) * (1 - smooth(t, E["lift"] + 1.2, E["lift"] + 1.6))
    va = TP(0.30, v0 + 0.03)
    fw = 0.13 * sc
    ctx.save()
    ctx.translate(va[0] - fw / 2, va[1] - 6)
    ctx.rotate(-lift * 0.9)
    rounded_rect(ctx, 0, -12, fw, 14, 6)
    ctx.set_source(lgrad(0, -12, 0, 2, [(0, hexc("#ff6b5a")), (1, C["rubber"])]))
    ctx.fill()
    ctx.restore()
    hl = 1 if E["flapper"] - 0.1 < t < E["handle"] + 0.6 else 0
    if hl:
        fa = TP(0.30, v0 + 0.06)
        ellipse(ctx, fa[0], fa[1], 0.14 * sc, 0.06 * sc)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9)
        ctx.set_line_width(4)
        ctx.stroke()
    # overflow tube
    o1, o2 = TP(0.38, v0 + 0.03), TP(0.38, v0 + 0.5)
    ctx.move_to(*o1)
    ctx.line_to(*o2)
    set_src(ctx, hexc("#f2f4f6"))
    ctx.set_line_width(0.035 * sc)
    ctx.stroke()
    # handle lever + chain
    hp = TP(u1 + 0.02, v1 - 0.08)
    ang = -0.5 * smooth(t, E["lift"] - 0.1, E["lift"] + 0.15) * (1 - smooth(t, E["lift"] + 1.2, E["lift"] + 1.6))
    ctx.save()
    ctx.translate(*hp)
    ctx.rotate(ang)
    rounded_rect(ctx, -0.25 * sc, -6, 0.3 * sc, 12, 6)
    ctx.set_source(lgrad(0, -6, 0, 6, [(0, hexc("#e8edf1")), (1, hexc("#8f99a3"))]))
    ctx.fill()
    ctx.restore()
    tx, ty = hp[0] - 0.22 * sc * math.cos(ang), hp[1] - 0.22 * sc * math.sin(ang)
    fx, fy = TP(0.30, v0 + 0.06 + 0.05 * lift)
    ctx.move_to(tx, ty)
    ctx.line_to(fx, fy - 10)
    ctx.set_source_rgba(0.5, 0.55, 0.6, 1)
    ctx.set_line_width(2.5)
    ctx.set_dash([5, 3])
    ctx.stroke()
    ctx.set_dash([])
    if E["handle"] - 0.1 < t < E["float"]:
        ctx.arc(hp[0] - 0.1 * sc, hp[1], 0.12 * sc, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9)
        ctx.set_line_width(4)
        ctx.stroke()
    # fill valve column + float ball on an arm
    fv_a, fv_b = TP(0.08, v0 + 0.03), TP(0.08, v1 - 0.12)
    ctx.move_to(*fv_a)
    ctx.line_to(*fv_b)
    set_src(ctx, hexc("#d6dce2"))
    ctx.set_line_width(0.05 * sc)
    ctx.stroke()
    fz = lerp(v0 + 0.15, v1 - 0.12, tl)
    bp = TP(0.24, fz)
    ctx.move_to(*fv_b)
    ctx.line_to(*bp)
    set_src(ctx, hexc("#9aa3ab"))
    ctx.set_line_width(3)
    ctx.stroke()
    sphere(ctx, bp[0], bp[1], 0.06 * sc, C["brass"])
    if E["float"] - 0.1 < t < E["rush2"]:
        ctx.arc(bp[0], bp[1], 0.1 * sc, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9)
        ctx.set_line_width(4)
        ctx.stroke()
    # refill stream from the fill valve
    if E["lift"] + 0.6 < t < E["full"] and tl < 0.88:
        ctx.move_to(fv_b[0] + 6, fv_b[1])
        ctx.line_to(fv_b[0] + 10, TP(0, lerp(v0, v1, tl))[1])
        ctx.set_source_rgba(0.6, 0.88, 1, 0.9)
        ctx.set_line_width(5)
        ctx.stroke()


def draw_waste_in_bowl(ctx, t):
    sc = CH.scale_at(0) * TS
    show = (E["catch"] - 0.4 < t < E["empty"] + 0.2)
    if not show:
        return
    u = smooth(t, E["rush"] + 0.3, E["empty"])
    trap, _ = trap_shape(t)
    pts = round_corners([TP(a, b) for a, b in trap], 10, 5) + [PH(*drain_path()[1][:1], 0, drain_path()[1][1])] if False else round_corners([TP(a, b) for a, b in trap], 10, 5)
    for i, (du, dv) in enumerate(((0.52, 0.20), (0.58, 0.24), (0.47, 0.17))):
        drop = smooth(t, E["catch"] - 0.4 + i * 0.12, E["catch"] + i * 0.12)
        if u > 0:
            p = polyline_point(pts, clamp(u * 1.4 - i * 0.12))
            x, y = p
        else:
            a = TP(du, lerp(0.7, dv, drop))
            x, y = a
        if u >= 0.99:
            continue
        ellipse(ctx, x, y, 0.035 * sc, 0.022 * sc)
        set_src(ctx, C["waste"])
        ctx.fill()


def draw_gas(ctx, t):
    """Green sewer-gas puffs travelling up the drain (and blocked by the water seal)."""
    windows = [(E["gas"] - 0.2, E["bend"] - 0.2, False), (E["seal"] + 0.3, E["trap_name"] + 1.0, True), (E["gas_back"] - 0.5, E["air_in"], False)]
    pts = drain_screen()
    trap, _ = trap_shape(t)
    tp = round_corners([TP(a, b) for a, b in trap], 10, 5)
    for t0, t1, blocked in windows:
        if not (t0 < t < t1 + 0.5):
            continue
        a = smooth(t, t0, t0 + 0.5) * (1 - smooth(t, t1, t1 + 0.5))
        for i in range(14):
            u = ((t - t0) * 0.28 + i / 14) % 1.0
            # u: 0 = sewer end, 1 = inside the room
            if u < 0.75:
                p = polyline_point(pts, 1 - u / 0.75)
            else:
                k = (u - 0.75) / 0.25
                if blocked:
                    p = polyline_point(tp, 1 - min(k, 0.45))
                    if k > 0.45:
                        continue
                else:
                    p = polyline_point(tp, 1 - min(k, 1.0))
            r = 9 + 4 * math.sin(i + t * 3)
            ctx.arc(p[0], p[1], r, 0, 2 * math.pi)
            ctx.set_source(rgrad(p[0], p[1], 1, r, [(0, (0.75, 1.0, 0.4, 0.95 * a)), (1, (0.55, 0.85, 0.2, 0.0))]))
            ctx.fill()
        if not blocked and t > (E["enter"] - 0.4 if t0 < E["bend"] else E["dry"]):
            bx, by = TP(0.55, 0.5)
            stink(ctx, [(bx - 40, by), (bx + 30, by - 10), (bx + 100, by)], t, a * 0.9, height=260, amp=14)
        if blocked and t > E["block"] - 0.2:
            bp = polyline_point(tp, 0.55)
            kx = pop(t, E["block"], 0.3) * a
            ctx.save()
            ctx.translate(bp[0] + 50, bp[1] - 40)
            ctx.scale(max(kx, 0.02), max(kx, 0.02))
            for ang in (math.pi / 4, -math.pi / 4):
                ctx.save()
                ctx.rotate(ang)
                rounded_rect(ctx, -34, -8, 68, 16, 8)
                set_src(ctx, C["red"])
                ctx.fill()
                ctx.restore()
            ctx.restore()


def draw_siphon_arrows(ctx, t):
    if not (E["fills"] - 0.2 < t < E["siphon_name"] + 1.0):
        return
    a = smooth(t, E["fills"] - 0.2, E["fills"] + 0.3) * (1 - smooth(t, E["siphon_name"] + 0.6, E["siphon_name"] + 1.0))
    trap, _ = trap_shape(t)
    tp = round_corners([TP(u, v) for u, v in trap], 10, 5) + drain_screen()[1:6]
    for i in range(6):
        u = ((t - E["fills"]) * 0.45 + i / 6) % 1.0
        p = polyline_point(tp, u)
        q = polyline_point(tp, min(1, u + 0.02))
        arrow(ctx, p[0], p[1], 34, 18, math.atan2(q[1] - p[1], q[0] - p[0]), alpha(C["white"], 0.95 * a))
    if E["siphon_name"] - 0.1 < t:
        c = TP(0.32, 0.18)
        ctx.arc(c[0], c[1], 0.3 * CH.scale_at(0) * TS, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.8 * a)
        ctx.set_line_width(5)
        ctx.stroke()


def draw_gurgle(ctx, t):
    if not (E["gurgle"] - 0.1 < t < E["air"] + 1.4):
        return
    trap, _ = trap_shape(t)
    tp = round_corners([TP(u, v) for u, v in trap], 10, 5)
    rnd = RNDS(int(t * 12))
    for i in range(10):
        u = rnd.random()
        p = polyline_point(tp, u)
        r = rnd.uniform(4, 10)
        ctx.arc(p[0] + rnd.uniform(-5, 5), p[1] + rnd.uniform(-5, 5), r, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.set_line_width(2.5)
        ctx.stroke()
    # sound waves
    c = TP(0.55, 0.5)
    for k in range(3):
        ph = ((t - E["gurgle"]) * 1.5 + k / 3) % 1.0
        ctx.arc(c[0], c[1], 30 + 110 * ph, -math.pi * 0.8, -math.pi * 0.2)
        ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - ph))
        ctx.set_line_width(5)
        ctx.stroke()
    # air arrows coming in from the drain side
    if t > E["air"] - 0.1:
        pts = drain_screen()
        for i in range(4):
            u = ((t - E["air"]) * 0.6 + i / 4) % 1.0
            p = polyline_point(pts, 0.35 - u * 0.3)
            arrow(ctx, p[0] - 20, p[1] + 30, 40, 18, -math.pi / 2 - 0.4, (0.8, 0.95, 1, 0.9))


def draw_vent(ctx, t):
    if t < E["vent"] - 0.1:
        return
    pts = vent_screen()
    g = smooth(t, E["vent"], E["roof"] + 0.3)
    sp = subpath(pts, 0, g)
    w = 0.13 * CH.scale_at(0)
    if len(sp) > 1:
        pipe(ctx, sp, w, C["pvc"])
    if g >= 1:
        top = pts[-1]
        rounded_rect(ctx, top[0] - w * 0.9, top[1] - w * 0.5, w * 1.8, w * 0.6, 4)
        set_src(ctx, hexc("#d9dee3"))
        ctx.fill()
    if E["air_in"] - 0.1 < t < E["see"]:
        a = smooth(t, E["air_in"] - 0.1, E["air_in"] + 0.3)
        for i in range(5):
            u = ((t - E["air_in"]) * 0.5 + i / 5) % 1.0
            p = polyline_point(pts, 1 - u)
            arrow(ctx, p[0] + w, p[1] - 20, 44, 20, math.pi / 2 if u < 0.85 else math.pi / 2 + 0.6, (0.8, 0.95, 1, 0.95 * a))
    if E["balance"] - 0.1 < t < E["see"]:
        c = TP(0.3, 0.2)
        k = pop(t, E["balance"], 0.35)
        ctx.save()
        ctx.translate(c[0] + 0.55 * CH.scale_at(0), c[1] - 0.25 * CH.scale_at(0))
        ctx.scale(max(k, 0.02), max(k, 0.02))
        ctx.arc(0, 0, 30, 0, 2 * math.pi)
        set_src(ctx, hexc("#3cbf5a"))
        ctx.fill()
        ctx.move_to(-13, 0)
        ctx.line_to(-3, 11)
        ctx.line_to(15, -10)
        ctx.set_source_rgba(1, 1, 1, 1)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.restore()


def draw_house(ctx, t):
    draw_outside(ctx, t)
    draw_room(ctx, t)
    draw_house_section(ctx, t)
    tank = smooth(t, E["tank"], E["tank"] + 0.45)
    seat = smooth(t, E["seat"], E["seat"] + 0.4)
    lid = smooth(t, E["lid"], E["lid"] + 0.4)
    draw_drain(ctx, t)
    draw_vent(ctx, t)
    draw_toilet(ctx, t, seat=seat, lid=lid, tank=tank)
    draw_waste_in_bowl(ctx, t)
    draw_gas(ctx, t)
    draw_siphon_arrows(ctx, t)
    draw_gurgle(ctx, t)
    # buckets of water (paragraph 3 and the big flush in paragraph 6)
    for t0, t1, big in ((E["bucket"] - 0.5, E["push"] + 0.9, False), (E["bigflush"] - 0.5, E["rush"] + 0.4, True)):
        if t0 < t < t1:
            sc = CH.scale_at(0)
            tilt = smooth(t, t0 + 0.3, t0 + 0.9) * (1.9 if big else 1.6)
            k = smooth(t, t0, t0 + 0.4) * (1 - smooth(t, t1 - 0.3, t1))
            bx, by = TP(0.9, 1.15)
            pour = smooth(t, t0 + 0.7, t0 + 1.0) * (1 - smooth(t, t1 - 0.6, t1 - 0.2))
            ctx.save()
            ctx.translate(0, (1 - k) * -300)
            bucket(ctx, bx, by, (0.42 if big else 0.32) * sc, -tilt + 0.0, pour, t, TP(0.55, 0.36))
            ctx.restore()
    # a pile of buckets for "nobody wants to carry buckets every time"
    if E["lazy"] - 0.1 < t < E["tank"]:
        k = pop(t, E["lazy"], 0.4) * (1 - smooth(t, E["tank"] - 0.4, E["tank"]))
        if k < 0.03:
            return
        sc = CH.scale_at(0)
        for i, (du, dv) in enumerate(((1.25, 0.12), (1.55, 0.12), (1.4, 0.42))):
            bx, by = TP(du, dv)
            ctx.save()
            ctx.translate(bx, by)
            ctx.scale(max(k, 0.02), max(k, 0.02))
            bucket(ctx, 0, 0, 0.3 * sc, 0.0)
            ctx.restore()
        cx, cy = TP(1.4, 0.75)
        ctx.save()
        ctx.translate(cx + 40, cy - 10)
        ctx.scale(max(k * 0.8, 0.02), max(k * 0.8, 0.02))
        for ang in (math.pi / 4, -math.pi / 4):
            ctx.save()
            ctx.rotate(ang)
            rounded_rect(ctx, -60, -10, 120, 20, 10)
            set_src(ctx, C["red"])
            ctx.fill()
            ctx.restore()
        ctx.restore()
    if E["trap_name"] - 0.1 < t < E["trap_name"] + 1.4:
        trap, _ = trap_shape(t)
        c = TP(*trap[CREST_I - 1])
        ctx.arc(c[0], c[1] + 10, 0.2 * CH.scale_at(0) * TS, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9 * (1 - smooth(t, E["trap_name"] + 1.0, E["trap_name"] + 1.4)))
        ctx.set_line_width(5)
        ctx.stroke()


# =============================================================== SET 3: rooftop exterior
CR = Cam(dist=9.0, height=4.0, pitch_deg=-8.0, focal=1350.0, horizon_y=900.0)
PR = CR.p


def draw_rooftop(ctx, t):
    draw_sky(ctx, t)
    draw_far(ctx, PR, 40)
    haze(ctx, 0, 1100, amount=0.25)
    # a closer villa roofline
    draw_villa(ctx, lambda x, y, z: PR(x, y + 2, z - 3.6), lambda y: CR.scale_at(y + 2), 4.0, t)
    yH = 6.0
    # vent stack rising above the parapet
    base, top = PR(1.2, yH - 0.6, 6.6 - 3.6 + 0.75), PR(1.2, yH - 0.6, 6.6 - 3.6 + 3.2)
    sc = CR.scale_at(yH)
    soft_shadow(ctx, base[0] + 30, base[1], 70, 12, 0.35)
    cylinder_v(ctx, base[0], top[1], base[1], 0.22 * sc, 0.07 * sc, C["pvc"])
    rounded_rect(ctx, top[0] - 0.34 * sc, top[1] - 0.2 * sc, 0.68 * sc, 0.2 * sc, 8)
    set_src(ctx, hexc("#d9dee3"))
    ctx.fill()
    # "not a chimney": brick chimney icon gets a red X
    if t > E["chimney"] - 0.2:
        k = pop(t, E["chimney"] - 0.2, 0.35)
        cx, cy = W * 0.24, 820
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(max(k, 0.02), max(k, 0.02))
        rounded_rect(ctx, -70, -130, 140, 220, 8)
        ctx.set_source(lgrad(-70, 0, 70, 0, [(0, hexc("#8a3a24")), (0.5, hexc("#c25a3a")), (1, hexc("#7a3220"))]))
        ctx.fill()
        for r in range(7):
            ctx.move_to(-70, -130 + r * 32)
            ctx.line_to(70, -130 + r * 32)
            ctx.set_source_rgba(0.95, 0.85, 0.75, 0.6)
            ctx.set_line_width(3)
            ctx.stroke()
        for i in range(3):
            ctx.arc(-20 + i * 25, -170 - i * 40 - (t * 30) % 30, 26 + i * 8, 0, 2 * math.pi)
            ctx.set_source_rgba(0.6, 0.6, 0.62, 0.55)
            ctx.fill()
        kx = pop(t, E["chimney"] + 0.3, 0.3)
        ctx.scale(max(kx, 0.02), max(kx, 0.02))
        for ang in (math.pi / 4, -math.pi / 4):
            ctx.save()
            ctx.rotate(ang)
            rounded_rect(ctx, -140, -16, 280, 32, 16)
            set_src(ctx, C["red"])
            ctx.fill()
            ctx.restore()
        ctx.restore()
    # breathing: air flowing in and out of the vent
    if t > E["breathe"] - 0.3:
        a = smooth(t, E["breathe"] - 0.3, E["breathe"] + 0.2)
        for i in range(6):
            ph = ((t - E["breathe"]) * 0.8 + i / 6) % 1.0
            ctx.arc(top[0] + 25 * math.sin(i * 2 + t), top[1] - 30 - ph * 260, 14 + 30 * ph, 0, 2 * math.pi)
            ctx.set_source_rgba(0.9, 0.97, 1, 0.55 * (1 - ph) * a)
            ctx.fill()
    arrow_y = top[1] - 140
    if E["see"] + 0.3 < t < E["chimney"]:
        k = pop(t, E["see"] + 0.3, 0.35)
        ctx.save()
        ctx.translate(top[0] + 170, arrow_y)
        ctx.scale(max(k, 0.02), max(k, 0.02))
        arrow(ctx, 0, 0, 120, 44, math.pi * 0.85, (1, 0.85, 0.25, 1))
        ctx.restore()


# =============================================================== finale
def draw_confetti(ctx, t, t0, dur=2.6, n=90, seed=1):
    if not (t0 <= t <= t0 + dur):
        return
    rnd = RNDS(seed)
    age = t - t0
    cols = [hexc("#ffcc22"), hexc("#22b5ff"), hexc("#ff4f7a"), hexc("#7bdc4a"), hexc("#ffffff")]
    for i in range(n):
        x = rnd.uniform(0.15, 0.85) * W + rnd.uniform(-260, 260) * age
        y = 1100 + rnd.uniform(-1200, -700) * age + 900 * age * age
        a = clamp((dur - age) / 0.4)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rnd.uniform(0, 6) + age * rnd.uniform(-8, 8))
        ctx.scale(1, max(0.05, abs(math.sin(age * rnd.uniform(6, 12) + i))))
        ctx.rectangle(-9, -5, 18, 10)
        set_src(ctx, alpha(cols[i % len(cols)], a))
        ctx.fill()
        ctx.restore()
