"""2.5D drawing toolkit (pycairo + numpy).

A fixed "cut-away diorama" camera like the reference videos: the ground is sliced
open along the plane y = 0, the soil cross-section faces the viewer flat, and
everything behind it (lawn, pool, house) recedes with a gentle perspective.
Objects are flat-shaded shapes with gradients so they read as 3D while the
whole picture keeps a clean 2D illustration style.
"""
import math

import cairo
import numpy as np

W, H = 1080, 1920


# ------------------------------------------------------------------ easing / timing
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def smooth(t, t0, t1):
    """0 before t0, 1 after t1, smoothstep in between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    u = clamp((t - t0) / (t1 - t0))
    return u * u * (3 - 2 * u)


def lin(t, t0, t1):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def back_out(u, s=1.7):
    u = clamp(u) - 1
    return u * u * ((s + 1) * u + s) + 1


def pop(t, t0, dur=0.35):
    """0 -> overshoot -> 1 scale for objects appearing."""
    if t < t0:
        return 0.0
    return back_out((t - t0) / dur)


def lerp(a, b, u):
    return a + (b - a) * u


def mix(c1, c2, u):
    return tuple(lerp(a, b, u) for a, b in zip(c1, c2))


def keyed(t, keys):
    """Piecewise smooth interpolation of numbers/tuples: keys = [(t, value), ...]."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = smooth(t, t0, t1)
            if isinstance(v0, tuple):
                return mix(v0, v1, u)
            return lerp(v0, v1, u)
    return keys[-1][1]


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def shade(c, f):
    """Darken (f<1) or lighten (f>1) a colour."""
    r, g, b = c[:3]
    if f <= 1:
        r, g, b = r * f, g * f, b * f
    else:
        k = f - 1
        r, g, b = r + (1 - r) * k, g + (1 - g) * k, b + (1 - b) * k
    return (r, g, b, c[3] if len(c) > 3 else 1.0)


def alpha(c, a):
    return (c[0], c[1], c[2], (c[3] if len(c) > 3 else 1.0) * a)


# ------------------------------------------------------------------ camera
class Cam:
    """Pinhole camera in front of the cut plane, slightly above ground, tilted down."""

    def __init__(self, dist=15.5, height=3.2, pitch_deg=9.0, focal=1450.0, horizon_y=880.0):
        self.C = np.array([0.0, -dist, height])
        a = math.radians(pitch_deg)
        self.f = np.array([0.0, math.cos(a), -math.sin(a)])
        self.u = np.array([0.0, math.sin(a), math.cos(a)])
        self.F = focal
        self.cy = horizon_y

    def p(self, x, y, z):
        d = np.array([x, y, z]) - self.C
        zc = d @ self.f
        return (W / 2 + self.F * d[0] / zc, self.cy - self.F * (d @ self.u) / zc)

    def scale_at(self, y):
        """Pixels per metre at depth y (for sizing round things)."""
        a = self.p(0, y, 0)
        b = self.p(1, y, 0)
        return b[0] - a[0]


# ------------------------------------------------------------------ primitives
def path_poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def fill_poly(ctx, pts, col, stroke=None, lw=2.0, seam=False):
    path_poly(ctx, pts)
    set_src(ctx, col)
    if seam:  # hide hairline gaps between adjacent faces
        ctx.fill_preserve()
        ctx.set_line_width(1.2)
        ctx.stroke()
        return
    if stroke:
        ctx.fill_preserve()
        set_src(ctx, stroke)
        ctx.set_line_width(lw)
        ctx.stroke()
    else:
        ctx.fill()


def set_src(ctx, col):
    if isinstance(col, cairo.Pattern):
        ctx.set_source(col)
    elif len(col) == 4:
        ctx.set_source_rgba(*col)
    else:
        ctx.set_source_rgb(*col)


