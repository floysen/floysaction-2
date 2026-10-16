"""Compose one frame: pick the set, apply the camera move, cross-fade, captions."""
import json
import os

import cairo

from draw import W, H, smooth, keyed, pop, vignette
import world
from world import E, SP, PY, PH, TP

ROOT = world.ROOT
BASE = (W / 2, H / 2)


def _ph(x, z):
    return PH(x, 0, z)


ROOM = _ph(-0.1, 0.5)
TOILET = TP(0.55, 0.45)
TOILET_HI = TP(0.75, 0.75)
TRAP = TP(0.40, 0.24)
TANK = TP(0.45, 0.85)
PIPE = _ph(1.6, -1.0)
PIPE_UP = _ph(-0.9, -0.4)
SEWER = _ph(4.3, -1.3)
VENT = _ph(-0.6, 1.2)

SCENES = [
    ("yard", 0.0, E["house"]),
    ("house", E["house"], E["see"]),
    ("rooftop", E["see"], E["seat"] - 0.1),
    ("house", E["seat"] - 0.1, SP.DURATION + 1),
]
FADE = 0.3

VIEWS = {
    "yard": [(0.0, 1.0, BASE), (E["build"], 1.0, BASE), (E["problem"], 1.08, PY(0, 0.5, 0.9)),
             (E["fill"] - 0.2, 1.08, PY(0, 0.5, 0.9)), (E["fill"] + 0.6, 1.5, PY(0, 0, -0.6)), (E["house"] + 1, 1.5, PY(0, 0, -0.6))],
    "house": [(E["house"], 1.02, ROOM), (E["seat_in"] - 0.2, 1.05, ROOM), (E["seat_in"] + 0.5, 2.0, TOILET),
              (E["pipe"] - 0.2, 2.0, TOILET), (E["pipe"] + 0.6, 1.0, PIPE), (E["street"] - 0.1, 1.0, PIPE),
              (E["street"] + 0.6, 1.2, SEWER), (E["stuck"] + 0.3, 1.2, SEWER), (E["stuck"] + 1.0, 1.4, PIPE_UP),
              (E["bucket"] - 0.4, 1.4, PIPE_UP), (E["bucket"] + 0.2, 1.7, TOILET_HI), (E["push"], 1.7, TOILET_HI),
              (E["push"] + 0.7, 1.0, PIPE), (E["problem2"] + 0.3, 1.0, PIPE), (E["gas"] + 0.2, 1.15, SEWER),
              (E["gas"] + 1.5, 1.0, PIPE), (E["enter"] - 0.3, 1.6, TOILET_HI), (E["bend"] - 0.3, 1.6, TOILET_HI),
              (E["bend"] + 0.5, 2.6, TRAP), (E["air"] + 0.9, 2.6, TRAP), (E["lazy"] + 0.3, 1.5, TOILET_HI),
              (E["tank"] - 0.1, 1.5, TOILET_HI), (E["tank"] + 0.5, 2.4, TANK), (E["full"] + 0.4, 2.4, TANK),
              (E["rush2"] + 0.3, 2.3, TRAP), (E["gas_back"] + 0.4, 2.3, TRAP), (E["vent"] + 0.4, 0.78, VENT),
              (E["see"] + 1, 0.78, VENT),
              (E["seat"] - 0.1, 1.9, TOILET_HI), (E["final"] - 0.1, 1.9, TOILET_HI), (E["final"] + 0.8, 1.15, ROOM),
              (SP.DURATION + 1, 1.05, ROOM)],
    "rooftop": [(E["see"], 1.0, BASE), (E["seat"], 1.12, (W / 2, H * 0.47))],
}
DRAW = {"yard": world.draw_yard, "house": world.draw_house, "rooftop": world.draw_rooftop}


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a
    return SCENES[-1][0], SCENES[-1][1]


def _keys(name, t):
    ks = VIEWS[name]
    if name == "house" and t < E["see"]:
        ks = [k for k in ks if k[0] <= E["see"] + 1]
    elif name == "house":
        ks = [k for k in ks if k[0] >= E["seat"] - 0.1]
    z = keyed(t, [(k[0], k[1]) for k in ks])
    f = keyed(t, [(k[0], tuple(k[2])) for k in ks])
    return z, f


def _draw(ctx, t, name):
    z, f = _keys(name, t)
    ctx.save()
    ctx.translate(W / 2, H / 2)
    ctx.scale(z, z)
    ctx.translate(-f[0], -f[1])
    DRAW[name](ctx, t)
    ctx.restore()


_CAPS = None


def captions():
    global _CAPS
    if _CAPS is None:
        meta = json.load(open(os.path.join(ROOT, "data", "captions.json"), encoding="utf-8"))
        _CAPS = (meta, [(e["start"], e["end"], cairo.ImageSurface.create_from_png(os.path.join(ROOT, e["file"]))) for e in meta["entries"]])
    return _CAPS


def draw_caption(ctx, t):
    meta, items = captions()
    for st, en, surf in items:
        if st <= t < en:
            k = pop(t, st, 0.16)
            s = 0.55 + 0.45 * k
            ctx.save()
            ctx.translate(W / 2, H * meta["center_y_ratio"])
            ctx.scale(s, s)
            ctx.set_source_surface(surf, -surf.get_width() / 2, -surf.get_height() / 2)
            ctx.paint_with_alpha(min(1.0, k * 1.6))
            ctx.restore()
            return


def render(t, scale=1.0):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(W * scale), int(H * scale))
    ctx = cairo.Context(surf)
    ctx.scale(scale, scale)
    name, t0 = scene_at(t)
    _draw(ctx, t, name)
    if t0 > 0 and t < t0 + FADE:
        prev, _ = scene_at(t0 - 0.001)
        ctx.push_group()
        _draw(ctx, t0 - 0.001, prev)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(1 - smooth(t, t0, t0 + FADE))
    vignette(ctx, 0.28)
    for tf in (E["toilet0"], E["final"]):
        if tf <= t < tf + 0.25:
            ctx.rectangle(0, 0, W, H)
            ctx.set_source_rgba(1, 1, 1, 0.3 * (1 - (t - tf) / 0.25))
            ctx.fill()
    world.draw_confetti(ctx, t, E["final"] + 0.1, 2.6, 100, 2)
    draw_caption(ctx, t)
    surf.flush()
    return surf
