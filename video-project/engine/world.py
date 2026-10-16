"""The pool story, drawn frame by frame with the 2.5D toolkit.

draw_frame(ctx, t) paints the whole picture for time t (seconds).  Every event
time comes from scripts/shotplan.py (word-aligned to the voiceover).
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
                  cylinder_v, cylinder_h, pipe, polyline_point, round_corners, arrow, chevron,
                  soil_texture, lawn_texture, cloud_sprite, concrete_texture, paint_surface)

E = SP.E
CAM = Cam(dist=12.0, height=3.4, pitch_deg=10.0, focal=1420.0, horizon_y=800.0)
P = CAM.p

# ------------------------------------------------------------------ pool geometry (metres)
IX = 3.6          # inner half width
PB = 3.4          # back wall (pool runs from the cut plane y=0 back to y=PB)
TH = 0.30         # shell thickness
OX = IX + TH
SHALLOW, DEEP = -1.25, -2.15
X_SLOPE0, X_SLOPE1 = -0.6, 1.1
WL = -0.18        # full water level
VALVE_X = 2.55
DRAIN_X = 1.65


def floor_in(x):
    if x <= X_SLOPE0:
        return SHALLOW
    if x >= X_SLOPE1:
        return DEEP
    return lerp(SHALLOW, DEEP, (x - X_SLOPE0) / (X_SLOPE1 - X_SLOPE0))


def floor_out(x):
    return floor_in(clamp(x, -IX, IX)) - TH


def profile_x(x0, x1, n=40):
    return [x0 + (x1 - x0) * i / n for i in range(n + 1)]


# ------------------------------------------------------------------ palette
C = {
    "sky_top": hexc("#7fb2e5"), "sky_low": hexc("#dfeaf2"),
    "lawn": hexc("#5c9a2c"), "lawn2": hexc("#4d8a24"), "lawn_dark": hexc("#3c6e1c"),
    "soil": hexc("#8a5a33"), "soil_top": hexc("#5a3a1f"), "dirt": hexc("#7a5030"), "dirt_dark": hexc("#5b3a20"),
    "concrete": hexc("#c9c6bf"), "concrete_dark": hexc("#9d9a93"), "red": hexc("#c8462f"),
    "water": hexc("#55c4ec"), "water_deep": hexc("#1f86c6"), "water_top": hexc("#9fe2f7"),
    "algae": hexc("#6f9a2a"), "algae_deep": hexc("#3f6a18"),
    "gw": hexc("#2f6fd6"), "white": hexc("#f4f6f8"), "pvc": hexc("#eef1f4"),
    "rebar": hexc("#9b4a2c"), "tile": hexc("#3aa7d8"), "tile2": hexc("#2b8fc4"),
    "house": hexc("#efe2c8"), "house_shadow": hexc("#d8c8a8"), "trim": hexc("#b8946a"),
    "glass": hexc("#3a5f80"), "wood": hexc("#7a4a26"), "wall": hexc("#e2cfa9"),
    "palm": hexc("#3f7a2a"), "trunk": hexc("#8a6a44"), "pump": hexc("#1f5fae"), "tank": hexc("#1f9aa6"),
    "sand": hexc("#e2c58e"), "gravel": hexc("#a8a39a"), "brass": hexc("#d9a440"),
    "leaf": hexc("#7fae2a"), "leaf2": hexc("#d99a2a"), "pebble": hexc("#8d8a85"),
    "bact": hexc("#7fd04a"), "chlor": hexc("#e8ff7a"), "outline": hexc("#1d2733"),
}

# ------------------------------------------------------------------ cached textures
_TEX = {}


def tex(name):
    if name not in _TEX:
        if name == "soil":
            _TEX[name] = soil_texture(1200, 1300, seed=3)
        elif name == "lawn":
            _TEX[name] = lawn_texture(800, 400, seed=5)
        elif name == "concrete":
            _TEX[name] = concrete_texture(400, 400, seed=9)
        elif name.startswith("cloud"):
            _TEX[name] = cloud_sprite(520, 220, seed=int(name[5:]))
    return _TEX[name]


def poly3(pts):
    return [P(*p) for p in pts]


def clip_poly(ctx, pts):
    path_poly(ctx, pts)
    ctx.clip()


def textured_poly(ctx, pts, base, texname=None, tex_alpha=0.45, box=None):
    fill_poly(ctx, pts, base)
    if texname:
        ctx.save()
        clip_poly(ctx, pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0 = min(xs), min(ys)
        sw, sh = max(xs) - x0, max(ys) - y0
        if box:
            x0, y0, sw, sh = box
        paint_surface(ctx, tex(texname), x0, y0, max(sw, 2), max(sh, 2), alpha_=tex_alpha)
        ctx.restore()


# ------------------------------------------------------------------ background
def draw_sky(ctx, t, night=0.0):
    top = mix(C["sky_top"], hexc("#1c2d55"), night)
    low = mix(C["sky_low"], hexc("#3a4f7a"), night)
    ctx.rectangle(-W, -H, 3 * W, 3 * H)
    ctx.set_source(lgrad(0, 0, 0, 760, [(0, top), (1, low)]))
    ctx.fill()
    for i, (x, y, s) in enumerate(((120, 120, 1.0), (640, 70, 1.25), (930, 230, 0.8), (380, 300, 0.7))):
        xx = (x + t * (6 + 3 * i)) % (W + 600) - 300
        paint_surface(ctx, tex(f"cloud{i}"), xx - 260 * s, y - 110 * s, 520 * s, 220 * s, alpha_=0.95 * (1 - night * 0.6))


def draw_sun(ctx, t):
    """Sun arcing across the sky during the 'week under the sun' montage."""
    a = lin(t, E["week"] - 0.3, E["green"] + 0.5)
    if a <= 0 or a >= 1:
        return 0.0
    cycles = 3
    ph = (a * cycles) % 1.0
    x = lerp(-80, W + 80, ph)
    y = 420 - math.sin(ph * math.pi) * 330
    night = max(0.0, 1 - math.sin(ph * math.pi) * 2.2) * 0.6
    ctx.arc(x, y, 60, 0, 2 * math.pi)
    ctx.set_source(rgrad(x, y, 10, 160, [(0, (1, 0.97, 0.75, 1)), (0.35, (1, 0.9, 0.5, 0.65)), (1, (1, 0.8, 0.4, 0))]))
    ctx.arc(x, y, 160, 0, 2 * math.pi)
    ctx.fill()
    sphere(ctx, x, y, 48, (1.0, 0.92, 0.55, 1))
    return night


def draw_trees_far(ctx):
    rnd = random.Random(4)
    for i in range(40):
        x = -W + i * 80 + rnd.uniform(-20, 20)
        y0 = P(0, 26, 0)[1]
        r = rnd.uniform(40, 70)
        for k in range(3):
            sphere(ctx, x + rnd.uniform(-25, 25), y0 - r * 0.9 - k * r * 0.45, r * rnd.uniform(0.7, 1.0),
                   mix(hexc("#5f8a4a"), hexc("#7aa05e"), rnd.random()), light=(-0.2, -0.5))


def draw_palm(ctx, base, height, sway=0.0, scale=1.0):
    bx, by = base
    top = (bx + 18 * scale + sway * 6, by - height)
    pts = [(bx - 9 * scale, by), (top[0] - 6 * scale, top[1]), (top[0] + 6 * scale, top[1]), (bx + 9 * scale, by)]
    ctx.set_source(lgrad(bx - 10, 0, bx + 10, 0, [(0, shade(C["trunk"], 0.7)), (0.5, shade(C["trunk"], 1.15)), (1, shade(C["trunk"], 0.6))]))
    path_poly(ctx, pts)
    ctx.fill()
    for k in range(9):
        yy = lerp(by, top[1], (k + 0.5) / 9)
        xx = lerp(bx, top[0], (k + 0.5) / 9)
        ctx.move_to(xx - 8 * scale, yy)
        ctx.line_to(xx + 8 * scale, yy - 3 * scale)
        ctx.set_source_rgba(*shade(C["trunk"], 0.55)[:3], 0.6)
        ctx.set_line_width(2 * scale)
        ctx.stroke()
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.42 + sway * 0.05
        L = 95 * scale * (0.85 + 0.25 * ((k * 7) % 3) / 2)
        tip = (top[0] + math.cos(a) * L, top[1] + math.sin(a) * L * 0.55 + abs(k - 4) * 9 * scale)
        mid = (top[0] + math.cos(a) * L * 0.5, top[1] + math.sin(a) * L * 0.5 - 18 * scale)
        nx, ny = -(tip[1] - top[1]), tip[0] - top[0]
        nl = math.hypot(nx, ny) or 1
        nx, ny = nx / nl * 13 * scale, ny / nl * 13 * scale
        ctx.move_to(*top)
        ctx.curve_to(mid[0] + nx, mid[1] + ny, mid[0] + nx, mid[1] + ny, *tip)
        ctx.curve_to(mid[0] - nx, mid[1] - ny, mid[0] - nx, mid[1] - ny, *top)
        set_src(ctx, shade(C["palm"], 0.85 + 0.08 * (k % 3)))
        ctx.fill()
    sphere(ctx, top[0], top[1] + 4, 9 * scale, shade(C["trunk"], 0.8))


def draw_house(ctx, t):
    yH = 15.0
    x0, x1 = -7.2, 7.2
    # boundary wall left/right of the house
    for (a, b) in ((-14, x0), (x1, 14)):
        pts = poly3([(a, yH + 0.5, 0), (b, yH + 0.5, 0), (b, yH + 0.5, 2.6), (a, yH + 0.5, 2.6)])
        fill_poly(ctx, pts, C["wall"])
        fill_poly(ctx, poly3([(a, yH + 0.5, 2.6), (b, yH + 0.5, 2.6), (b, yH + 0.5, 2.85), (a, yH + 0.5, 2.85)]), C["trim"])
    # house body (two volumes)
    def facade(xa, xb, z0, z1, y, col):
        fill_poly(ctx, poly3([(xa, y, z0), (xb, y, z0), (xb, y, z1), (xa, y, z1)]), col)
    facade(x0, x1, 0, 6.6, yH, C["house"])
    facade(-4.5, 2.8, 6.6, 10.0, yH + 1.0, shade(C["house"], 0.96))
    # parapet with crenellation
    for (xa, xb, z, y) in ((x0 - 0.15, x1 + 0.15, 6.6, yH - 0.05), (-4.65, 2.95, 10.0, yH + 0.95)):
        facade(xa, xb, z, z + 0.45, y, C["trim"])
        n = int((xb - xa) / 0.7)
        for k in range(n):
            xa2 = xa + k * (xb - xa) / n + 0.12
            facade(xa2, xa2 + 0.3, z + 0.45, z + 0.75, y, C["trim"])
    # shading under parapet
    pts = poly3([(x0, yH - 0.04, 6.25), (x1, yH - 0.04, 6.25), (x1, yH - 0.04, 6.6), (x0, yH - 0.04, 6.6)])
    fill_poly(ctx, pts, alpha(C["house_shadow"], 0.8))
    # arched windows with frames
    for wx in (-5.4, -2.4, 2.4, 5.4):
        for wz, hgt in ((1.0, 2.0), (3.9, 1.8)):
            a, b = P(wx - 0.6, yH - 0.02, wz), P(wx + 0.6, yH - 0.02, wz + hgt)
            x, y, w, h = a[0], b[1], b[0] - a[0], a[1] - b[1]
            ctx.save()
            ctx.new_path()
            ctx.move_to(x, y + w / 2)
            ctx.arc(x + w / 2, y + w / 2, w / 2, math.pi, 0)
            ctx.line_to(x + w, y + h)
            ctx.line_to(x, y + h)
            ctx.close_path()
            ctx.set_source(lgrad(0, y, 0, y + h, [(0, shade(C["glass"], 1.3)), (1, C["glass"])]))
            ctx.fill_preserve()
            set_src(ctx, C["trim"])
            ctx.set_line_width(4)
            ctx.stroke()
            ctx.move_to(x + w / 2, y)
            ctx.line_to(x + w / 2, y + h)
            ctx.set_line_width(2.5)
            ctx.stroke()
            ctx.restore()
            sill = poly3([(wx - 0.75, yH - 0.1, wz - 0.12), (wx + 0.75, yH - 0.1, wz - 0.12), (wx + 0.75, yH - 0.1, wz), (wx - 0.75, yH - 0.1, wz)])
            fill_poly(ctx, sill, shade(C["trim"], 1.1))
    for wx in (-3.0, 0.6):
        a, b = P(wx - 0.5, yH + 0.98, 7.3), P(wx + 0.5, yH + 0.98, 9.0)
        rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 6)
        set_src(ctx, C["glass"])
        ctx.fill()
    # door + canopy
    a, b = P(-0.85, yH - 0.03, 0), P(0.85, yH - 0.03, 2.7)
    rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 4)
    ctx.set_source(lgrad(a[0], 0, b[0], 0, [(0, shade(C["wood"], 0.8)), (0.5, shade(C["wood"], 1.1)), (1, shade(C["wood"], 0.75))]))
    ctx.fill()
    ctx.move_to((a[0] + b[0]) / 2, b[1])
    ctx.line_to((a[0] + b[0]) / 2, a[1])
    set_src(ctx, shade(C["wood"], 0.5))
    ctx.set_line_width(2)
    ctx.stroke()
    fill_poly(ctx, poly3([(-1.6, yH - 0.9, 3.05), (1.6, yH - 0.9, 3.05), (1.6, yH, 3.05), (-1.6, yH, 3.05)]), shade(C["trim"], 0.9))
    fill_poly(ctx, poly3([(-1.6, yH - 0.9, 2.9), (1.6, yH - 0.9, 2.9), (1.6, yH - 0.9, 3.05), (-1.6, yH - 0.9, 3.05)]), C["trim"])
    # AC units
    for ax in (-6.3, 6.1):
        a, b = P(ax - 0.45, yH - 0.25, 4.9), P(ax + 0.45, yH - 0.25, 5.55)
        rounded_rect(ctx, a[0], b[1], b[0] - a[0], a[1] - b[1], 3)
        set_src(ctx, hexc("#f1f1ee"))
        ctx.fill()
        ellipse(ctx, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (b[0] - a[0]) * 0.28, (a[1] - b[1]) * 0.33)
        set_src(ctx, hexc("#5a5f63"))
        ctx.fill()
    # patio slab in front of the house
    fill_poly(ctx, poly3([(-7.6, yH - 2.2, 0.02), (7.6, yH - 2.2, 0.02), (7.6, yH, 0.02), (-7.6, yH, 0.02)]), hexc("#d9c9ad"))
    for k in range(9):
        xa = -7.6 + k * 1.9
        ctx.move_to(*P(xa, yH - 2.2, 0.03))
        ctx.line_to(*P(xa, yH, 0.03))
        ctx.set_source_rgba(0.6, 0.53, 0.43, 0.6)
        ctx.set_line_width(1.5)
        ctx.stroke()
    # potted plants + palms
    for px in (-6.6, -1.6, 1.6, 6.6):
        b = P(px, yH - 1.0, 0)
        s = CAM.scale_at(yH - 1.0)
        cylinder_v(ctx, b[0], b[1] - 0.6 * s, b[1], 0.3 * s, 0.09 * s, hexc("#b8643a"))
        for k in range(5):
            sphere(ctx, b[0] + (k - 2) * 0.13 * s, b[1] - 0.95 * s - (k % 2) * 0.2 * s, 0.32 * s,
                   hexc("#d0447a") if k % 2 else hexc("#4f8f30"))
    sway = math.sin(t * 1.3)
    for (px, py, ht, sc) in ((-9.8, 13.5, 7.5, 1.15), (9.6, 13.8, 6.6, 1.05), (-12.0, 9.0, 6.0, 1.2), (12.2, 9.5, 6.2, 1.25)):
        b = P(px, py, 0)
        s = CAM.scale_at(py)
        draw_palm(ctx, b, ht * s, sway, scale=sc * s / 30)


def draw_lawn(ctx, t):
    yb = 16.0
    pts = poly3([(-30, 0, 0), (30, 0, 0), (30, yb, 0), (-30, yb, 0)])
    pts_h = P(0, yb, 0)[1]
    ctx.set_source(lgrad(0, pts_h, 0, P(0, 0, 0)[1], [(0, shade(C["lawn"], 0.92)), (1, shade(C["lawn"], 1.05))]))
    path_poly(ctx, pts)
    ctx.fill()
    # mowing stripes (diagonal, as in the references)
    ctx.save()
    clip_poly(ctx, pts)
    for k in range(-30, 30, 2):
        q = poly3([(k, 0, 0), (k + 1, 0, 0), (k + 1 + 6, yb, 0), (k + 6, yb, 0)])
        fill_poly(ctx, q, alpha(C["lawn2"], 0.55))
    paint_surface(ctx, tex("lawn"), 0, pts_h, W, P(0, 0, 0)[1] - pts_h, alpha_=0.35)
    ctx.restore()


# ------------------------------------------------------------------ pool parts
def pit_depth_factor(t):
    """0 = flat ground (not dug), 1 = full pit."""
    return smooth(t, E["dig"], E["dig_end"] + 0.4)


def outer_profile(d=1.0):
    xs = profile_x(-OX, OX, 48)
    return [(x, floor_out(x) * d) for x in xs]


def inner_profile():
    xs = profile_x(-IX, IX, 48)
    return [(x, floor_in(x)) for x in xs]


def draw_box_interior(ctx, X, Y, prof, cols, dz=0.0, tilt=0.0):
    """Interior faces of an open box cut at y=0: back wall, floor segments, side walls.
    prof: [(x, floor_z)] across the width.  cols: dict(back, floor, side_l, side_r)."""
    def q(pts):
        return poly3([(x, y, z + dz + tilt * x) for x, y, z in pts])
    # back wall
    back = [(X[0], Y, dz)] + [(x, Y, z) for x, z in prof] + [(X[1], Y, 0)]
    back = [(x, Y, (0 if i in (0, len(back) - 1) else z)) for i, (x, _, z) in enumerate(back)]
    fill_poly(ctx, q(back), cols["back"])
    # floor
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        slope = abs(zb - za) / max(xb - xa, 1e-6)
        col = shade(cols["floor"], 1.0 - min(0.25, slope * 0.35))
        fill_poly(ctx, q([(xa, 0, za), (xb, 0, zb), (xb, Y, zb), (xa, Y, za)]), col, seam=True)
    # side walls
    fill_poly(ctx, q([(X[0], 0, prof[0][1]), (X[0], Y, prof[0][1]), (X[0], Y, 0), (X[0], 0, 0)]), cols["side_l"])
    fill_poly(ctx, q([(X[1], 0, prof[-1][1]), (X[1], Y, prof[-1][1]), (X[1], Y, 0), (X[1], 0, 0)]), cols["side_r"])


def interior_polys(X, Y, prof, dz=0.0):
    out = []
    back = [(X[0], Y, 0)] + [(x, Y, z) for x, z in prof] + [(X[1], Y, 0)]
    out.append(poly3([(x, y, z + dz) for x, y, z in back]))
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        out.append(poly3([(xa, 0, za + dz), (xb, 0, zb + dz), (xb, Y, zb + dz), (xa, Y, za + dz)]))
    out.append(poly3([(X[0], 0, prof[0][1] + dz), (X[0], Y, prof[0][1] + dz), (X[0], Y, dz), (X[0], 0, dz)]))
    out.append(poly3([(X[1], 0, prof[-1][1] + dz), (X[1], Y, prof[-1][1] + dz), (X[1], Y, dz), (X[1], 0, dz)]))
    return out


def water_level(t):
    k = [(0, None)]
    if t < E["fill"]:
        return None
    if t < E["fix"]:
        lvl = keyed(t, [(E["fill"], DEEP - TH - 0.3), (E["pool"] - 0.2, WL), (E["seep"], WL), (E["collapse_end"], -1.9)])
        return ("pit", lvl)
    if t < E["holds"] - 0.05:
        return None
    if t < E["drain"] + 1.3:
        lvl = keyed(t, [(E["holds"], DEEP - 0.01), (E["holds"] + 1.0, WL), (E["drain"], WL), (E["drain"] + 1.2, DEEP - 0.01)])
        return ("pool", lvl)
    if t < E["valve_open"] + 0.1:
        return None
    if t < E["week"] - 0.4:
        lvl = keyed(t, [(E["valve_open"] + 0.1, DEEP - 0.01), (E["no_lift"] + 0.8, DEEP + 0.35)])
        return ("pool", lvl)
    return ("pool", WL)


def water_color(t):
    g = keyed(t, [(0, 0.0), (E["collapse"], 0.0), (E["collapse_end"], 0.0),
                  (E["green"] - 0.5, 0.0), (E["green"] + 0.8, 1.0), (E["clean"], 1.0), (E["clean"] + 1.2, 0.0)])
    mud = keyed(t, [(E["collapse"], 0.0), (E["collapse_end"], 0.7), (E["fix"] - 0.01, 0.7), (E["fix"], 0.0)])
    top = mix(mix(C["water_top"], hexc("#b8d66a"), g), hexc("#b89464"), mud)
    front = mix(mix(C["water"], C["algae"], g), hexc("#8a6a44"), mud)
    deep = mix(mix(C["water_deep"], C["algae_deep"], g), hexc("#5a4026"), mud)
    return top, front, deep, g


def draw_water(ctx, t, X, Y, prof_fn, lvl, dz=0.0, front_only=False):
    top_c, front_c, deep_c, g = water_color(t)
    xs = profile_x(X[0], X[1], 60)
    wet = [x for x in xs if prof_fn(x) < lvl - 0.005]
    if len(wet) < 2:
        return
    xa, xb = wet[0], wet[-1]
    # top surface (seen from above)
    if not front_only:
        top = poly3([(xa, 0, lvl + dz), (xb, 0, lvl + dz), (xb, Y, lvl + dz), (xa, Y, lvl + dz)])
        ys = [p[1] for p in top]
        fill_poly(ctx, top, lgrad(0, min(ys), 0, max(ys), [(0, alpha(shade(top_c, 1.05), 0.85)), (1, alpha(top_c, 0.75))]))
        ctx.save()
        clip_poly(ctx, top)
        for k in range(14):
            yy = (k / 14 * Y + t * 0.25) % Y
            pts = []
            for i in range(25):
                x = lerp(xa, xb, i / 24)
                pts.append(P(x, yy + 0.06 * math.sin(x * 2.3 + t * 2 + k), lvl + dz))
            path_poly(ctx, pts, close=False)
            ctx.set_source_rgba(1, 1, 1, 0.22)
            ctx.set_line_width(2)
            ctx.stroke()
        ctx.restore()
    # front face (section through the water)
    pts = [P(x, 0, lvl + dz) for x in wet] + [P(x, 0, prof_fn(x) + dz) for x in reversed(wet)]
    ys = [p[1] for p in pts]
    fill_poly(ctx, pts, lgrad(0, min(ys), 0, max(ys), [(0, alpha(shade(front_c, 1.1), 0.62)), (1, alpha(deep_c, 0.78))]))
    ctx.save()
    clip_poly(ctx, pts)
    # caustic wiggles
    for k in range(6):
        z = lvl - 0.25 - k * 0.32
        line = [P(x, 0, z + dz + 0.04 * math.sin(x * 3 + t * 2.4 + k)) for x in profile_x(xa, xb, 30)]
        path_poly(ctx, line, close=False)
        ctx.set_source_rgba(1, 1, 1, 0.13)
        ctx.set_line_width(3)
        ctx.stroke()
    ctx.restore()
    # bright surface line
    path_poly(ctx, [P(xa, 0, lvl + dz), P(xb, 0, lvl + dz)], close=False)
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(4)
    ctx.stroke()


def draw_soil_face(ctx, t, hole=None, gw_level=None):
    """The cut face of the ground (y = 0) with an optional hole (pit section)."""
    top = P(-30, 0, 0)[1]
    ctx.save()
    ctx.rectangle(-500, top, W + 1000, H + 600)
    if hole:
        path_poly(ctx, [P(x, 0, z) for x, z in hole])
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.clip()
    for ox in (-W - 60, -60, W + 60):
        paint_surface(ctx, tex("soil"), ox, top - 10, W + 120, H - top + 300)
    # dark topsoil band + grass lip
    ctx.rectangle(-500, top, W + 1000, 26)
    ctx.set_source(lgrad(0, top, 0, top + 26, [(0, (0.24, 0.16, 0.08, 0.9)), (1, (0.24, 0.16, 0.08, 0))]))
    ctx.fill()
    ctx.restore()
    if gw_level is not None and gw_level > -14:
        # groundwater fills the soil AND any empty part of the pit below its level
        ctx.save()
        ctx.rectangle(-W, top, 3 * W, H * 2)
        ctx.clip()
        gy = P(0, 0, gw_level)[1]
        pts = [(x, gy + 6 * math.sin(x / 40 + t * 2)) for x in range(-W, 2 * W, 20)]
        path_poly(ctx, pts + [(2 * W, H + 500), (-W, H + 500)])
        ctx.set_source(lgrad(0, gy, 0, H, [(0, alpha(C["gw"], 0.62)), (1, alpha(shade(C["gw"], 0.7), 0.75))]))
        ctx.fill()
        path_poly(ctx, pts, close=False)
        ctx.set_source_rgba(0.75, 0.9, 1, 0.8)
        ctx.set_line_width(4)
        ctx.stroke()
        ctx.restore()
    # grass tufts along the top edge
    rnd = random.Random(2)
    for x in range(-10, W + 10, 9):
        if hole:
            wx = (x - W / 2) / CAM.scale_at(0)
            if -OX - 0.05 < wx < OX + 0.05 and pit_depth_factor(t) > 0.05:
                continue
        h = rnd.uniform(8, 18)
        ctx.move_to(x, top + 4)
        ctx.line_to(x + rnd.uniform(-4, 4), top - h)
        ctx.line_to(x + 5, top + 4)
        set_src(ctx, shade(C["lawn"], rnd.uniform(0.8, 1.15)))
        ctx.fill()


def draw_shell_band(ctx, t, reveal=1.0, dz=0.0, tilt=0.0):
    """U-shaped concrete section of the shell with a red waterproof line and rebar dots."""
    if reveal <= 0:
        return
    outer = [(-OX, 0)] + [(x, floor_out(x)) for x in profile_x(-OX, OX, 48)] + [(OX, 0)]
    inner = [(IX, 0)] + [(x, floor_in(x)) for x in profile_x(IX, -IX, 48)] + [(-IX, 0)]
    pts = [P(x, 0, z + dz + tilt * x) for x, z in outer + inner]
    ctx.save()
    if reveal < 1:
        xr = P(lerp(-OX - 0.1, OX + 0.1, reveal), 0, 0)[0]
        ctx.rectangle(-200, -200, xr + 200, H + 400)
        ctx.clip()
    textured_poly(ctx, pts, C["concrete"], "concrete", 0.6)
    # red waterproof membrane line close to the outside
    mid = [(-OX + 0.08, 0)] + [(x, floor_out(x) + 0.08) for x in profile_x(-OX + 0.08, OX - 0.08, 48)] + [(OX - 0.08, 0)]
    path_poly(ctx, [P(x, 0, z + dz + tilt * x) for x, z in mid], close=False)
    set_src(ctx, C["red"])
    ctx.set_line_width(5)
    ctx.stroke()
    # rebar dots
    mid2 = [(x, floor_out(x) + TH * 0.55) for x in profile_x(-OX + 0.2, OX - 0.2, 22)]
    mid2 += [(-OX + TH * 0.5, z) for z in (-0.3, -0.7)] + [(OX - TH * 0.5, z) for z in (-0.3, -0.7, -1.1, -1.5)]
    for x, z in mid2:
        sx, sy = P(x, 0, z + dz + tilt * x)
        ctx.arc(sx, sy, 3.2, 0, 2 * math.pi)
        set_src(ctx, C["rebar"])
        ctx.fill()
    # coping / top rim
    for xa, xb in ((-OX, -IX), (IX, OX)):
        fill_poly(ctx, poly3([(xa, 0, dz + tilt * xa), (xb, 0, dz + tilt * xb), (xb, PB + TH, dz + tilt * xb), (xa, PB + TH, dz + tilt * xa)]), shade(C["concrete"], 1.08))
    fill_poly(ctx, poly3([(-OX, PB, dz - tilt * OX), (OX, PB, dz + tilt * OX), (OX, PB + TH, dz + tilt * OX), (-OX, PB + TH, dz - tilt * OX)]), shade(C["concrete"], 1.08))
    ctx.restore()


def draw_tiles(ctx, t, polys, amount):
    if amount <= 0:
        return
    for pts in polys:
        ctx.save()
        xr = lerp(-50, W + 50, amount)
        ctx.rectangle(-100, -100, xr + 100, H + 200)
        ctx.clip()
        fill_poly(ctx, pts, alpha(C["tile"], 0.92))
        ctx.restore()


def tile_grid(ctx, X, Y, prof, amount, dz=0.0):
    """Grout lines in perspective over the tiled interior."""
    if amount <= 0:
        return
    ctx.save()
    xr = lerp(-50, W + 50, amount)
    ctx.rectangle(-100, -100, xr + 100, H + 200)
    ctx.clip()
    ctx.set_source_rgba(0.92, 0.97, 1, 0.55)
    ctx.set_line_width(1.5)
    step = 0.3
    x = X[0]
    while x <= X[1] + 1e-6:
        z = floor_in(x)
        path_poly(ctx, [P(x, Y, 0 + dz), P(x, Y, z + dz), P(x, 0, z + dz)], close=False)
        ctx.stroke()
        x += step
    z = -step
    while z > DEEP:
        xa = X[0] if z > SHALLOW else lerp(X_SLOPE0, X_SLOPE1, (z - SHALLOW) / (DEEP - SHALLOW))
        path_poly(ctx, [P(xa, Y, z + dz), P(X[1], Y, z + dz)], close=False)
        ctx.stroke()
        for xs_ in (X[0], X[1]):
            if floor_in(xs_) < z:
                path_poly(ctx, [P(xs_, 0, z + dz), P(xs_, Y, z + dz)], close=False)
                ctx.stroke()
        z -= step
    y = step
    while y < Y:
        pts = [P(x, y, floor_in(x) + dz) for x in profile_x(X[0], X[1], 24)]
        path_poly(ctx, pts, close=False)
        ctx.stroke()
        y += step
    ctx.restore()


# ------------------------------------------------------------------ story elements
RND = random.Random(11)
CHUNKS = [(RND.uniform(-OX + 0.2, OX - 0.2), RND.uniform(0.25, 0.5), RND.uniform(0, 0.9), RND.random()) for _ in range(14)]
LEAVES = [(RND.uniform(-3.0, 3.0), RND.uniform(0.4, PB - 0.4), RND.uniform(0, 6.28), RND.random()) for _ in range(14)]
PEBBLES = [(RND.uniform(-2.5, 3.0), RND.uniform(0.0, 0.9)) for _ in range(7)]


def draw_drops(ctx, t, t0, t1, n, area, speed, col, seed, size=7, fall=1.0):
    """Stateless falling droplets in screen space area=(x0,y0,x1,y1)."""
    if t < t0 or t > t1 + 1.5:
        return
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(area[0], area[2])
        ph = rnd.random()
        life = rnd.uniform(0.8, 1.4)
        age = ((t - t0) / life + ph) % 1.0
        if t - t0 < ph * life or (t > t1 and (t - t1) > (1 - age) * life):
            continue
        y = lerp(area[1], area[3], age * fall)
        a = math.sin(age * math.pi)
        ctx.save()
        ctx.translate(x, y)
        ctx.move_to(0, -size * 1.6)
        ctx.curve_to(size * 0.9, -size * 0.2, size * 0.8, size, 0, size)
        ctx.curve_to(-size * 0.8, size, -size * 0.9, -size * 0.2, 0, -size * 1.6)
        set_src(ctx, alpha(col, a))
        ctx.fill()
        ctx.restore()


def draw_shovel_and_pile(ctx, t):
    d = pit_depth_factor(t)
    if t > E["next_day"] + 0.3:
        return
    # dirt pile grows on the lawn behind-left
    s = smooth(t, E["dig"], E["dig_end"] + 0.4)
    if s > 0:
        b = P(-5.3, 2.2, 0)
        sc = CAM.scale_at(2.2)
        rx, ry = 1.5 * sc * s, 0.95 * sc * s
        ctx.save()
        ctx.move_to(b[0] - rx, b[1])
        ctx.curve_to(b[0] - rx * 0.6, b[1] - ry * 1.3, b[0] + rx * 0.6, b[1] - ry * 1.3, b[0] + rx, b[1])
        ctx.close_path()
        ctx.set_source(rgrad(b[0] - rx * 0.2, b[1] - ry * 0.8, 5, rx * 1.3, [(0, shade(C["dirt"], 1.25)), (1, shade(C["dirt"], 0.7))]))
        ctx.fill()
        ctx.restore()
    # flying clumps
    if E["dig"] < t < E["dig_end"] + 0.6:
        rnd = random.Random(5)
        for i in range(18):
            t0 = E["dig"] + i * (E["dig_end"] - E["dig"]) / 18
            age = (t - t0) / 0.6
            if 0 <= age <= 1:
                x0, y0 = P(rnd.uniform(-2, 2), 0.8, 0)
                x1, y1 = P(-5.3 + rnd.uniform(-0.6, 0.6), 2.2, 0.5)
                x = lerp(x0, x1, age)
                y = lerp(y0, y1, age) - math.sin(age * math.pi) * 180
                sphere(ctx, x, y, rnd.uniform(6, 11), C["dirt"])
    # shovel
    if t < E["dig_end"] + 0.8:
        k = (t - E["dig"]) / max(0.01, (E["dig_end"] - E["dig"]) / 4)
        ph = k % 1.0 if E["dig"] <= t <= E["dig_end"] else 0.0
        x = 1.6 - min(3, int(max(k, 0))) * 1.0 if t <= E["dig_end"] else -1.4
        z = 0.6 - math.sin(ph * math.pi) * (0.6 + 1.2 * d)
        ang = -0.5 + math.sin(ph * math.pi) * 0.4
        base = P(x, 0.9, z)
        sc = CAM.scale_at(0.9)
        ctx.save()
        ctx.translate(*base)
        ctx.rotate(ang)
        ctx.rectangle(-4, -1.6 * sc, 8, 1.6 * sc)
        set_src(ctx, C["wood"])
        ctx.fill()
        rounded_rect(ctx, -0.17 * sc, 0, 0.34 * sc, 0.42 * sc, 8)
        ctx.set_source(lgrad(-0.17 * sc, 0, 0.17 * sc, 0, [(0, hexc("#8d9399")), (0.5, hexc("#e2e6ea")), (1, hexc("#7a8086"))]))
        ctx.fill()
        ctx.restore()


def draw_hose(ctx, t):
    if not (E["fill"] - 0.2 < t < E["next_day"] + 0.3) and not (E["holds"] - 0.1 < t < E["holds"] + 1.1):
        return
    pts = [P(-6.5, 3.5, 0), P(-5.5, 2.4, 0.0), P(-4.6, 1.2, 0.05), P(-3.7, 1.0, 0.6), P(-3.2, 1.2, 0.75)]
    pipe(ctx, round_corners(pts, 30), 9, hexc("#2f9a4a"))
    lvl = water_level(t)
    if lvl:
        tip = pts[-1]
        endy = P(-2.9, 1.3, lvl[1])[1]
        for i in range(10):
            u = ((t * 3 + i / 10) % 1.0)
            x = tip[0] + u * 30
            y = tip[1] + (endy - tip[1]) * u * u
            ctx.arc(x, y, 4.5, 0, 2 * math.pi)
            ctx.set_source_rgba(0.7, 0.9, 1, 0.8)
            ctx.fill()
        ctx.move_to(*tip)
        ctx.curve_to(tip[0] + 15, tip[1], tip[0] + 30, tip[1] + 10, tip[0] + 30, endy)
        ctx.set_source_rgba(0.75, 0.92, 1, 0.65)
        ctx.set_line_width(7)
        ctx.stroke()


def draw_confetti(ctx, t, t0, dur=1.8, n=70, seed=1):
    if not (t0 <= t <= t0 + dur):
        return
    rnd = random.Random(seed)
    age = t - t0
    cols = [hexc("#ffcc22"), hexc("#22b5ff"), hexc("#ff4f7a"), hexc("#7bdc4a"), hexc("#ffffff")]
    for i in range(n):
        x0 = rnd.uniform(0.2, 0.8) * W
        vx = rnd.uniform(-260, 260)
        vy = rnd.uniform(-1150, -650)
        x = x0 + vx * age
        y = 1050 + vy * age + 900 * age * age
        a = clamp((dur - age) / 0.4)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rnd.uniform(0, 6) + age * rnd.uniform(-8, 8))
        ctx.scale(1, abs(math.sin(age * rnd.uniform(6, 12) + i)))
        ctx.rectangle(-9, -5, 18, 10)
        set_src(ctx, alpha(cols[i % len(cols)], a))
        ctx.fill()
        ctx.restore()


def draw_ring(ctx, t):
    vis = (E["pool"] - 0.05 < t < E["next_day"] + 0.3) or t > E["final"] + 0.5
    if not vis:
        return
    t0 = E["pool"] if t < E["final"] else E["final"] + 0.6
    x, y = (1.3, 1.6) if t < E["final"] else (-1.2, 1.9)
    fall = smooth(t, t0, t0 + 0.4)
    z = lerp(3.5, WL + 0.05, fall) + 0.05 * math.sin(t * 3) * fall
    c = P(x, y, z)
    s = CAM.scale_at(y)
    R, r = 0.55 * s, 0.17 * s
    for k in range(8):
        a0 = k * math.pi / 4
        ctx.save()
        ctx.translate(*c)
        ctx.scale(1, 0.42)
        ctx.arc(0, 0, R + r, a0, a0 + math.pi / 4)
        ctx.arc_negative(0, 0, R - r, a0 + math.pi / 4, a0)
        ctx.close_path()
        ctx.restore()
        set_src(ctx, hexc("#e8403a") if k % 2 else hexc("#ffffff"))
        ctx.fill()
    ctx.save()
    ctx.translate(*c)
    ctx.scale(1, 0.42)
    ctx.arc(0, 0, R + r, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.25)
    ctx.set_line_width(2)
    ctx.stroke()


def draw_chunks(ctx, t):
    if not (E["next_day"] < t < E["fix"]):
        return
    for i, (x, r, delay, rr) in enumerate(CHUNKS):
        t0 = E["collapse"] + delay
        u = smooth(t, t0, t0 + 0.55)
        z = lerp(-0.1, floor_out(x) + r * 0.6, u)
        xx = lerp(x, x * 0.85, u)
        sx, sy = P(xx, 0.02, z)
        s = CAM.scale_at(0) * r
        ctx.save()
        ctx.translate(sx, sy)
        ctx.rotate(u * (rr - 0.5) * 4)
        rnd = random.Random(i)
        pts = [(math.cos(a) * s * rnd.uniform(0.7, 1.1), math.sin(a) * s * rnd.uniform(0.6, 1.0)) for a in [k * math.pi / 4 for k in range(8)]]
        path_poly(ctx, pts)
        ctx.set_source(rgrad(-s * 0.3, -s * 0.3, 2, s * 1.4, [(0, shade(C["dirt"], 1.2)), (1, shade(C["dirt"], 0.6))]))
        ctx.fill()
        ctx.restore()
    # slumped mud at the base
    u = smooth(t, E["collapse"] + 0.2, E["collapse_end"])
    if u > 0:
        for side in (-1, 1):
            x = side * (OX - 0.1)
            base = P(x, 0.01, floor_out(x))
            s = CAM.scale_at(0)
            ctx.move_to(base[0], base[1] - 1.1 * s * u)
            ctx.curve_to(base[0] - side * 0.6 * s * u, base[1] - 0.6 * s * u, base[0] - side * 1.2 * s * u, base[1], base[0] - side * 1.6 * s * u, base[1])
            ctx.line_to(base[0], base[1])
            ctx.close_path()
            set_src(ctx, shade(C["dirt"], 0.85))
            ctx.fill()


def rebar_progress(t):
    return [smooth(t, E["rebar"] + i * 0.16, E["rebar"] + i * 0.16 + 0.45) for i in range(4)]


def draw_rebar(ctx, t, dz=0.0):
    if t < E["rebar"] or t > E["shell_done"] + 0.2:
        return
    g = rebar_progress(t)
    X0, X1 = -OX + TH * 0.5, OX - TH * 0.5
    Y = PB + TH * 0.5
    ctx.set_line_width(4)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    def line(a, b, k):
        drop = (1 - g[k]) * 3.5
        if g[k] <= 0:
            return
        pa = P(a[0], a[1], a[2] + drop + dz)
        pb = P(b[0], b[1], b[2] + drop + dz)
        ctx.move_to(*pa)
        ctx.line_to(*pb)
        set_src(ctx, alpha(C["rebar"], min(1, g[k] * 3)))
        ctx.stroke()
    fz = lambda x: floor_out(x) + TH * 0.5  # noqa: E731
    xs = profile_x(X0, X1, 18)
    for x in xs:                                   # floor bars along y + back wall verticals
        line((x, 0, fz(x)), (x, Y, fz(x)), 0)
        line((x, Y, fz(x)), (x, Y, -0.05), 2)
    for k in range(9):                             # floor bars along x
        y = k * Y / 8
        for xa, xb in zip(xs, xs[1:]):
            line((xa, y, fz(xa)), (xb, Y if False else y, fz(xb)), 1)
    for k in range(6):                             # horizontal rings on walls
        z = -0.15 - k * 0.38
        xa = max(X0, -OX) if z > floor_out(X0) else None
        line((X0, Y, max(z, fz(X0))), (X1, Y, max(z, fz(X1))), 3)
        if z > fz(X0):
            line((X0, 0, z), (X0, Y, z), 3)
        if z > fz(X1):
            line((X1, 0, z), (X1, Y, z), 3)
    for y in [k * Y / 6 for k in range(7)]:        # side wall verticals
        line((X0, y, fz(X0)), (X0, y, -0.05), 2)
        line((X1, y, fz(X1)), (X1, y, -0.05), 2)


def draw_spray(ctx, t):
    if not (E["spray"] - 0.3 < t < E["holds"]):
        return
    u = lin(t, E["spray"], E["shell_done"])
    x = lerp(-OX, OX, u)
    zz = -0.4 - 0.9 * abs(math.sin(u * math.pi * 5))
    noz = P(x - 0.3, -0.6, 0.9)
    tgt = P(x, PB * 0.7, zz)
    # hose
    pipe(ctx, round_corners([P(x - 2.5, -1.8, 0.2), P(x - 1.2, -1.2, 0.6), noz], 30), 12, hexc("#2a2f36"))
    ctx.save()
    ctx.translate(*noz)
    ang = math.atan2(tgt[1] - noz[1], tgt[0] - noz[0])
    ctx.rotate(ang)
    rounded_rect(ctx, -10, -9, 70, 18, 6)
    ctx.set_source(lgrad(0, -9, 0, 9, [(0, hexc("#c9ced3")), (0.4, hexc("#ffffff")), (1, hexc("#7d848b"))]))
    ctx.fill()
    ctx.restore()
    if u < 1:
        rnd = random.Random(int(t * 30))
        for i in range(40):
            k = rnd.random()
            sp = rnd.uniform(-0.25, 0.25)
            px = lerp(noz[0], tgt[0], k) + sp * 120 * k
            py = lerp(noz[1], tgt[1], k) + rnd.uniform(-1, 1) * 40 * k
            ctx.arc(px, py, rnd.uniform(2.5, 6), 0, 2 * math.pi)
            ctx.set_source_rgba(0.78, 0.77, 0.73, 0.9)
            ctx.fill()


def gw_level(t):
    return keyed(t, [(0, -14.0), (E["ground_water"], -14.0), (E["push_up"], DEEP - TH - 0.1), (E["lift"], DEEP - TH - 0.1),
                     (E["lift"] + 1.4, -1.0), (E["solution"] - 0.01, -1.0), (E["solution"], -14.0),
                     (E["pressure"], -6.0), (E["valve_open"], DEEP - TH - 0.1), (E["week"] - 0.42, DEEP - TH - 0.1),
                     (E["week"] - 0.4, -14.0)])


def pool_lift(t):
    """(dz, tilt) of the whole shell."""
    if E["lift"] <= t < E["solution"]:
        dz = 1.9 * smooth(t, E["lift"], E["lift"] + 1.4)
        tilt = 0.02 * smooth(t, E["lift"], E["lift"] + 1.4)
        if t > E["boat"]:
            dz += 0.12 * math.sin((t - E["boat"]) * 7)
            tilt += 0.035 * math.sin((t - E["boat"]) * 5.5)
        return dz, tilt
    if E["no_lift"] - 0.1 < t < E["no_lift"] + 0.8:
        k = (t - E["no_lift"] + 0.1) / 0.9
        return 0.08 * math.sin(k * math.pi * 3) * (1 - k), 0.0
    return 0.0, 0.0


def draw_up_arrows(ctx, t):
    show = (E["push_up"] < t < E["lift"] + 1.3) or (E["pressure"] < t < E["no_lift"] + 0.6)
    if not show:
        return
    a = min(smooth(t, E["push_up"], E["push_up"] + 0.3) if t < E["solution"] else smooth(t, E["pressure"], E["pressure"] + 0.3), 1.0)
    for i, x in enumerate((-2.6, -0.9, 0.9, 2.6)):
        if t > E["solution"]:
            x = VALVE_X + (x * 0.35)
        bob = 18 * math.sin(t * 6 + i)
        base = P(x, 0, DEEP - TH - 1.6)
        arrow(ctx, base[0], base[1] - bob, 120, 44, -math.pi / 2, alpha(C["white"], 0.92 * a))


def draw_valve(ctx, t, dz):
    if t < E["valve_in"] - 0.02:
        return
    drop = (1 - smooth(t, E["valve_in"], E["valve_in"] + 0.55)) * 2.5
    x = VALVE_X
    zf = floor_in(x) + dz + drop
    s = CAM.scale_at(0)
    # gravel bed under the slab
    rnd = random.Random(8)
    gb = P(x, 0, floor_out(x) + dz - 0.25)
    for i in range(16):
        sphere(ctx, gb[0] + rnd.uniform(-0.55, 0.55) * s, gb[1] + rnd.uniform(-0.15, 0.25) * s, rnd.uniform(0.09, 0.15) * s, C["gravel"])
    # pipe through the slab
    top = P(x, 0, zf)
    bot = P(x, 0, floor_out(x) + dz - 0.25)
    ctx.rectangle(top[0] - 0.09 * s, top[1], 0.18 * s, bot[1] - top[1])
    ctx.set_source(lgrad(top[0] - 0.09 * s, 0, top[0] + 0.09 * s, 0, [(0, hexc("#cdd3d8")), (0.4, hexc("#ffffff")), (1, hexc("#9aa1a8"))]))
    ctx.fill()
    # red cap (flap) that swings open
    op = smooth(t, E["valve_open"] - 0.05, E["valve_open"] + 0.35) * (1 - smooth(t, E["no_lift"] + 1.5, E["no_lift"] + 2.0))
    ctx.save()
    ctx.translate(top[0] - 0.22 * s, top[1])
    ctx.rotate(-op * 1.1)
    rounded_rect(ctx, 0, -0.14 * s, 0.44 * s, 0.14 * s, 4)
    ctx.set_source(lgrad(0, -0.14 * s, 0, 0, [(0, hexc("#ff6b5a")), (1, hexc("#c43a2c"))]))
    ctx.fill()
    ctx.restore()
    if op > 0.3 and t < E["no_lift"] + 1.4:
        rnd = random.Random(int(t * 20))
        for i in range(14):
            k = rnd.random()
            ctx.arc(top[0] + rnd.uniform(-0.12, 0.12) * s, top[1] - k * 1.4 * s, rnd.uniform(3, 7), 0, 2 * math.pi)
            ctx.set_source_rgba(0.75, 0.92, 1, 0.9 * (1 - k))
            ctx.fill()
    if E["valve_name"] - 0.1 < t < E["week"] - 0.4:
        pulse = 0.5 + 0.5 * math.sin((t - E["valve_name"]) * 8)
        ellipse(ctx, top[0], top[1], (0.45 + 0.1 * pulse) * s, (0.25 + 0.05 * pulse) * s)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9)
        ctx.set_line_width(5)
        ctx.stroke()


def draw_skimmer(ctx, t, dz):
    if t < E["skimmer"]:
        return
    s = CAM.scale_at(0)
    k = pop(t, E["skimmer"], 0.4)
    x0 = IX
    top = P(x0, 0, WL + 0.15 + dz)
    w, h = (TH + 0.35) * s * k, 0.55 * s * k
    # pipe going down to the suction line
    pipe(ctx, [(top[0] + 0.35 * s, top[1] + h * 0.7), P(OX + 0.35, 0, -3.2), P(OX + 0.35, 0, -3.6), P(5.0, 0, -3.6)], 0.22 * s, C["pvc"])
    rounded_rect(ctx, top[0] - 0.05 * s, top[1], w, h, 6)
    ctx.set_source(lgrad(0, top[1], 0, top[1] + h, [(0, hexc("#ffffff")), (1, hexc("#cfd6dc"))]))
    ctx.fill()
    rounded_rect(ctx, top[0] - 0.02 * s, top[1] + h * 0.18, w * 0.45, h * 0.5, 4)
    set_src(ctx, hexc("#26323c"))
    ctx.fill()
    if E["skimmer_name"] - 0.1 < t < E["drain_hole"]:
        pulse = 0.5 + 0.5 * math.sin((t - E["skimmer_name"]) * 9)
        rounded_rect(ctx, top[0] - 0.15 * s, top[1] - 0.1 * s, w + 0.2 * s, h + 0.2 * s, 10)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.6 + 0.4 * pulse)
        ctx.set_line_width(5)
        ctx.stroke()


def draw_drain(ctx, t, dz):
    if t < E["drain_hole"]:
        return
    s = CAM.scale_at(0)
    k = pop(t, E["drain_hole"], 0.4)
    x = DRAIN_X
    c = P(x, 0.9, floor_in(x) + dz + 0.01)
    ellipse(ctx, c[0], c[1], 0.38 * s * k, 0.11 * s * k)
    set_src(ctx, hexc("#f2f4f6"))
    ctx.fill()
    for i in range(5):
        ctx.rectangle(c[0] - (0.25 - abs(i - 2) * 0.05) * s * k, c[1] - 0.07 * s * k + i * 0.03 * s * k, (0.5 - abs(i - 2) * 0.1) * s * k, 0.012 * s * k)
        set_src(ctx, hexc("#2a3540"))
        ctx.fill()
    sec = P(x, 0, floor_in(x) + dz)
    pipe(ctx, [sec, P(x, 0, floor_out(x) - 1.0), P(x + 0.6, 0, -3.6), P(5.0, 0, -3.6)], 0.2 * s, C["pvc"])
    if E["drain_hole"] + 0.1 < t < E["jets"]:
        pulse = 0.5 + 0.5 * math.sin((t - E["drain_hole"]) * 9)
        ellipse(ctx, c[0], c[1], (0.55 + 0.08 * pulse) * s, (0.17 + 0.03 * pulse) * s)
        ctx.set_source_rgba(1, 0.85, 0.3, 0.9)
        ctx.set_line_width(5)
        ctx.stroke()


def draw_leaves(ctx, t):
    if not (E["leaves"] - 1.2 < t < E["bacteria"]):
        return
    for i, (x, y, rot, r) in enumerate(LEAVES):
        t_land = E["leaves"] - 0.3 + i * 0.07
        fall = smooth(t, t_land - 1.0, t_land)
        if t < t_land - 1.0:
            continue
        z = lerp(3.5, WL + 0.02, fall)
        xx = x + 0.4 * math.sin(t * 2 + i) * (1 - fall)
        yy = y
        if t > E["skimmer_suck"] + i * 0.08 and t < E["jets"]:
            u = smooth(t, E["skimmer_suck"] + i * 0.08, E["skimmer_suck"] + i * 0.08 + 0.9)
            xx = lerp(xx, IX - 0.1, u)
            yy = lerp(yy, 0.2, u)
            if u >= 0.98:
                continue
        if t >= E["jets"]:
            # circulate with the swirl, then drift into the skimmer
            ang = rot + max(0, t - E["swirl"]) * 1.2
            cx, cy = 0.0, PB / 2
            xx = cx + math.cos(ang) * 2.6 * (0.5 + r * 0.5)
            yy = cy + math.sin(ang) * 1.3 * (0.5 + r * 0.5)
            u = smooth(t, E["push_skimmer"] + i * 0.1, E["push_skimmer"] + i * 0.1 + 1.0)
            xx = lerp(xx, IX - 0.1, u)
            yy = lerp(yy, 0.2, u)
            if u >= 0.98:
                continue
        c = P(xx, yy, z)
        s = CAM.scale_at(yy)
        ctx.save()
        ctx.translate(*c)
        ctx.scale(1, 0.5 if fall >= 1 else 0.5 + 0.5 * abs(math.sin(t * 5 + i)))
        ctx.rotate(rot + t * 0.3)
        ctx.move_to(-0.18 * s, 0)
        ctx.curve_to(-0.05 * s, -0.11 * s, 0.1 * s, -0.09 * s, 0.18 * s, 0)
        ctx.curve_to(0.1 * s, 0.09 * s, -0.05 * s, 0.11 * s, -0.18 * s, 0)
        set_src(ctx, C["leaf"] if i % 3 else C["leaf2"])
        ctx.fill()
        ctx.restore()


def draw_pebbles(ctx, t, dz):
    if not (E["sink"] - 0.6 < t < E["jets"]):
        return
    s = CAM.scale_at(0)
    for i, (x, dly) in enumerate(PEBBLES):
        t0 = E["sink"] + 0.2 + i * 0.12
        if t < t0 - 0.5:
            continue
        z = keyed(t, [(t0 - 0.5, 2.0), (t0, WL), (t0 + 1.2, floor_in(x) + 0.08)])
        xx = x
        u = smooth(t, E["drain_suck"] + i * 0.1, E["drain_suck"] + 0.9 + i * 0.1)
        xx = lerp(x, DRAIN_X, u)
        z = lerp(z, floor_in(DRAIN_X) + 0.08, u) if u > 0 else z
        if u > 0.97:
            continue
        c = P(xx, 0.05, z + dz)
        sphere(ctx, c[0], c[1], 0.09 * s, C["pebble"])


def draw_swirl(ctx, t):
    if not (E["swirl"] - 0.1 < t < E["bacteria"] - 0.2):
        return
    a = smooth(t, E["swirl"] - 0.1, E["swirl"] + 0.4)
    n = 22
    for i in range(n):
        ang = i / n * 2 * math.pi + (t - E["swirl"]) * 1.4
        x = math.cos(ang) * 2.5
        y = PB / 2 + math.sin(ang) * 1.15
        p = P(x, y, WL + 0.02)
        q = P(x - math.sin(ang) * 0.1, y + math.cos(ang) * 0.1, WL + 0.02)
        chevron(ctx, p[0], p[1], 22, math.atan2(q[1] - p[1], q[0] - p[0]), alpha(C["white"], 0.9 * a))


def draw_jets(ctx, t, dz):
    if t < E["jets"]:
        return
    s = CAM.scale_at(0)
    for i, (y, z) in enumerate(((1.0, -0.6), (2.4, -0.6))):
        k = pop(t, E["jets"] + i * 0.15, 0.3)
        c = P(-IX + 0.02, y, z + dz)
        sphere(ctx, c[0], c[1], 0.09 * s * k, hexc("#e9edf0"))
        if t < E["bacteria"] - 0.2 and k > 0.5:
            for j in range(10):
                u = ((t * 1.6 + j / 10) % 1.0)
                p = P(-IX + 0.1 + u * 2.4, y - u * 0.6, z + dz)
                ctx.arc(p[0], p[1], 5 * (1 - u) + 1, 0, 2 * math.pi)
                ctx.set_source_rgba(0.85, 0.97, 1, 0.8 * (1 - u))
                ctx.fill()


def draw_algae_and_puffs(ctx, t):
    g = water_color(t)[3]
    if g <= 0.05:
        return
    rnd = random.Random(3)
    for i in range(22):
        x = rnd.uniform(-IX + 0.3, IX - 0.3)
        z = rnd.uniform(DEEP + 0.2, WL - 0.2)
        if z < floor_in(x) + 0.1:
            continue
        c = P(x, 0.02, z + 0.06 * math.sin(t * 2 + i))
        ctx.arc(c[0], c[1], rnd.uniform(5, 12) * g, 0, 2 * math.pi)
        ctx.set_source_rgba(0.45, 0.62, 0.15, 0.55 * g)
        ctx.fill()


def draw_smell(ctx, t):
    if not (E["smell"] - 0.2 < t < E["not_chlorine"] + 0.3):
        return
    a = smooth(t, E["smell"] - 0.2, E["smell"] + 0.3) * (1 - smooth(t, E["not_chlorine"] - 0.1, E["not_chlorine"] + 0.3))
    for i, x in enumerate((-2.6, -1.4, -0.2, 1.0, 2.2)):
        base = P(x, 1.5, WL)
        pts = []
        for k in range(30):
            u = k / 29
            yy = base[1] - u * 360 - ((t * 120 + i * 40) % 60)
            xx = base[0] + 18 * math.sin(u * 10 + t * 6 + i)
            pts.append((xx, yy))
        path_poly(ctx, pts, close=False)
        ctx.set_source_rgba(0.95, 0.85, 0.25, 0.9 * a)
        ctx.set_line_width(6)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()


def draw_pipes_section(ctx, t):
    """Return line running in the soil face from the equipment back to the jets."""
    if t < E["pump"]:
        return
    s = CAM.scale_at(0)
    g = smooth(t, E["pump"] + 0.3, E["pump"] + 1.2)
    pts = [P(5.2, 0, -0.6), P(OX + 0.6, 0, -0.6), P(OX + 0.6, 0, -4.0), P(-OX - 0.6, 0, -4.0), P(-OX - 0.6, 0, -0.6), P(-IX + 0.02, 0, -0.6)]
    pts = round_corners(pts, 30)
    n = max(2, int(len(pts) * g))
    pipe(ctx, pts[:n], 0.2 * s, C["pvc"])
    if t > E["clean"] - 0.3:
        for i in range(16):
            u = (t * 0.12 + i / 16) % 1.0
            p = polyline_point(pts, u)
            ctx.arc(p[0], p[1], 6, 0, 2 * math.pi)
            ctx.set_source_rgba(0.55, 0.85, 1, 0.9)
            ctx.fill()


def draw_equipment(ctx, t):
    if t < E["pump"] - 0.3:
        return
    s = CAM.scale_at(2.0)
    kp = pop(t, E["pump"], 0.4)
    kf = pop(t, E["pump"] + 0.25, 0.45)
    # concrete pad
    fill_poly(ctx, poly3([(4.9, 0.6, 0.0), (9.3, 0.6, 0.0), (9.3, 3.4, 0.0), (4.9, 3.4, 0.0)]), shade(C["concrete"], 1.05))
    fill_poly(ctx, poly3([(4.9, 0.6, -0.15), (9.3, 0.6, -0.15), (9.3, 0.6, 0.0), (4.9, 0.6, 0.0)]), shade(C["concrete"], 0.8))
    # pump (horizontal motor + housing)
    pb = P(5.9, 1.6, 0.0)
    if kp > 0:
        ctx.save()
        ctx.translate(*pb)
        ctx.scale(kp, kp)
        cylinder_h(ctx, -0.9 * s, 0.1 * s, -0.42 * s, 0.32 * s, 0.1 * s, C["pump"])
        for k in range(6):
            ctx.rectangle(-0.85 * s + k * 0.15 * s, -0.74 * s, 0.05 * s, 0.64 * s)
            ctx.set_source_rgba(0, 0, 0, 0.18)
            ctx.fill()
        cylinder_v(ctx, 0.45 * s, -1.0 * s, -0.05 * s, 0.38 * s, 0.12 * s, hexc("#eef1f3"))
        ellipse(ctx, 0.45 * s, -1.0 * s, 0.3 * s, 0.09 * s)
        set_src(ctx, hexc("#7a8a96"))
        ctx.fill()
        ctx.restore()
    # sand filter tank with cut-away
    fb = P(8.0, 1.8, 0.0)
    if kf > 0:
        ctx.save()
        ctx.translate(*fb)
        ctx.scale(kf, kf)
        rx, top, bot = 0.75 * s, -2.3 * s, -0.05 * s
        cut = smooth(t, E["filter"], E["filter"] + 0.6) * (1 - smooth(t, E["leaves"] - 0.3, E["leaves"]))
        cylinder_v(ctx, 0, top, bot, rx, 0.22 * rx, C["tank"])
        ellipse(ctx, 0, top, rx, 0.22 * rx)
        ctx.set_source(rgrad(-rx * 0.3, top - rx * 0.3, 2, rx * 1.2, [(0, shade(C["tank"], 1.35)), (1, shade(C["tank"], 0.8))]))
        ctx.fill()
        ctx.save()
        ctx.translate(0, top)
        ctx.scale(1, 0.6)
        ctx.arc(0, 0, rx, math.pi, 0)
        ctx.restore()
        ctx.set_source(rgrad(-rx * 0.3, top - rx * 0.5, 2, rx * 1.2, [(0, shade(C["tank"], 1.35)), (1, shade(C["tank"], 0.85))]))
        ctx.fill()
        if cut > 0:
            # cut-away window into the tank
            ctx.save()
            ctx.rectangle(-rx * 0.82, top + 0.1 * s, 2 * rx * 0.82 * cut, bot - top - 0.2 * s)
            ctx.clip()
            h_tot = bot - top
            g = water_color(t)[3]
            ctx.rectangle(-rx, top, 2 * rx, h_tot * 0.35)
            set_src(ctx, mix(hexc("#7fd3ef"), C["algae"], g))
            ctx.fill()
            ctx.rectangle(-rx, top + h_tot * 0.35, 2 * rx, h_tot * 0.45)
            set_src(ctx, C["sand"])
            ctx.fill()
            rnd = random.Random(1)
            for i in range(140):
                ctx.arc(rnd.uniform(-rx, rx), top + h_tot * rnd.uniform(0.36, 0.8), rnd.uniform(1.5, 3.5), 0, 2 * math.pi)
                set_src(ctx, shade(C["sand"], rnd.uniform(0.75, 1.1)))
                ctx.fill()
            ctx.rectangle(-rx, top + h_tot * 0.8, 2 * rx, h_tot * 0.2)
            set_src(ctx, C["gravel"])
            ctx.fill()
            for i in range(30):
                sphere(ctx, rnd.uniform(-rx, rx), top + h_tot * rnd.uniform(0.82, 0.98), rnd.uniform(4, 8), C["gravel"])
            # trapped dirt on top of the sand
            trap = smooth(t, E["sand_trap"], E["sand_trap"] + 1.2)
            for i in range(int(40 * trap)):
                ctx.arc(rnd.uniform(-rx * 0.9, rx * 0.9), top + h_tot * rnd.uniform(0.33, 0.4), rnd.uniform(3, 6), 0, 2 * math.pi)
                set_src(ctx, hexc("#4a3a1f"))
                ctx.fill()
            # standpipe + down arrows
            ctx.rectangle(-0.05 * s, top - 0.1 * s, 0.1 * s, h_tot * 0.85)
            set_src(ctx, hexc("#f2f4f6"))
            ctx.fill()
            for k in (-1, 1):
                ya = top + h_tot * (0.05 + 0.25 * ((t * 0.8) % 1.0))
                arrow(ctx, k * rx * 0.5, ya, 0.45 * s, 0.22 * s, math.pi / 2, alpha(C["white"], 0.95))
            ctx.restore()
            ctx.rectangle(-rx * 0.82, top + 0.1 * s, 2 * rx * 0.82 * cut, bot - top - 0.2 * s)
            ctx.set_source_rgba(0.1, 0.25, 0.3, 0.5)
            ctx.set_line_width(3)
            ctx.stroke()
        # multiport valve on top
        cylinder_v(ctx, 0, top - 0.55 * s, top - 0.05 * s, 0.22 * s, 0.07 * s, hexc("#2b3036"))
        sphere(ctx, 0.25 * s, top - 0.5 * s, 0.09 * s, hexc("#d8dde2"))
        ctx.restore()
    # plumbing: pool -> pump -> filter -> back
    g = smooth(t, E["pump"] + 0.3, E["pump"] + 1.1)
    sx = CAM.scale_at(1.0)
    suction = [P(5.0, 0, -3.6), P(5.2, 0, -0.1), P(5.25, 1.4, 0.35), P(pb[0] / 1.0 and 5.55, 1.6, 0.42)]
    suction = round_corners([P(5.0, 0, -3.6), P(5.2, 0.0, 0.3), P(5.4, 1.5, 0.42)], 25)
    tofilter = round_corners([P(6.3, 1.6, 1.0), P(6.3, 1.6, 1.6), P(7.4, 1.8, 2.75), P(7.9, 1.8, 2.75)], 25)
    ret = round_corners([P(8.1, 1.8, 2.75), P(8.9, 1.8, 2.75), P(9.0, 1.4, 0.4), P(8.6, 0.0, -0.6), P(5.2, 0.0, -0.6)], 25)
    for path in (suction, tofilter, ret):
        n = max(2, int(len(path) * g))
        pipe(ctx, path[:n], 0.18 * sx, C["pvc"])
    if t > E["suck"]:
        dirty = water_color(t)[3]
        col = mix((0.6, 0.88, 1, 1), (0.55, 0.62, 0.25, 1), dirty)
        for path, sp in ((suction, 0.6), (tofilter, 0.7)):
            for i in range(8):
                u = (t * sp + i / 8) % 1.0
                p = polyline_point(path, u)
                ctx.arc(p[0], p[1], 6, 0, 2 * math.pi)
                set_src(ctx, col)
                ctx.fill()
        for i in range(10):
            u = (t * 0.5 + i / 10) % 1.0
            p = polyline_point(ret, u)
            ctx.arc(p[0], p[1], 6, 0, 2 * math.pi)
            ctx.set_source_rgba(0.6, 0.9, 1, 0.95)
            ctx.fill()


def draw_finish(ctx, t):
    if t < E["tiles"]:
        return
    s = CAM.scale_at(0)
    # coping stones drop onto the rim
    n = 18
    for i in range(n):
        k = smooth(t, E["tiles"] + i * 0.025, E["tiles"] + i * 0.025 + 0.25)
        if k <= 0:
            continue
        x0 = -OX - 0.25 + i * (2 * OX + 0.5) / n
        x1 = x0 + (2 * OX + 0.5) / n - 0.03
        z = 0.1 + (1 - k) * 1.2
        y0, y1 = PB - 0.05, PB + TH + 0.3
        fill_poly(ctx, poly3([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]), hexc("#f3efe6"))
        fill_poly(ctx, poly3([(x0, y0, z - 0.1), (x1, y0, z - 0.1), (x1, y0, z), (x0, y0, z)]), hexc("#d6d0c3"))
    for side in (-1, 1):
        for i in range(6):
            k = smooth(t, E["tiles"] + 0.2 + i * 0.04, E["tiles"] + 0.45 + i * 0.04)
            if k <= 0:
                continue
            xa, xb = (side * OX, side * (OX + 0.3)) if side > 0 else (side * (OX + 0.3), side * OX)
            xa, xb = (xa - 0.0, xb) if side > 0 else (xa, xb)
            if side < 0:
                xa, xb = -OX - 0.3, -IX
            else:
                xa, xb = IX, OX + 0.3
            y0 = i * (PB / 6)
            y1 = y0 + PB / 6 - 0.03
            z = 0.1 + (1 - k) * 1.2
            fill_poly(ctx, poly3([(xa, y0, z), (xb, y0, z), (xb, y1, z), (xa, y1, z)]), hexc("#f3efe6"))
        front = P(side * (OX + 0.3), 0, 0.1)
    # ladder (left back corner)
    if t > E["ladder"]:
        k = smooth(t, E["ladder"], E["ladder"] + 0.4)
        dz = (1 - k) * 2.5
        for rx in (-2.6, -2.0):
            rail = [P(rx, PB - 0.1, -1.1 + dz), P(rx, PB - 0.1, 0.1 + dz), P(rx, PB + 0.15, 0.75 + dz), P(rx, PB + 0.55, 0.75 + dz), P(rx, PB + 0.6, 0.1 + dz)]
            pipe(ctx, round_corners(rail, 18), 0.07 * s, hexc("#d9dee3"))
        for k2 in range(3):
            z = -0.25 - k2 * 0.3 + dz
            ctx.move_to(*P(-2.6, PB - 0.12, z))
            ctx.line_to(*P(-2.0, PB - 0.12, z))
            ctx.set_line_width(0.06 * s)
            set_src(ctx, hexc("#aab2ba"))
            ctx.stroke()
    # diving board on the left rim
    if t > E["board"]:
        k = smooth(t, E["board"], E["board"] + 0.35)
        dz = (1 - k) * 2.0
        wob = 0.25 * math.exp(-3 * max(0, t - E["board"] - 0.35)) * math.sin((t - E["board"]) * 18) if t > E["board"] + 0.35 else 0
        base = [(-OX - 1.2, 1.2), (-OX - 0.4, 2.0)]
        fill_poly(ctx, poly3([(-OX - 1.3, 1.25, 0.0 + dz), (-OX - 0.5, 1.25, 0.0 + dz), (-OX - 0.5, 1.25, 0.45 + dz), (-OX - 1.3, 1.25, 0.45 + dz)]), hexc("#2a64b8"))
        tipz = 0.5 + wob + dz
        fill_poly(ctx, poly3([(-OX - 1.3, 1.0, 0.5 + dz), (-OX + 1.7, 1.0, tipz), (-OX + 1.7, 1.5, tipz), (-OX - 1.3, 1.5, 0.5 + dz)]), hexc("#f5f7f9"))
        fill_poly(ctx, poly3([(-OX - 1.3, 1.0, 0.43 + dz), (-OX + 1.7, 1.0, tipz - 0.07), (-OX + 1.7, 1.0, tipz), (-OX - 1.3, 1.0, 0.5 + dz)]), hexc("#c9d1d8"))
    # loungers + umbrella (final)
    if t > E["final"]:
        for i, (x, y) in enumerate(((5.2, 2.0), (6.6, 2.4))):
            k = pop(t, E["final"] + 0.1 + i * 0.12, 0.4)
            if k <= 0:
                continue
            c = P(x, y, 0)
            sc = CAM.scale_at(y) * k
            ctx.save()
            ctx.translate(*c)
            fill_poly(ctx, [(-0.9 * sc, -0.3 * sc), (0.6 * sc, -0.3 * sc), (0.75 * sc, -0.42 * sc), (-0.75 * sc, -0.42 * sc)], hexc("#ffffff"))
            fill_poly(ctx, [(-0.85 * sc, -0.42 * sc), (-0.55 * sc, -0.42 * sc), (-0.85 * sc, -1.0 * sc), (-1.05 * sc, -0.95 * sc)], hexc("#f39a2c"))
            fill_poly(ctx, [(-0.55 * sc, -0.46 * sc), (0.72 * sc, -0.46 * sc), (0.72 * sc, -0.42 * sc), (-0.55 * sc, -0.42 * sc)], hexc("#f39a2c"))
            for lx in (-0.8, 0.55):
                ctx.rectangle(lx * sc, -0.3 * sc, 0.05 * sc, 0.3 * sc)
                set_src(ctx, hexc("#9aa2aa"))
                ctx.fill()
            ctx.restore()
        k = pop(t, E["final"] + 0.4, 0.45)
        if k > 0:
            c = P(7.8, 3.0, 0)
            sc = CAM.scale_at(3.0) * k
            ctx.rectangle(c[0] - 0.03 * sc, c[1] - 2.2 * sc, 0.06 * sc, 2.2 * sc)
            set_src(ctx, hexc("#e9e2d5"))
            ctx.fill()
            for j in range(8):
                a0 = math.pi + j * math.pi / 8
                ctx.move_to(c[0], c[1] - 2.6 * sc)
                ctx.line_to(c[0] + math.cos(a0) * 1.3 * sc, c[1] - 2.0 * sc + math.sin(a0) * 0.1 * sc)
                ctx.line_to(c[0] + math.cos(a0 + math.pi / 8) * 1.3 * sc, c[1] - 2.0 * sc + math.sin(a0 + math.pi / 8) * 0.1 * sc)
                ctx.close_path()
                set_src(ctx, hexc("#e8403a") if j % 2 else hexc("#ffffff"))
                ctx.fill()


# ------------------------------------------------------------------ macro sets
def draw_macro_sand(ctx, t):
    ctx.rectangle(0, 0, W, H)
    ctx.set_source(rgrad(W / 2, H * 0.4, 50, 1300, [(0, hexc("#2c7d8c")), (1, hexc("#0c2f3a"))]))
    ctx.fill()
    rnd = random.Random(21)
    grains = []
    for row in range(5):
        for col in range(6):
            x = 60 + col * 200 + (row % 2) * 100 + rnd.uniform(-30, 30)
            y = 1020 + row * 165 + rnd.uniform(-25, 25)
            grains.append((x, y, rnd.uniform(85, 115), rnd.uniform(-0.5, 0.5)))
    # bacteria: wriggle down through the gaps
    gaps = [(160, 0), (360, 1), (560, 2), (760, 3), (960, 4), (260, 5), (660, 6)]
    for gx, i in gaps:
        t0 = E["bacteria"] - 0.2 + i * 0.13
        u = lin(t, t0, E["chlorine"] + 0.8)
        y = lerp(560, 1700, u)
        x = gx + 40 * math.sin(u * 14 + i)
        kill = smooth(t, E["kill"] + i * 0.07, E["kill"] + i * 0.07 + 0.35)
        if kill >= 1:
            continue
        sc = 1 + 0.4 * math.sin(clamp((t - E["kill"] - i * 0.07) / 0.35) * math.pi) if kill > 0 else 1
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(math.pi / 2 + 0.4 * math.sin(u * 14 + i + 1))
        ctx.scale(sc * (1 - kill * 0.9), sc * (1 - kill * 0.9))
        for f in range(3):
            ctx.move_to(-48, 0)
            for k in range(10):
                ctx.line_to(-48 - k * 7, 8 * math.sin(k * 1.2 + t * 18 + f))
            ctx.set_source_rgba(0.5, 0.85, 0.3, 0.8)
            ctx.set_line_width(2.5)
            ctx.stroke()
        rounded_rect(ctx, -50, -20, 100, 40, 20)
        ctx.set_source(lgrad(0, -20, 0, 20, [(0, shade(C["bact"], 1.35)), (0.5, C["bact"]), (1, shade(C["bact"], 0.6))]))
        ctx.fill()
        for d in range(3):
            ctx.arc(-20 + d * 20, -3 + (d % 2) * 6, 4, 0, 2 * math.pi)
            ctx.set_source_rgba(0.2, 0.45, 0.1, 0.7)
            ctx.fill()
        ctx.restore()
        if kill > 0:
            ctx.arc(x, y, 30 + 90 * kill, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 0.7, 0.8 * (1 - kill))
            ctx.set_line_width(6)
            ctx.stroke()
    for x, y, r, rot in grains:
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rot)
        ctx.scale(1.0, 0.82)
        sphere(ctx, 0, 0, r, C["sand"], outline=alpha(shade(C["sand"], 0.6), 0.6))
        ctx.restore()
    # dirt clumps caught on top of the sand
    for i in range(9):
        t0 = E["bacteria"] - 0.2 + i * 0.1
        u = smooth(t, t0, t0 + 0.8)
        x = 90 + i * 115
        y = lerp(500, 905 + (i % 2) * 15, u)
        sphere(ctx, x, y, 26 + (i % 3) * 6, hexc("#5a4022"))
    # chlorine rain
    if t > E["chlorine"]:
        rnd = random.Random(5)
        for i in range(60):
            ph = rnd.random()
            x = rnd.uniform(30, W - 30)
            u = ((t - E["chlorine"]) * 0.9 + ph) % 1.0
            if t - E["chlorine"] < ph / 0.9:
                continue
            y = lerp(380, 1500, u)
            ctx.arc(x, y, 9, 0, 2 * math.pi)
            ctx.set_source(rgrad(x, y, 1, 22, [(0, (1, 1, 0.8, 1)), (0.4, alpha(C["chlor"], 0.9)), (1, alpha(C["chlor"], 0))]))
            ctx.arc(x, y, 22, 0, 2 * math.pi)
            ctx.fill()
    # magnifier vignette
    ctx.rectangle(0, 0, W, H)
    ctx.set_source(rgrad(W / 2, H * 0.55, 400, 1150, [(0, (0, 0, 0, 0)), (1, (0, 0, 0, 0.55))]))
    ctx.fill()


def molecule(ctx, x, y, atoms, bonds, s=1.0):
    for a, b in bonds:
        xa, ya = x + atoms[a][0] * s, y + atoms[a][1] * s
        xb, yb = x + atoms[b][0] * s, y + atoms[b][1] * s
        ctx.move_to(xa, ya)
        ctx.line_to(xb, yb)
        ctx.set_line_width(14 * s)
        set_src(ctx, hexc("#c9cfd6"))
        ctx.stroke()
    for ax, ay, r, col in sorted(atoms, key=lambda a: a[2]):
        sphere(ctx, x + ax * s, y + ay * s, r * s, col)


def draw_molecules(ctx, t):
    ctx.rectangle(0, 0, W, H)
    ctx.set_source(rgrad(W / 2, H * 0.45, 50, 1300, [(0, hexc("#2c3f6e")), (1, hexc("#0f1830"))]))
    ctx.fill()
    green, blue, white, black, red = hexc("#4cc94c"), hexc("#3a62e0"), hexc("#f2f2f2"), hexc("#3a3d44"), hexc("#e8483a")
    react = smooth(t, E["reaction"] - 0.1, E["reaction"] + 0.7)
    form = smooth(t, E["sweat"] + 0.1, E["sweat"] + 0.5)
    # chlorine molecule
    k = pop(t, E["not_chlorine"] - 0.05, 0.4)
    if form < 1 and k > 0:
        x = lerp(330, 430, react)
        y = 860 + 15 * math.sin(t * 2)
        molecule(ctx, x, y, [(-55, 0, 62, green), (55, 0, 62, green)], [(0, 1)], s=1.8 * k * (1 - form))
    # red X ("not the chlorine itself")
    kx = pop(t, E["not_chlorine"] + 0.6, 0.3) * (1 - smooth(t, E["reaction"] + 0.1, E["reaction"] + 0.4))
    if kx > 0:
        ctx.save()
        ctx.translate(380, 860)
        ctx.scale(1.4 * kx, 1.4 * kx)
        ctx.rotate(0.12 * math.sin(t * 10))
        for a in (math.pi / 4, -math.pi / 4):
            ctx.save()
            ctx.rotate(a)
            rounded_rect(ctx, -150, -18, 300, 36, 18)
            set_src(ctx, red)
            ctx.fill()
            ctx.restore()
        ctx.restore()
    # urea (sweat) molecule drifting in
    if t > E["reaction"] - 0.7 and form < 1:
        x = lerp(1400, 720, smooth(t, E["reaction"] - 0.7, E["reaction"] + 0.3))
        y = 900
        molecule(ctx, x, y, [(0, 0, 40, black), (0, -70, 40, red), (-70, 40, 40, blue), (70, 40, 40, blue),
                             (-105, 95, 24, white), (-120, 10, 24, white), (105, 95, 24, white), (120, 10, 24, white)],
                 [(0, 1), (0, 2), (0, 3), (2, 4), (2, 5), (3, 6), (3, 7)], s=1.6 * (1 - form))
    # flash + chloramine floating up
    if E["sweat"] - 0.05 < t < E["sweat"] + 0.6:
        f = lin(t, E["sweat"] - 0.05, E["sweat"] + 0.6)
        ctx.arc(560, 880, 60 + 400 * f, 0, 2 * math.pi)
        ctx.set_source(rgrad(560, 880, 10, 60 + 400 * f, [(0, (1, 1, 0.85, 0.9 * (1 - f))), (1, (1, 1, 0.8, 0))]))
        ctx.fill()
    if form > 0:
        y = lerp(880, 620, smooth(t, E["sweat"] + 0.4, E["finish"]))
        molecule(ctx, 560, y + 10 * math.sin(t * 2), [(0, 0, 48, blue), (-95, -10, 62, green), (45, 60, 26, white), (55, -55, 26, white)],
                 [(0, 1), (0, 2), (0, 3)], s=1.9 * form)
        for i in range(6):
            u = ((t - E["sweat"]) * 0.5 + i / 6) % 1.0
            xx = 560 + 120 * math.sin(i * 2 + u * 4)
            ctx.arc(xx, y - 120 - u * 500, 30 + 60 * u, 0, 2 * math.pi)
            ctx.set_source_rgba(0.85, 0.9, 0.5, 0.25 * (1 - u) * form)
            ctx.fill()


# ------------------------------------------------------------------ the main diorama
def draw_main(ctx, t):
    night = draw_sun(ctx, t) if False else 0.0
    draw_sky(ctx, t)
    night = draw_sun(ctx, t)
    draw_trees_far(ctx)
    draw_house(ctx, t)
    draw_lawn(ctx, t)
    draw_shovel_and_pile(ctx, t) if t < E["dig_end"] else None
    d = pit_depth_factor(t)
    dz, tilt = pool_lift(t)
    shell_reveal = smooth(t, E["spray"], E["shell_done"])
    shell = shell_reveal > 0
    # pit (bare dirt hole) interior
    if d > 0:
        prof = [(x, z * d) for x, z in outer_profile(1.0)]
        draw_box_interior(ctx, (-OX, OX), PB + TH, prof,
                          {"back": shade(C["dirt"], 0.85), "floor": shade(C["dirt"], 0.95),
                           "side_l": shade(C["dirt"], 1.05), "side_r": shade(C["dirt"], 0.75)})
    else:
        fill_poly(ctx, poly3([(-OX, 0, 0.01), (OX, 0, 0.01), (OX, PB + TH, 0.01), (-OX, PB + TH, 0.01)]), shade(C["dirt"], 1.05))
    draw_rebar(ctx, t, dz) if not shell or shell_reveal < 1 else None
    # dirt-pit water (before the shell)
    wl = water_level(t)
    if wl and wl[0] == "pit":
        draw_water(ctx, t, (-OX, OX), PB + TH, lambda x: floor_out(x) * d, wl[1])
    # soil cut face with the pit hole + groundwater
    hole = [(-OX, 0)] + [(x, z * d) for x, z in outer_profile(1.0)] + [(OX, 0)] if d > 0 else None
    gwl = gw_level(t)
    draw_soil_face(ctx, t, hole, gwl)
    # wet patch under the leaking pit
    seep = smooth(t, E["seep"], E["collapse_end"]) * (1 - smooth(t, E["fix"] - 0.05, E["fix"]))
    if seep > 0:
        c = P(0, 0, -3.0)
        ctx.save()
        ctx.translate(*c)
        ctx.scale(1.0, 0.7)
        ctx.arc(0, 0, 520, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source(rgrad(c[0], c[1], 40, 520, [(0, (0.15, 0.1, 0.05, 0.45 * seep)), (1, (0.15, 0.1, 0.05, 0))]))
        ctx.fill()
        draw_drops(ctx, t, E["seep"], E["collapse_end"], 22, (P(-OX, 0, 0)[0], P(0, 0, -2.4)[1], P(OX, 0, 0)[0], P(0, 0, -6.5)[1]),
                   1.0, hexc("#7fd0ff"), 4, size=8)
        for side in (-1, 1):
            x0 = P(side * (OX + 0.1), 0, 0)[0]
            draw_drops(ctx, t, E["seep"] + 0.3, E["collapse_end"], 8, (x0 + side * 10, P(0, 0, -0.6)[1], x0 + side * 160, P(0, 0, -4)[1]),
                       1.0, hexc("#7fd0ff"), 9 + side, size=7)
    draw_chunks(ctx, t)
    # the concrete pool (moves as one body when it floats up)
    if shell:
        ctx.save()
        if tilt:
            cx, cy = P(0, 0, -1)
            ctx.translate(cx, cy)
            ctx.rotate(-tilt * 1.2)
            ctx.translate(-cx, -cy)
        prof = inner_profile()
        algae = water_color(t)[3]
        conc = mix(C["concrete"], hexc("#8aa64a"), algae * 0.8)
        tiles = smooth(t, E["tiles"], E["tiles"] + 0.75)
        ctx.save()
        xr = P(lerp(-OX - 0.1, OX + 0.1, shell_reveal), 0, 0)[0] + 80
        ctx.rectangle(-200, -400, xr + 200, H + 800)
        ctx.clip()
        draw_box_interior(ctx, (-IX, IX), PB, [(x, z + dz) for x, z in prof] if False else prof,
                          {"back": shade(conc, 0.92), "floor": shade(conc, 1.02), "side_l": shade(conc, 1.08), "side_r": shade(conc, 0.82)},
                          dz=dz)
        polys = interior_polys((-IX, IX), PB, prof, dz)
        for pts in polys:
            ctx.save()
            clip_poly(ctx, pts)
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            paint_surface(ctx, tex("concrete"), min(xs), min(ys), max(xs) - min(xs) + 2, max(ys) - min(ys) + 2, alpha_=0.35 * (1 - tiles))
            ctx.restore()
        if tiles > 0:
            ctx.save()
            ctx.rectangle(-100, -400, lerp(-50, W + 50, tiles) + 100, H + 800)
            ctx.clip()
            for j, pts in enumerate(polys):
                f = (0.9, 1.0, 1.0, 1.05, 0.85)[min(j, 4)] if j < 2 else (1.08 if j == len(polys) - 2 else 0.85 if j == len(polys) - 1 else 1.0)
                fill_poly(ctx, pts, shade(C["tile"], f), seam=True)
            ctx.restore()
            tile_grid(ctx, (-IX, IX), PB, prof, tiles, dz)
        ctx.restore()
        draw_drain(ctx, t, dz)
        draw_jets(ctx, t, dz)
        if wl and wl[0] == "pool":
            draw_water(ctx, t, (-IX, IX), PB, floor_in, wl[1], dz=dz)
        draw_leaves(ctx, t)
        draw_swirl(ctx, t)
        draw_pebbles(ctx, t, dz)
        draw_algae_and_puffs(ctx, t)
        draw_shell_band(ctx, t, shell_reveal, dz, 0.0)
        draw_valve(ctx, t, dz)
        draw_skimmer(ctx, t, dz)
        ctx.restore()
        draw_rebar(ctx, t, dz) if shell_reveal < 1 else None
    draw_ring(ctx, t)
    draw_spray(ctx, t)
    draw_hose(ctx, t)
    draw_up_arrows(ctx, t)
    draw_pipes_section(ctx, t)
    draw_equipment(ctx, t)
    draw_finish(ctx, t)
    draw_smell(ctx, t)
    if t < E["dig_end"] + 0.8:
        draw_shovel_and_pile(ctx, t)
    if night > 0:
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0.05, 0.08, 0.2, night)
        ctx.fill()
    if t > E["final"] + 0.8:
        warm = smooth(t, E["final"] + 0.8, E["final"] + 2.5)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(1.0, 0.6, 0.2, 0.12 * warm)
        ctx.fill()