def lgrad(x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c in stops:
        g.add_color_stop_rgba(o, *(c if len(c) == 4 else (*c, 1)))
    return g


def rgrad(cx, cy, r0, r1, stops, fx=None, fy=None):
    g = cairo.RadialGradient(cx if fx is None else fx, cy if fy is None else fy, r0, cx, cy, r1)
    for o, c in stops:
        g.add_color_stop_rgba(o, *(c if len(c) == 4 else (*c, 1)))
    return g


def rounded_rect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def sphere(ctx, cx, cy, r, col, light=(-0.35, -0.4), outline=None):
    if r <= 0.3:
        return
    g = rgrad(cx, cy, r * 0.05, r, [(0, shade(col, 1.45)), (0.55, col), (1, shade(col, 0.55))],
              fx=cx + light[0] * r, fy=cy + light[1] * r)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source(g)
    if outline:
        ctx.fill_preserve()
        set_src(ctx, outline)
        ctx.set_line_width(max(1.0, r * 0.06))
        ctx.stroke()
    else:
        ctx.fill()


def ellipse(ctx, cx, cy, rx, ry):
    if rx <= 0 or ry <= 0:
        return
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def cylinder_v(ctx, cx, top, bottom, rx, ry, col, cap=None):
    """Upright cylinder seen slightly from above (screen space)."""
    g = lgrad(cx - rx, 0, cx + rx, 0, [(0, shade(col, 0.6)), (0.35, shade(col, 1.25)), (0.6, col), (1, shade(col, 0.5))])
    ctx.move_to(cx - rx, top)
    ctx.line_to(cx - rx, bottom)
    ctx.save()
    ctx.translate(cx, bottom)
    ctx.scale(rx, ry)
    ctx.arc_negative(-1, 0, 1, math.pi, 0) if False else ctx.arc_negative(0, 0, 1, math.pi, 0)
    ctx.restore()
    ctx.line_to(cx + rx, top)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill()
    ellipse(ctx, cx, top, rx, ry)
    set_src(ctx, cap or shade(col, 1.15))
    ctx.fill()


def cylinder_h(ctx, x0, x1, cy, ry, rx_end, col):
    """Horizontal cylinder (pipe/motor) lying along screen x."""
    g = lgrad(0, cy - ry, 0, cy + ry, [(0, shade(col, 0.65)), (0.3, shade(col, 1.3)), (0.55, col), (1, shade(col, 0.45))])
    ctx.rectangle(x0, cy - ry, x1 - x0, 2 * ry)
    ctx.set_source(g)
    ctx.fill()
    ellipse(ctx, x1, cy, rx_end, ry)
    set_src(ctx, shade(col, 0.85))
    ctx.fill()


def pipe(ctx, pts, width, col, highlight=True, cap=cairo.LINE_CAP_ROUND):
    """Thick tube along a screen polyline with rounded joins and a specular stripe."""
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cap)
    path_poly(ctx, pts, close=False)
    set_src(ctx, shade(col, 0.62))
    ctx.set_line_width(width)
    ctx.stroke()
    path_poly(ctx, pts, close=False)
    set_src(ctx, col)
    ctx.set_line_width(width * 0.72)
    ctx.stroke()
    if highlight:
        ctx.save()
        ctx.translate(-width * 0.14, -width * 0.16)
        path_poly(ctx, pts, close=False)
        set_src(ctx, alpha(shade(col, 1.6), 0.8))
        ctx.set_line_width(width * 0.2)
        ctx.stroke()
        ctx.restore()


def polyline_point(pts, u):
    """Point at fraction u (0..1) along a polyline."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg) or 1
    d = clamp(u) * total
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if d <= s:
            k = d / s if s else 0
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        d -= s
    return pts[-1]


def round_corners(pts, r=20, steps=6):
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        da, dc = math.dist(a, b), math.dist(c, b)
        rr = min(r, da / 2, dc / 2)
        p1 = (b[0] + (a[0] - b[0]) * rr / da, b[1] + (a[1] - b[1]) * rr / da) if da else b
        p2 = (b[0] + (c[0] - b[0]) * rr / dc, b[1] + (c[1] - b[1]) * rr / dc) if dc else b
        for s in range(steps + 1):
            u = s / steps
            out.append(((1 - u) ** 2 * p1[0] + 2 * (1 - u) * u * b[0] + u * u * p2[0],
                        (1 - u) ** 2 * p1[1] + 2 * (1 - u) * u * b[1] + u * u * p2[1]))
    out.append(pts[-1])
    return out


def arrow(ctx, x, y, length, width, angle, col, outline=None):
    """Chunky arrow pointing along `angle` (radians, 0 = right, -pi/2 = up), tail at (x, y)."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    hw = width / 2
    hl = min(length * 0.45, width * 1.3)
    pts = [(0, -hw * 0.55), (length - hl, -hw * 0.55), (length - hl, -hw * 1.25), (length, 0),
           (length - hl, hw * 1.25), (length - hl, hw * 0.55), (0, hw * 0.55)]
    path_poly(ctx, pts)
    set_src(ctx, col)
    if outline:
        ctx.fill_preserve()
        set_src(ctx, outline)
        ctx.set_line_width(3)
        ctx.stroke()
    else:
        ctx.fill()
    ctx.restore()


def chevron(ctx, x, y, size, angle, col):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    ctx.move_to(-size * 0.5, -size * 0.6)
    ctx.line_to(size * 0.3, 0)
    ctx.line_to(-size * 0.5, size * 0.6)
    ctx.set_line_width(size * 0.32)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    set_src(ctx, col)
    ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ procedural textures
