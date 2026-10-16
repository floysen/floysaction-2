"""Procedural PBR texture set (albedo + normal + roughness), photo-like, tileable.

    python tools/make_textures.py   -> web/textures/<name>_{albedo,normal,rough}.jpg
All textures are generated from noise; no downloaded images, no licences.
"""
import os
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "textures")
N = 1024
rng = np.random.default_rng(7)


def tile_noise(n, cells, seed):
    """Tileable value noise with smooth interpolation."""
    r = np.random.default_rng(seed)
    g = r.random((cells, cells)).astype(np.float32)
    x = np.linspace(0, cells, n, endpoint=False)
    i0 = np.floor(x).astype(int)
    f = x - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells
    a = g[i0][:, i0]; b = g[i0][:, i1]; c = g[i1][:, i0]; d = g[i1][:, i1]
    fx = f[None, :]; fy = f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(n, base, octaves, seed, gain=0.5):
    out = np.zeros((n, n), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        out += tile_noise(n, base * 2 ** o, seed + o) * amp
        tot += amp; amp *= gain
    return out / tot


def stretch_fbm(n, bx, by, octaves, seed):
    """Anisotropic noise (bx cells across, by cells down) - vertical streaks when by < bx."""
    out = np.zeros((n, n), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        r = np.random.default_rng(seed + o)
        cx, cy = bx * 2 ** o, by * 2 ** o
        g = r.random((cy, cx)).astype(np.float32)
        xs = np.linspace(0, cx, n, endpoint=False); ys = np.linspace(0, cy, n, endpoint=False)
        x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
        fx = xs - x0; fy = ys - y0; fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        x1 = (x0 + 1) % cx; y1 = (y0 + 1) % cy
        a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
        out += ((a * (1 - fx) + b * fx) * (1 - fy[:, None]) + (c * (1 - fx) + d * fx) * fy[:, None]) * amp
        tot += amp; amp *= 0.5
    return out / tot


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + 1)
    nrm = np.stack([-dx / l, dy / l, nz / l], axis=2)
    return ((nrm * 0.5 + 0.5) * 255).astype(np.uint8)


def save(name, albedo, height, rough, nstrength):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((np.clip(albedo, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/{name}_albedo.jpg", quality=90)
    Image.fromarray(normal_from_height(height, nstrength)).save(f"{OUT}/{name}_normal.jpg", quality=92)
    Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/{name}_rough.jpg", quality=90)
    print("  ", name)


def lerp3(c1, c2, k):
    return np.array(c1)[None, None, :] * (1 - k[..., None]) + np.array(c2)[None, None, :] * k[..., None]


def soil():
    # eroded cut face: irregular rain-carved vertical forms of varying width, crumbly lumps,
    # pebbles; warm orange-tan.  Relief is carried by the normal map.
    big = stretch_fbm(N, 6, 1, 4, 1)
    mid = stretch_fbm(N, 16, 3, 3, 5)
    clod = fbm(N, 30, 4, 2)
    fine = fbm(N, 220, 2, 3)
    blot = fbm(N, 4, 3, 4)
    h = big * 0.55 + mid * 0.25 + clod * 0.22 + fine * 0.04
    cavity = np.clip((0.42 - (big * 0.7 + mid * 0.3)) * 5, 0, 1)
    alb = lerp3((0.42, 0.24, 0.11), (0.66, 0.42, 0.23), np.clip(0.5 + (clod - 0.5) * 1.0 + (blot - 0.5) * 0.6 + (big - 0.5) * 0.4, 0, 1))
    alb *= (0.94 + 0.1 * fine)[..., None]
    alb *= (1 - cavity * 0.5)[..., None]
    pb = ((fbm(N, 90, 2, 9) > 0.72) & (fine > 0.45)).astype(np.float32)
    alb = alb * (1 - pb[..., None] * 0.45) + pb[..., None] * np.array([0.66, 0.6, 0.52]) * 0.45
    save("soil", alb, h + pb * 0.06, 0.93 + 0.05 * fine, 40.0)


def grass():
    blades = stretch_fbm(N, 200, 40, 2, 11)
    clump = fbm(N, 12, 4, 12)
    fine = fbm(N, 256, 1, 13)
    k = np.clip(blades * 0.6 + clump * 0.5, 0, 1)
    alb = lerp3((0.12, 0.26, 0.05), (0.36, 0.56, 0.16), k)
    alb *= (0.85 + 0.3 * fine)[..., None]
    dry = np.clip((clump - 0.62) * 4, 0, 1)
    alb = alb * (1 - dry[..., None] * 0.35) + dry[..., None] * np.array([0.55, 0.52, 0.25]) * 0.35
    save("grass", alb, blades * 0.7 + clump * 0.3, 0.85 + 0.1 * fine, 6.0)


def concrete():
    base = fbm(N, 8, 6, 21)
    agg = fbm(N, 160, 2, 22)
    pits = (fbm(N, 220, 1, 23) > 0.78).astype(np.float32)
    alb = lerp3((0.55, 0.54, 0.51), (0.76, 0.75, 0.72), base)
    alb *= (0.92 + 0.12 * agg)[..., None]
    alb *= (1 - pits * 0.35)[..., None]
    save("concrete", alb, base * 0.4 + agg * 0.4 - pits * 0.4, 0.8 + 0.15 * agg, 5.0)


def asphalt():
    grit = fbm(N, 300, 2, 31); base = fbm(N, 10, 4, 32)
    alb = lerp3((0.12, 0.12, 0.13), (0.27, 0.27, 0.28), grit * 0.7 + base * 0.3)
    stones = (grit > 0.7).astype(np.float32)
    alb += stones[..., None] * 0.08
    save("asphalt", alb, grit, 0.75 + 0.2 * base, 6.0)


def plaster():
    base = fbm(N, 6, 6, 41); fine = fbm(N, 180, 2, 42)
    alb = lerp3((0.84, 0.78, 0.66), (0.94, 0.89, 0.79), base)
    alb *= (0.95 + 0.07 * fine)[..., None]
    save("plaster", alb, fine * 0.6 + base * 0.4, 0.88 + 0.06 * fine, 3.0)


def tiles():
    t = 128  # 8 x 8 tiles per texture
    yy, xx = np.mgrid[0:N, 0:N]
    gx = np.minimum(xx % t, t - xx % t); gy = np.minimum(yy % t, t - yy % t)
    grout = np.clip(1 - np.minimum(gx, gy) / 5.0, 0, 1)
    var = tile_noise(N, 8, 51)
    var = var[(yy // t) * t % N, (xx // t) * t % N]
    fine = fbm(N, 64, 2, 52)
    alb = lerp3((0.93, 0.95, 0.96), (0.98, 0.99, 1.0), var * 0.6 + fine * 0.4)
    alb = alb * (1 - grout[..., None]) + grout[..., None] * np.array([0.72, 0.74, 0.76])
    h = 1 - grout * 0.8 + fine * 0.05
    save("tiles", alb, h, 0.12 + grout * 0.7, 4.0)


def wood():
    rings = stretch_fbm(N, 6, 60, 4, 61)
    fine = stretch_fbm(N, 40, 400, 2, 62)
    plank = (np.arange(N) // (N // 6)) % 2
    alb = lerp3((0.30, 0.18, 0.09), (0.55, 0.36, 0.20), np.clip(rings * 1.2 - 0.1, 0, 1))
    alb *= (0.88 + 0.2 * fine)[..., None]
    alb *= (0.92 + 0.1 * plank)[None, :, None]
    seam = ((np.arange(N) % (N // 6)) < 4).astype(np.float32)
    alb *= (1 - seam * 0.6)[None, :, None]
    save("wood", alb, rings * 0.5 + fine * 0.3 - seam[None, :] * 0.5, 0.7 + 0.1 * fine, 4.0)


def stone():  # sandstone wall blocks for Saudi villa boundary walls
    t = 170
    yy, xx = np.mgrid[0:N, 0:N]
    off = ((yy // 85) % 2) * (t // 2)
    gx = np.minimum((xx + off) % t, t - (xx + off) % t); gy = np.minimum(yy % 85, 85 - yy % 85)
    joint = np.clip(1 - np.minimum(gx, gy) / 4.0, 0, 1)
    base = fbm(N, 16, 5, 71); fine = fbm(N, 200, 1, 72)
    alb = lerp3((0.72, 0.60, 0.44), (0.86, 0.76, 0.60), base)
    alb *= (0.9 + 0.15 * fine)[..., None]
    alb = alb * (1 - joint[..., None] * 0.45)
    save("stone", alb, base * 0.5 + fine * 0.3 - joint * 0.6, 0.9 + 0.05 * fine, 5.0)


def floortile():
    t = 256  # 4 x 4 checker tiles
    yy, xx = np.mgrid[0:N, 0:N]
    chk = (((xx // t) + (yy // t)) % 2).astype(np.float32)
    gx = np.minimum(xx % t, t - xx % t); gy = np.minimum(yy % t, t - yy % t)
    grout = np.clip(1 - np.minimum(gx, gy) / 4.0, 0, 1)
    fine = fbm(N, 40, 3, 101)
    alb = lerp3((0.55, 0.58, 0.62), (0.93, 0.94, 0.95), chk) * (0.95 + 0.08 * fine)[..., None]
    alb = alb * (1 - grout[..., None] * 0.5)
    save("floortile", alb, 1 - grout * 0.8 + fine * 0.03, 0.18 + grout * 0.6, 4.0)


def brick():
    bw, bh = 128, 56
    yy, xx = np.mgrid[0:N, 0:N]
    off = ((yy // bh) % 2) * (bw // 2)
    gx = np.minimum((xx + off) % bw, bw - (xx + off) % bw); gy = np.minimum(yy % bh, bh - yy % bh)
    mortar = np.clip(1 - np.minimum(gx, gy) / 5.0, 0, 1)
    var = fbm(N, 16, 4, 111); fine = fbm(N, 160, 2, 112)
    alb = lerp3((0.45, 0.17, 0.10), (0.68, 0.30, 0.18), var) * (0.9 + 0.15 * fine)[..., None]
    alb = alb * (1 - mortar[..., None]) + mortar[..., None] * np.array([0.78, 0.74, 0.68])
    save("brick", alb, 1 - mortar * 0.7 + fine * 0.1, 0.85 + 0.05 * fine, 6.0)


def cloud_sprite():
    n = 512
    yy, xx = np.mgrid[0:n, 0:n] / n
    d = np.sqrt(((xx - 0.5) * 1.6) ** 2 + ((yy - 0.55) * 2.6) ** 2)
    nz = fbm(n, 6, 6, 81)
    a = np.clip((nz * 1.3 - 0.25) - d * 1.4, 0, 1) ** 0.9
    shade = 0.78 + 0.22 * (1 - yy)
    rgba = np.dstack([shade, shade, shade * 1.02, a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/cloud.png")
    print("   cloud")


def leaf_cluster():
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / n
    d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    nz = fbm(n, 24, 3, 91)
    a = ((nz > 0.42) & (d < 0.48)).astype(np.float32)
    g = lerp3((0.12, 0.25, 0.06), (0.35, 0.55, 0.15), nz)
    rgba = np.dstack([g, a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/leaves.png")
    print("   leaves")


def palm_frond():
    w, h = 512, 128
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / w; v = (yy - h / 2) / (h / 2)
    width = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.6 * 0.95
    leaflet = (np.abs(np.sin(u * 90)) > 0.25)
    a = ((np.abs(v) < width) & (leaflet | (np.abs(v) < 0.06))).astype(np.float32)
    col = lerp3((0.14, 0.30, 0.08), (0.40, 0.58, 0.20), np.clip(1 - np.abs(v), 0, 1))
    rgba = np.dstack([col, a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/frond.png")
    print("   frond")


if __name__ == "__main__":
    for f in (soil, grass, concrete, asphalt, plaster, tiles, wood, stone, floortile, brick, cloud_sprite, leaf_cluster, palm_frond):
        f()
