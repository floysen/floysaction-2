"""Procedural materials (no texture files needed).

Every material is built from Blender nodes so the project has no
external texture dependencies. Names map to a cached bpy material.
"""
import bpy

_cache = {}


def hex_rgba(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    # sRGB -> linear
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b), a)


def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def _base(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    return m, nt, bsdf


def _ramp(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) > 2:
        els.remove(els[-1])
    for i, (pos, col) in enumerate(stops):
        e = els[i] if i < 2 else els.new(pos)
        e.position = pos
        e.color = hex_rgba(col)
    return r


def _noisy(name, stops, scale=4.0, detail=6.0, rough=0.9, bump=0.4,
           voronoi=None, coord="Object", distort=0.0, stretch=None):
    """Noise texture -> colour ramp -> principled, optional voronoi cracks."""
    m, nt, bsdf = _base(name)
    links = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    src = tc.outputs[coord]
    if stretch:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch
        links.new(src, mp.inputs["Vector"])
        src = mp.outputs["Vector"]
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    _set(noise, "Distortion", distort)
    links.new(src, noise.inputs["Vector"])
    ramp = _ramp(nt, stops)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    color_out = ramp.outputs["Color"]
    height = noise.outputs["Fac"]
    if voronoi:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = voronoi
        links.new(src, vor.inputs["Vector"])
        edge = _ramp(nt, [(0.0, "#2a1a10"), (0.06, "#ffffff")])
        links.new(vor.outputs["Distance"], edge.inputs["Fac"])
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.85
        links.new(color_out, mix.inputs["Color1"])
        links.new(edge.outputs["Color"], mix.inputs["Color2"])
        color_out = mix.outputs["Color"]
        height = vor.outputs["Distance"]
    links.new(color_out, bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", rough)
    if bump:
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        links.new(height, b.inputs["Height"])
        links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def _flat(name, col, rough=0.6, metal=0.0, emit=None, strength=0.0):
    m, nt, bsdf = _base(name)
    bsdf.inputs["Base Color"].default_value = hex_rgba(col)
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Metallic", metal)
    if emit:
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = hex_rgba(emit)
                break
        _set(bsdf, "Emission Strength", strength)
    return m


def _lawn(name):
    """Striped mowed lawn like the reference videos."""
    m, nt, bsdf = _base(name)
    links = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 0.35
    links.new(tc.outputs["Object"], wave.inputs["Vector"])
    ramp = _ramp(nt, [(0.49, "#4f9a2c"), (0.51, "#62b337")])
    links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.25
    links.new(noise.outputs["Fac"], b.inputs["Height"])
    links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Roughness", 0.95)
    return m


def _water(name, col_a, col_b, strength=0.15):
    m, nt, bsdf = _base(name)
    links = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.5
    noise.inputs["Detail"].default_value = 3
    links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = _ramp(nt, [(0.35, col_a), (0.65, col_b)])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    for key in ("Emission Color", "Emission"):
        if key in bsdf.inputs:
            links.new(ramp.outputs["Color"], bsdf.inputs[key])
            break
    _set(bsdf, "Emission Strength", strength)
    _set(bsdf, "Roughness", 0.15)
    return m


BUILDERS = {
    "soil": lambda n: _noisy(n, [(0.25, "#7a4524"), (0.5, "#9b5a2e"), (0.8, "#b8743d")],
                             scale=1.6, detail=8, voronoi=1.2, bump=0.6, distort=0.4,
                             stretch=(1.0, 1.0, 0.45)),
    "deep_soil": lambda n: _noisy(n, [(0.3, "#5e3a22"), (0.7, "#7d4c2b")],
                                  scale=1.4, detail=8, voronoi=1.0, bump=0.6),
    "dirt": lambda n: _noisy(n, [(0.3, "#8a5530"), (0.7, "#a86a3a")], scale=3, bump=0.8),
    "turf": lambda n: _noisy(n, [(0.3, "#3f7f22"), (0.7, "#5aa531")], scale=20, bump=0.3),
    "lawn": _lawn,
    "groundwater": lambda n: _water(n, "#3d7fd1", "#6aa8ee", 0.25),
    "water": lambda n: _water(n, "#9fe0e6", "#c8f1f2", 0.2),
    "muddy_water": lambda n: _water(n, "#8c8a3c", "#a8a454", 0.1),
    "sewage": lambda n: _water(n, "#b8c46a", "#d6dc8a", 0.1),
    "sludge": lambda n: _noisy(n, [(0.3, "#2e2116"), (0.7, "#4a3424")], scale=8, bump=0.3),
    "scum": lambda n: _noisy(n, [(0.3, "#d8b34a"), (0.7, "#f0d37a")], scale=10, bump=0.2),
    "concrete": lambda n: _noisy(n, [(0.3, "#9a9690"), (0.7, "#bdb9b2")], scale=12, bump=0.15),
    "dark_concrete": lambda n: _noisy(n, [(0.3, "#2b2b2e"), (0.7, "#3a3a3e")], scale=12, bump=0.2),
    "gravel": lambda n: _noisy(n, [(0.2, "#77746f"), (0.5, "#a9a59e"), (0.8, "#d4d0c8")],
                               scale=35, voronoi=30, bump=1.0),
    "stone": lambda n: _noisy(n, [(0.3, "#8f8d88"), (0.7, "#c9c6bf")], scale=6, bump=0.5),
    "sand": lambda n: _noisy(n, [(0.3, "#cfae72"), (0.7, "#e6c98f")], scale=40, bump=0.4),
    "clay": lambda n: _noisy(n, [(0.3, "#a9522d"), (0.7, "#c56a3c")], scale=6, bump=0.2),
    "brick": lambda n: _noisy(n, [(0.3, "#8e3b22"), (0.7, "#b0502e")], scale=4,
                              voronoi=3, bump=0.4),
    "asphalt": lambda n: _noisy(n, [(0.3, "#1e1e21"), (0.7, "#35353a")], scale=60, bump=0.3),
    "wood": lambda n: _noisy(n, [(0.3, "#7a5230"), (0.7, "#a3744a")], scale=3,
                             stretch=(1, 1, 12), bump=0.2),
    "bark": lambda n: _noisy(n, [(0.3, "#4a3524"), (0.7, "#6b4e35")], scale=8, bump=0.6),
    "leaf": lambda n: _noisy(n, [(0.3, "#2f5a22"), (0.6, "#4f7f30"), (0.9, "#6f9a40")],
                             scale=6, bump=0.6),
    "roof": lambda n: _noisy(n, [(0.3, "#c2552e"), (0.7, "#d86a3c")], scale=3, bump=0.2),
    "wall": lambda n: _flat(n, "#efe2cf", 0.8),
    "window": lambda n: _flat(n, "#2e4f8a", 0.1, metal=0.2),
    "white": lambda n: _flat(n, "#f4f4f2", 0.5),
    "dark": lambda n: _flat(n, "#202024", 0.6),
    "metal": lambda n: _flat(n, "#b9bec4", 0.3, metal=1.0),
    "pipe": lambda n: _flat(n, "#c9ccd0", 0.35, metal=0.6),
    "rust": lambda n: _noisy(n, [(0.3, "#6e3418"), (0.7, "#9a4f25")], scale=10, bump=0.3),
    "fence": lambda n: _noisy(n, [(0.3, "#4d3324"), (0.7, "#5f4130")], scale=2,
                              stretch=(12, 1, 1), bump=0.1),
    "fire": lambda n: _flat(n, "#ff7a1a", 0.5, emit="#ff8a20", strength=12),
    "ember": lambda n: _flat(n, "#ff3b10", 0.5, emit="#ff4010", strength=6),
    "smoke": lambda n: _flat(n, "#9a9a9a", 1.0),
    "rain": lambda n: _flat(n, "#d6e6f5", 0.1, emit="#d6e6f5", strength=0.6),
    "tire": lambda n: _flat(n, "#141414", 0.8),
    "truck_white": lambda n: _flat(n, "#ecedee", 0.4),
    "truck_red": lambda n: _flat(n, "#7b2a1e", 0.35, metal=0.3),
    "glass": lambda n: _flat(n, "#3b5466", 0.05, metal=0.5),
    "yellow": lambda n: _flat(n, "#f2c21b", 0.4),
}


def get(name):
    """Material by name, or by hex colour like '#ff00aa'."""
    if name in _cache and _cache[name].name in bpy.data.materials:
        return _cache[name]
    if name.startswith("#"):
        mat = _flat(name, name, 0.6)
    else:
        mat = BUILDERS.get(name, BUILDERS["concrete"])(name)
    _cache[name] = mat
    return mat


def reset():
    _cache.clear()