def _noise2(w, h, scale, rng):
    gw, gh = max(2, int(w / scale) + 2), max(2, int(h / scale) + 2)
    grid = rng.random((gh, gw)).astype(np.float32)
    ys = np.linspace(0, gh - 1.001, h)
    xs = np.linspace(0, gw - 1.001, w)
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    fy = (ys - y0)[:, None]
    fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = grid[y0][:, x0]
    b = grid[y0][:, x0 + 1]
    c = grid[y0 + 1][:, x0]
    d = grid[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(w, h, scale, octaves, seed, stretch=(1.0, 1.0)):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    s = scale
    for _ in range(octaves):
        sw, sh = max(4, int(w / stretch[0])), max(4, int(h / stretch[1]))
        n = _noise2(sw, sh, s, rng)
        if (sw, sh) != (w, h):
            yi = (np.arange(h) * sh / h).astype(int)
            xi = (np.arange(w) * sw / w).astype(int)
            n = n[yi][:, xi]
        out += n * amp
        tot += amp
        amp *= 0.5
        s /= 2
    return out / tot


def array_to_surface(rgba):
    """float RGBA (h, w, 4) in 0..1, straight alpha -> cairo ARGB32 surface (premultiplied BGRA)."""
    h, w, _ = rgba.shape
    a = rgba[..., 3:4]
    pm = np.concatenate([rgba[..., 2:3] * a, rgba[..., 1:2] * a, rgba[..., 0:1] * a, a], axis=2)
    buf = np.ascontiguousarray((np.clip(pm, 0, 1) * 255).astype(np.uint8))
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    if stride != w * 4:
        pad = np.zeros((h, stride), np.uint8)
        pad[:, : w * 4] = buf.reshape(h, w * 4)
        buf = pad
    surf = cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride)
    return surf


def soil_texture(w, h, seed=3, wet=0.0):
    """Eroded dirt cross-section like the references: warm red-brown, soft vertical
    erosion streaks, clods and fine grain, slightly darker with depth."""
    streak = fbm(w, h, 70, 4, seed, stretch=(1.0, 5.0))
    clods = fbm(w, h, 26, 4, seed + 1)
    fine = fbm(w, h, 6, 2, seed + 2)
    blot = fbm(w, h, 200, 3, seed + 3)
    base = np.array([0.66, 0.42, 0.24], np.float32)
    dark = np.array([0.46, 0.28, 0.14], np.float32)
    light = np.array([0.80, 0.58, 0.38], np.float32)
    k = np.clip(0.5 + (streak - 0.5) * 1.6 + (clods - 0.5) * 0.6, 0, 1)[..., None]
    col = dark * (1 - k) + base * k
    hl = np.clip((clods - 0.6) * 3.0, 0, 1)[..., None] * 0.55
    col = col * (1 - hl) + light * hl
    sh = np.clip((0.4 - clods) * 3.0, 0, 1)[..., None] * 0.35
    col = col * (1 - sh)
    cracks = np.clip((0.035 - np.abs(streak - 0.5)) * 18, 0, 1)[..., None]
    col = col * (1 - cracks * 0.4)
    col = col * (0.93 + 0.14 * fine[..., None])
    depth = np.linspace(1.0, 0.8, h, dtype=np.float32)[:, None, None]
    col = col * depth * (0.92 + 0.16 * blot[..., None])
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((h, w, 1), np.float32)], axis=2)
    return array_to_surface(rgba)


def lawn_texture(w, h, seed=5):
    n = fbm(w, h, 30, 4, seed)
    base = np.array([0.30, 0.55, 0.16], np.float32)
    col = base * (0.85 + 0.3 * n[..., None])
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((h, w, 1), np.float32)], axis=2)
    return array_to_surface(rgba)


def cloud_sprite(w, h, seed=0):
    n = fbm(w, h, 50, 4, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = (xx - w / 2) / (w / 2)
    dy = (yy - h * 0.6) / (h / 2)
    fall = np.clip(1 - (dx * dx + dy * dy * 2.2), 0, 1)
    a = np.clip((n * 1.3 - 0.35) * fall * 2.2, 0, 1) ** 1.2
    shade_ = 0.82 + 0.18 * np.clip(1 - (yy / h), 0, 1)
    col = np.stack([shade_, shade_, shade_ * 1.02], axis=2)
    rgba = np.concatenate([np.clip(col, 0, 1), a[..., None] * 0.95], axis=2)
    return array_to_surface(rgba)


def concrete_texture(w, h, seed=9):
    n = fbm(w, h, 20, 4, seed)
    col = np.array([0.74, 0.73, 0.70], np.float32) * (0.88 + 0.22 * n[..., None])
    rgba = np.concatenate([np.clip(col, 0, 1), np.ones((h, w, 1), np.float32)], axis=2)
    return array_to_surface(rgba)


def paint_surface(ctx, surf, x, y, sw=None, sh=None, alpha_=1.0):
    ctx.save()
    ctx.translate(x, y)
    if sw and sh:
        ctx.scale(sw / surf.get_width(), sh / surf.get_height())
    ctx.set_source_surface(surf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    if alpha_ < 1:
        ctx.paint_with_alpha(alpha_)
    else:
        ctx.paint()
    ctx.restore()
