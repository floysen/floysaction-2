"""Compose one finished frame: scene + camera move + transitions + caption."""
import json
import math
import os

import cairo

from draw import W, H, smooth, keyed, pop, lerp
import world
from world import E, P, SP, VALVE_X, DRAIN_X, IX, DEEP, WL

ROOT = world.ROOT

# ------------------------------------------------------------------ camera moves (2D zoom on the diorama)
# (time, zoom, focus point in base-screen pixels).  Focus is placed at the frame centre.
BASE = (W / 2, H / 2)


def _f(x, y, z):
    return P(x, y, z)


VIEW_KEYS = [
    (0.0, 1.06, (W / 2, 900)),
    (E["dig_end"], 1.0, BASE),
    (E["next_day"], 1.0, BASE),
    (E["seep"] + 0.6, 1.08, (W / 2, 1060)),
    (E["fix"], 1.0, BASE),
    (E["spray"], 1.12, (W / 2, 1000)),
    (E["holds"], 1.0, BASE),
    (E["solution"] + 0.2, 1.0, BASE),
    (E["valve_in"] + 0.3, 1.9, _f(VALVE_X - 0.6, 0, DEEP - 0.3)),
    (E["pressure"], 1.9, _f(VALVE_X - 0.6, 0, DEEP - 0.3)),
    (E["pressure"] + 0.6, 1.35, _f(VALVE_X - 1.5, 0, DEEP - 1.4)),
    (E["no_lift"] + 0.4, 1.2, _f(0.8, 0, -1.6)),
    (E["valve_name"], 2.4, _f(VALVE_X, 0, DEEP - 0.1)),
    (E["week"] - 0.6, 2.4, _f(VALVE_X, 0, DEEP - 0.1)),
    (E["week"] - 0.2, 1.0, BASE),
    (E["pump"] - 0.5, 1.0, BASE),
    (E["pump"] + 0.2, 1.45, _f(6.4, 1.6, 0.6)),
    (E["filter"] - 0.2, 1.45, _f(6.4, 1.6, 0.6)),
    (E["filter"] + 0.4, 2.1, _f(8.0, 1.8, 1.2)),
    (E["clean"] + 1.0, 2.1, _f(8.0, 1.8, 1.2)),
    (E["leaves"] - 0.4, 1.0, BASE),
    (E["skimmer"] - 0.2, 1.0, BASE),
    (E["skimmer"] + 0.4, 1.7, _f(IX - 0.3, 0.6, -0.6)),
    (E["drain_hole"] - 0.2, 1.7, _f(IX - 0.3, 0.6, -0.6)),
    (E["drain_hole"] + 0.4, 1.7, _f(DRAIN_X, 0.4, DEEP + 0.2)),
    (E["jets"] - 0.3, 1.7, _f(DRAIN_X, 0.4, DEEP + 0.2)),
    (E["jets"] + 0.3, 1.0, BASE),
    (E["bacteria"] - 0.55, 1.0, BASE),
    (E["bacteria"] - 0.2, 3.2, _f(0.5, 1.5, WL - 0.6)),
    (E["smell"] - 0.1, 1.15, (W / 2, 950)),
    (E["not_chlorine"], 1.0, BASE),
    (E["finish"], 1.0, BASE),
    (E["final"], 1.0, BASE),
    (SP.DURATION, 1.08, (W / 2, 1000)),
]

MACRO = (E["bacteria"] - 0.2, E["smell"] - 0.1)
MOLECULE = (E["not_chlorine"] - 0.1, E["finish"])
FADE = 0.25


def view_at(t):
    z = keyed(t, [(k[0], k[1]) for k in VIEW_KEYS])
    f = keyed(t, [(k[0], tuple(k[2])) for k in VIEW_KEYS])
    return z, f


# ------------------------------------------------------------------ captions (one word at a time, like the references)
_CAPS = None


def captions():
    global _CAPS
    if _CAPS is None:
        meta = json.load(open(os.path.join(ROOT, "data", "captions.json"), encoding="utf-8"))
        items = []
        for e in meta["entries"]:
            surf = cairo.ImageSurface.create_from_png(os.path.join(ROOT, e["file"]))
            items.append((e["start"], e["end"], surf))
        _CAPS = (meta, items)
    return _CAPS


def draw_caption(ctx, t):
    meta, items = captions()
    for st, en, surf in items:
        if st <= t < en:
            k = pop(t, st, 0.16)
            s = 0.55 + 0.45 * k
            cx, cy = W / 2, H * meta["center_y_ratio"]
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(s, s)
            ctx.set_source_surface(surf, -surf.get_width() / 2, -surf.get_height() / 2)
            ctx.paint_with_alpha(min(1.0, k * 1.6))
            ctx.restore()
            return


# ------------------------------------------------------------------ compose
def _scene(ctx, t, which):
    if which == "macro":
        world.draw_macro_sand(ctx, t)
    elif which == "molecule":
        world.draw_molecules(ctx, t)
    else:
        z, f = view_at(t)
        ctx.save()
        ctx.translate(W / 2, H / 2)
        ctx.scale(z, z)
        ctx.translate(-f[0], -f[1])
        world.draw_main(ctx, t)
        ctx.restore()


def scene_at(t):
    if MACRO[0] <= t < MACRO[1]:
        return "macro"
    if MOLECULE[0] <= t < MOLECULE[1]:
        return "molecule"
    return "main"


def render(t, scale=1.0):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(W * scale), int(H * scale))
    ctx = cairo.Context(surf)
    ctx.scale(scale, scale)
    ctx.set_antialias(cairo.ANTIALIAS_GOOD)
    cur = scene_at(t)
    _scene(ctx, t, cur)
    # cross-fade into each scene change
    for t0 in (MACRO[0], MACRO[1], MOLECULE[0], MOLECULE[1]):
        if t0 <= t < t0 + FADE:
            prev = scene_at(t0 - 0.001)
            if prev != cur:
                a = 1 - smooth(t, t0, t0 + FADE)
                ctx.push_group()
                _scene(ctx, t0 - 0.001, prev)
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(a)
    # white flash on the "congratulations" beats
    for tf in (E["congrats"], E["final"]):
        if tf <= t < tf + 0.25:
            ctx.rectangle(0, 0, W, H)
            ctx.set_source_rgba(1, 1, 1, 0.35 * (1 - (t - tf) / 0.25))
            ctx.fill()
    world.draw_confetti(ctx, t, E["congrats"], 1.6, 60, 1)
    world.draw_confetti(ctx, t, E["final"] + 0.1, 2.4, 90, 2)
    draw_caption(ctx, t)
    surf.flush()
    return surf
