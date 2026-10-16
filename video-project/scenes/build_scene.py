"""Builds the complete animated 3D scene for
"How a Hole in Your Yard Becomes a Swimming Pool" and saves build/pool.blend.

Run (done automatically by render.sh):
    blender -b --factory-startup --python scenes/build_scene.py

Every event time comes from scripts/shotplan.py, which reads the voiceover
alignment in data/timeline.json.
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import lib  # noqa: E402
from lib import (F, box, cylinder, sphere, ico, torus, key, keys, vis, show_between,  # noqa: E402
                 pop_in, pop_out, drop_in, empty, parent, camera, camera_moves, emitter,
                 particle_shape, principled, key_value, value_node, curve_path, follow_path,
                 smooth_path_points, damped_rotation, use_collection, collection)
import shotplan as SP  # noqa: E402

E = SP.E
lib.FPS = SP.FPS
RND = random.Random(7)

# pool geometry (metres).  Inner basin 8 x 4 x 2, 25 cm shotcrete shell.
IX, IY, DEPTH, TH = 4.0, 2.0, 2.0, 0.25
OX, OY, OB = IX + TH, IY + TH, -(DEPTH + TH)
WL = -0.15  # full water level


def hold(ob, path, t, old, new):
    """Instant change at time t (used on camera cuts)."""
    key(ob, path, t - 0.02, old)
    key(ob, path, t, new)


# ============================================================== materials
def build_materials():
    M = {}
    # --- soil with geological strata (visible in cross-sections)
    m = lib.new_material("soil")
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 8
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.35
    mp = nt.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = -9.0
    mp.inputs["From Max"].default_value = 0.2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    stops = [(0.0, (0.30, 0.27, 0.24)), (0.30, (0.42, 0.30, 0.20)), (0.52, (0.55, 0.36, 0.22)),
             (0.70, (0.72, 0.58, 0.40)), (0.86, (0.60, 0.45, 0.30)), (0.97, (0.36, 0.25, 0.16))]
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[1][0], (*stops[1][1], 1)
    for p, c in stops[2:]:
        e = cr.elements.new(p)
        e.color = (*c, 1)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], add.inputs[0])
    nt.links.new(sep.outputs["Z"], add.inputs[2])
    nt.links.new(add.outputs[0], mp.inputs["Value"])
    nt.links.new(mp.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    lib.add_noise_bump(m, scale=12, strength=0.35)
    M["soil"] = m

    # --- yard pavers
    m = lib.new_material("pavers")
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.75
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.6
    br.inputs["Color1"].default_value = (0.60, 0.50, 0.38, 1)
    br.inputs["Color2"].default_value = (0.52, 0.43, 0.33, 1)
    br.inputs["Mortar"].default_value = (0.36, 0.31, 0.27, 1)
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.6
    br.inputs["Row Height"].default_value = 0.3
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.4
    bp.invert = True
    nt.links.new(br.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    M["pavers"] = m

    M["dirt"] = principled("dirt", (0.40, 0.27, 0.16), rough=0.95, bump=(18, 0.5))
    lib.color_variation(M["dirt"], (0.30, 0.20, 0.12), (0.50, 0.35, 0.22), scale=6)
    M["mud"] = principled("mud", (0.33, 0.22, 0.13), rough=0.6, bump=(10, 0.4))

    # --- concrete shell with spray reveal, algae and tile finish
    m = lib.new_material("shell")
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.8
    out = nt.nodes["Material Output"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    conc = nt.nodes.new("ShaderNodeValToRGB")
    conc.color_ramp.elements[0].color = (0.50, 0.50, 0.48, 1)
    conc.color_ramp.elements[1].color = (0.72, 0.71, 0.68, 1)
    nt.links.new(nz.outputs["Fac"], conc.inputs["Fac"])
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 4.0
    brick.inputs["Color1"].default_value = (0.20, 0.62, 0.78, 1)
    brick.inputs["Color2"].default_value = (0.14, 0.52, 0.72, 1)
    brick.inputs["Mortar"].default_value = (0.92, 0.95, 0.96, 1)
    brick.inputs["Mortar Size"].default_value = 0.03
    brick.inputs["Brick Width"].default_value = 0.5
    brick.inputs["Row Height"].default_value = 0.5
    mapping = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    mapping.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    add_v = nt.nodes.new("ShaderNodeVectorMath")
    add_v.operation = "ADD"
    nt.links.new(tc.outputs["Object"], add_v.inputs[0])
    nt.links.new(mapping.outputs["Vector"], add_v.inputs[1])
    nt.links.new(add_v.outputs["Vector"], brick.inputs["Vector"])
    # tile sweep factor: x < tile_front
    tile_front = value_node(m, "tile_front", -6.0)
    cmp_t = nt.nodes.new("ShaderNodeMath")
    cmp_t.operation = "LESS_THAN"
    nt.links.new(sep.outputs["X"], cmp_t.inputs[0])
    nt.links.new(tile_front.outputs[0], cmp_t.inputs[1])
    mix_t = nt.nodes.new("ShaderNodeMix")
    mix_t.data_type = "RGBA"
    nt.links.new(cmp_t.outputs[0], mix_t.inputs["Factor"])
    nt.links.new(conc.outputs["Color"], mix_t.inputs[6])
    nt.links.new(brick.outputs["Color"], mix_t.inputs[7])
    # algae overlay
    algae = value_node(m, "algae", 0.0)
    nz2 = nt.nodes.new("ShaderNodeTexNoise")
    nz2.inputs["Scale"].default_value = 1.4
    nz2.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.use_clamp = True
    sm = nt.nodes.new("ShaderNodeMapRange")
    sm.inputs["From Min"].default_value = 0.35
    sm.inputs["From Max"].default_value = 0.6
    nt.links.new(nz2.outputs["Fac"], sm.inputs["Value"])
    nt.links.new(sm.outputs["Result"], mul.inputs[0])
    nt.links.new(algae.outputs[0], mul.inputs[1])
    mix_a = nt.nodes.new("ShaderNodeMix")
    mix_a.data_type = "RGBA"
    mix_a.inputs[7].default_value = (0.16, 0.36, 0.08, 1)
    nt.links.new(mul.outputs[0], mix_a.inputs["Factor"])
    nt.links.new(mix_t.outputs[2], mix_a.inputs[6])
    nt.links.new(mix_a.outputs[2], bsdf.inputs["Base Color"])
    rough_mix = nt.nodes.new("ShaderNodeMapRange")
    rough_mix.inputs["To Min"].default_value = 0.85
    rough_mix.inputs["To Max"].default_value = 0.12
    nt.links.new(cmp_t.outputs[0], rough_mix.inputs["Value"])
    nt.links.new(rough_mix.outputs["Result"], bsdf.inputs["Roughness"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.25
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    # spray reveal: visible where x + noise*0.4 < spray_front
    spray_front = value_node(m, "spray_front", -6.0)
    nadd = nt.nodes.new("ShaderNodeMath")
    nadd.operation = "MULTIPLY_ADD"
    nadd.inputs[1].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], nadd.inputs[0])
    nt.links.new(sep.outputs["X"], nadd.inputs[2])
    cmp_s = nt.nodes.new("ShaderNodeMath")
    cmp_s.operation = "LESS_THAN"
    nt.links.new(nadd.outputs[0], cmp_s.inputs[0])
    nt.links.new(spray_front.outputs[0], cmp_s.inputs[1])
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cmp_s.outputs[0], mixs.inputs[0])
    nt.links.new(transp.outputs[0], mixs.inputs[1])
    nt.links.new(bsdf.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs["Surface"])
    lib.set_blend(m)
    M["shell"] = m
    M["concrete_cut"] = principled("concrete_cut", (0.55, 0.55, 0.53), rough=0.9, bump=(25, 0.3))
    M["concrete"] = principled("concrete", (0.66, 0.65, 0.62), rough=0.85, bump=(14, 0.15))

    # --- water (colour can turn green)
    m = lib.new_material("water")
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.04
    bsdf.inputs["IOR"].default_value = 1.333
    lib._sock(bsdf, "Transmission Weight", "Transmission").default_value = 0.75
    bsdf.inputs["Alpha"].default_value = 0.72
    green = value_node(m, "green", 0.0)
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.inputs[6].default_value = (0.08, 0.55, 0.85, 1)
    mixc.inputs[7].default_value = (0.20, 0.45, 0.10, 1)
    nt.links.new(green.outputs[0], mixc.inputs["Factor"])
    nt.links.new(mixc.outputs[2], bsdf.inputs["Base Color"])
    alpha_mr = nt.nodes.new("ShaderNodeMapRange")
    alpha_mr.inputs["To Min"].default_value = 0.72
    alpha_mr.inputs["To Max"].default_value = 0.93
    nt.links.new(green.outputs[0], alpha_mr.inputs["Value"])
    nt.links.new(alpha_mr.outputs["Result"], bsdf.inputs["Alpha"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wn = nt.nodes.new("ShaderNodeTexNoise")
    wn.noise_dimensions = "4D"
    wn.name = "ripple"
    wn.inputs["Scale"].default_value = 1.6
    wn.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], wn.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.18
    nt.links.new(wn.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    wn.inputs["W"].default_value = 0.0
    wn.inputs["W"].keyframe_insert("default_value", frame=1)
    wn.inputs["W"].default_value = SP.DURATION * 0.35
    wn.inputs["W"].keyframe_insert("default_value", frame=F(SP.DURATION))
    for fc in nt.animation_data.action.fcurves:
        if "ripple" in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    lib.set_blend(m)
    M["water"] = m
    M["groundwater"] = principled("groundwater", (0.10, 0.42, 0.85), rough=0.2, alpha=0.62,
                                  emission=(0.05, 0.3, 0.8), emission_strength=0.25)
    M["drop"] = principled("drop", (0.25, 0.65, 1.0), rough=0.05, emission=(0.2, 0.6, 1.0),
                           emission_strength=1.5)
    M["rebar"] = principled("rebar", (0.28, 0.20, 0.16), rough=0.55, metal=0.85, bump=(60, 0.4))
    M["steel"] = principled("steel", (0.85, 0.86, 0.88), rough=0.18, metal=1.0)
    M["brass"] = principled("brass", (0.85, 0.62, 0.30), rough=0.25, metal=1.0)
    M["dark"] = principled("dark_plastic", (0.03, 0.035, 0.04), rough=0.4)
    M["white_plastic"] = principled("white_plastic", (0.92, 0.93, 0.92), rough=0.3)
    M["pvc"] = principled("pvc", (0.93, 0.94, 0.95), rough=0.25, coat=0.3)
    M["pump_blue"] = principled("pump_blue", (0.05, 0.25, 0.65), rough=0.3, coat=0.5)
    M["tank"] = principled("tank", (0.06, 0.45, 0.55), rough=0.25, coat=0.6)
    M["sand"] = principled("sand", (0.85, 0.72, 0.50), rough=0.9, bump=(80, 0.6))
    M["sand_macro"] = principled("sand_macro", (0.80, 0.62, 0.38), rough=0.55, subsurface=0.15, bump=(30, 0.04))
    M["gravel"] = principled("gravel", (0.45, 0.43, 0.40), rough=0.9, bump=(20, 0.8))
    M["grime"] = principled("grime", (0.18, 0.13, 0.07), rough=0.9)
    M["plaster"] = principled("plaster", (0.93, 0.89, 0.81), rough=0.85, bump=(9, 0.12))
    lib.color_variation(M["plaster"], (0.88, 0.83, 0.74), (0.96, 0.93, 0.86), scale=2)
    M["wall"] = principled("yard_wall", (0.86, 0.76, 0.60), rough=0.9, bump=(7, 0.2))
    lib.color_variation(M["wall"], (0.80, 0.69, 0.53), (0.90, 0.81, 0.66), scale=1.5)
    M["trim"] = principled("trim", (0.62, 0.50, 0.36), rough=0.7)
    M["glass"] = principled("window_glass", (0.08, 0.16, 0.22), rough=0.04, metal=0.3, coat=1.0)
    M["wood"] = principled("wood", (0.36, 0.20, 0.10), rough=0.5, bump=(4, 0.15))
    lib.color_variation(M["wood"], (0.30, 0.16, 0.08), (0.45, 0.27, 0.14), scale=12)
    M["trunk"] = principled("palm_trunk", (0.40, 0.30, 0.20), rough=0.9, bump=(14, 0.8))
    M["frond"] = principled("palm_frond", (0.20, 0.42, 0.12), rough=0.6, subsurface=0.1)
    M["bush"] = principled("bush", (0.18, 0.40, 0.14), rough=0.7, bump=(10, 0.7))
    M["pot"] = principled("terracotta", (0.66, 0.33, 0.20), rough=0.7)
    M["leaf"] = principled("leaf", (0.45, 0.55, 0.12), rough=0.5)
    M["leaf2"] = principled("leaf_dry", (0.75, 0.50, 0.12), rough=0.6)
    M["pebble"] = principled("pebble", (0.42, 0.40, 0.38), rough=0.6, bump=(8, 0.3))
    M["tile_coping"] = principled("coping", (0.92, 0.88, 0.80), rough=0.45, bump=(5, 0.1))
    M["board"] = principled("board", (0.95, 0.96, 0.97), rough=0.2, coat=0.8)
    M["board_blue"] = principled("board_blue", (0.05, 0.35, 0.75), rough=0.25, coat=0.6)
    M["ring_red"] = principled("ring_red", (0.85, 0.10, 0.08), rough=0.25, coat=0.8)
    M["ring_white"] = principled("ring_white", (0.95, 0.95, 0.95), rough=0.25, coat=0.8)
    M["fabric"] = principled("fabric", (0.95, 0.55, 0.15), rough=0.8)
    M["fabric2"] = principled("fabric_white", (0.95, 0.94, 0.90), rough=0.8)
    M["confetti_a"] = principled("confetti_a", (1.0, 0.75, 0.1), rough=0.4, emission=(1, 0.75, 0.1), emission_strength=0.6)
    M["confetti_b"] = principled("confetti_b", (0.1, 0.7, 1.0), rough=0.4, emission=(0.1, 0.7, 1), emission_strength=0.6)
    M["confetti_c"] = principled("confetti_c", (1.0, 0.25, 0.45), rough=0.4, emission=(1, 0.25, 0.45), emission_strength=0.6)
    M["arrow"] = principled("arrow", (0.2, 0.75, 1.0), rough=0.3, alpha=0.85,
                            emission=(0.15, 0.6, 1.0), emission_strength=2.0)
    M["arrow_up"] = principled("arrow_up", (0.15, 0.55, 1.0), rough=0.3,
                               emission=(0.15, 0.5, 1.0), emission_strength=3.0)
    M["flow"] = principled("flow", (0.25, 0.7, 1.0), emission=(0.2, 0.65, 1.0), emission_strength=4.0)
    M["flow_dirty"] = principled("flow_dirty", (0.35, 0.5, 0.12), emission=(0.3, 0.5, 0.1), emission_strength=2.5)
    M["glow"] = principled("glow_ring", (1.0, 0.85, 0.3), emission=(1.0, 0.8, 0.25), emission_strength=6.0)
    M["bacteria"] = principled("bacteria", (0.35, 0.85, 0.20), rough=0.35, subsurface=0.3,
                               emission=(0.3, 0.9, 0.15), emission_strength=0.6)
    M["chlorine"] = principled("chlorine_drop", (0.85, 1.0, 0.55), rough=0.1,
                               emission=(0.8, 1.0, 0.4), emission_strength=4.0)
    M["vapor"] = principled("vapor", (0.80, 0.92, 0.45), rough=0.9, alpha=0.16,
                            emission=(0.7, 0.85, 0.30), emission_strength=0.25)
    M["atom_cl"] = principled("atom_cl", (0.25, 0.85, 0.25), rough=0.3, coat=0.8)
    M["atom_n"] = principled("atom_n", (0.15, 0.30, 0.95), rough=0.3, coat=0.8)
    M["atom_h"] = principled("atom_h", (0.95, 0.95, 0.95), rough=0.3, coat=0.8)
    M["atom_c"] = principled("atom_c", (0.15, 0.15, 0.17), rough=0.3, coat=0.8)
    M["atom_o"] = principled("atom_o", (0.95, 0.15, 0.12), rough=0.3, coat=0.8)
    M["bond"] = principled("bond", (0.75, 0.75, 0.78), rough=0.3, metal=0.5)
    M["cross"] = principled("cross", (0.95, 0.12, 0.12), emission=(1, 0.1, 0.1), emission_strength=3.0)
    M["flash"] = principled("flash", (1, 1, 0.8), emission=(1, 0.95, 0.7), emission_strength=12.0)
    M["backdrop_macro"] = principled("backdrop_macro", (0.05, 0.22, 0.28), rough=1.0,
                                     emission=(0.03, 0.18, 0.24), emission_strength=0.6)
    M["backdrop_mol"] = principled("backdrop_mol", (0.10, 0.14, 0.22), rough=1.0,
                                   emission=(0.06, 0.10, 0.20), emission_strength=0.7)
    M["chrome"] = principled("chrome", (0.95, 0.95, 0.96), rough=0.06, metal=1.0)
    M["lounger"] = principled("lounger", (0.96, 0.96, 0.94), rough=0.4)
    M["glass_tank"] = principled("tank_clear", (0.06, 0.45, 0.55), rough=0.15, alpha=1.0, coat=0.6)
    M["tank_alpha"] = M["glass_tank"]
    return M


# ============================================================== world, light
def build_world():
    w = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(48)
    sky.sun_rotation = math.radians(200)
    sky.altitude = 200
    sky.air_density = 1.2
    sky.dust_density = 1.5
    sky.sun_disc = False
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.28
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(2.5)
    sun_d.color = (1.0, 0.96, 0.9)
    sun = bpy.data.objects.new("Sun", sun_d)
    lib.link(sun)
    sun.rotation_euler = (math.radians(42), 0, math.radians(-28))
    return sun, sky, bg


# ============================================================== yard & house
def build_yard(M):
    use_collection(collection("Yard"))
    # soil block with the pool pit carved out
    soil = box("Soil", (44, 44, 20), (0, 0, 0), M["soil"], origin="top")
    pit = box("pit_cut", (2 * OX, 2 * OY, 3), (0, 0, OB), origin="bottom")
    lib.boolean(soil, pit)
    soil.data.materials.append(M["pavers"])
    for p in soil.data.polygons:
        if p.normal.z > 0.9 and p.center.z > -0.01:
            p.material_index = 1
    # dirt plug that is "dug out" at the start
    plug = box("DirtPlug", (2 * OX - 0.01, 2 * OY - 0.01, -OB), (0, 0, OB), M["dirt"], origin="bottom")
    keys(plug, "scale", [(0, (1, 1, 1)), (E["dig"], (1, 1, 1)), (E["dig_end"] + 0.4, (1, 1, 0.002))])
    vis(plug, [(0, True), (E["dig_end"] + 0.42, False)])
    # pit border kerb before it is dug (marks the area)
    house = []
    # house facade (back of yard)
    hb = box("House", (20, 7, 7.2), (0, 13.5, 0), M["plaster"], bevel=0.05, origin="bottom")
    house.append(hb)
    house.append(box("HouseUpper", (12, 6.5, 3.4), (-3.5, 13.7, 7.2), M["plaster"], bevel=0.05, origin="bottom"))
    house.append(box("Parapet", (20.3, 7.3, 0.5), (0, 13.5, 7.2), M["trim"], bevel=0.03, origin="bottom"))
    house.append(box("Parapet2", (12.3, 6.8, 0.4), (-3.5, 13.7, 10.6), M["trim"], bevel=0.03, origin="bottom"))
    for i, x in enumerate((-7.5, -3.5, 3.5, 7.5)):
        house.append(box(f"Window{i}", (2.0, 0.2, 1.9), (x, 9.95, 3.6), M["glass"], bevel=0.02))
        house.append(box(f"WindowFrame{i}", (2.3, 0.15, 2.2), (x, 10.02, 3.6), M["trim"], bevel=0.02))
        house.append(box(f"Sill{i}", (2.5, 0.35, 0.12), (x, 9.85, 2.55), M["trim"], bevel=0.02))
    for i, x in enumerate((-6.5, -0.5)):
        house.append(box(f"WindowUp{i}", (1.8, 0.2, 1.6), (x, 10.4, 8.6), M["glass"], bevel=0.02))
    house.append(box("Door", (2.4, 0.25, 3.2), (0, 9.95, 0), M["wood"], bevel=0.03, origin="bottom"))
    house.append(box("DoorFrame", (2.9, 0.18, 3.6), (0, 10.03, 0), M["trim"], bevel=0.03, origin="bottom"))
    house.append(box("Canopy", (4.5, 1.6, 0.2), (0, 9.4, 3.8), M["trim"], bevel=0.04))
    house.append(box("Step", (4, 1.2, 0.18), (0, 9.4, 0), M["concrete"], bevel=0.02, origin="bottom"))
    for i, x in enumerate((-9.3, 8.6)):
        ac = box(f"AC{i}", (1.1, 0.6, 0.8), (x, 9.6, 6.0), M["white_plastic"], bevel=0.04)
        house.append(ac)
        house.append(cylinder(f"ACfan{i}", 0.28, 0.05, (x, 9.28, 6.0), M["dark"], rot=(math.pi / 2, 0, 0)))
    # boundary walls (side walls extend toward camera; front wall behind camera)
    walls = []
    walls.append(box("WallL", (0.35, 30, 2.8), (-12.5, -3.5, 0), M["wall"], bevel=0.03, origin="bottom"))
    walls.append(box("WallR", (0.35, 30, 2.8), (12.5, -3.5, 0), M["wall"], bevel=0.03, origin="bottom"))
    walls.append(box("WallF", (25.3, 0.35, 2.8), (0, -18.5, 0), M["wall"], bevel=0.03, origin="bottom"))
    for nm, sz, loc in (("CapL", (0.55, 30.2, 0.15), (-12.5, -3.5, 2.8)), ("CapR", (0.55, 30.2, 0.15), (12.5, -3.5, 2.8)),
                        ("CapF", (25.5, 0.55, 0.15), (0, -18.5, 2.8))):
        walls.append(box(nm, sz, loc, M["trim"], bevel=0.02, origin="bottom"))
    for i in range(7):
        y = -17 + i * 4.5
        for x in (-12.5, 12.5):
            walls.append(box(f"Pillar{i}{x}", (0.6, 0.6, 3.05), (x, y, 0), M["trim"], bevel=0.03, origin="bottom"))
    # neighbours beyond the wall
    for i, (x, y, w, d, h) in enumerate(((-19, 6, 8, 8, 8), (19, 4, 8, 10, 9.5), (-17, 22, 10, 6, 11),
                                         (16, 22, 12, 6, 7), (0, 26, 14, 4, 13))):
        house.append(box(f"Neighbour{i}", (w, d, h), (x, y, 0), M["wall" if i % 2 else "plaster"], bevel=0.05, origin="bottom"))
    # palm trees
    def palm(name, loc, h=6.0, lean=(0.0, 0.0)):
        parts = []
        segs = 9
        for s in range(segs):
            z = h * s / segs
            r = 0.24 - 0.06 * s / segs
            c = cylinder(f"{name}_t{s}", r, h / segs * 1.02, (loc[0] + lean[0] * (z / h) ** 2, loc[1] + lean[1] * (z / h) ** 2, z),
                         M["trunk"], verts=12, r2=r * 0.86, origin="bottom")
            parts.append(c)
        top = Vector((loc[0] + lean[0], loc[1] + lean[1], h))
        for k in range(11):
            a = 2 * math.pi * k / 11 + RND.uniform(-0.2, 0.2)
            droop = RND.uniform(0.35, 0.8)
            pts = []
            for j in range(7):
                u = j / 6
                pts.append(top + Vector((math.cos(a) * 3.0 * u, math.sin(a) * 3.0 * u, 0.9 * u - droop * 2.2 * u * u)))
            cu = curve_path(f"{name}_f{k}", [tuple(p) for p in pts], bevel=0.0, mat=M["frond"])
            cu.data.extrude = 0.32
            cu.data.bevel_depth = 0.0
            cu.data.twist_mode = "Z_UP"
            cu.data.taper_radius_mode = "MULTIPLY"
            parts.append(cu)
        parts.append(ico(f"{name}_crown", 0.35, tuple(top), M["trunk"], sub=2))
        return parts
    palms = []
    palms += palm("PalmA", (-10.5, 6.5, 0), 6.6, (0.6, -0.3))
    palms += palm("PalmB", (10.4, 6.0, 0), 5.8, (-0.5, 0.2))
    palms += palm("PalmC", (-11.0, 1.5, 0), 4.6, (0.8, 0.1))
    palms += palm("PalmBack", (14.5, 12.5, 0), 7.5, (0.2, 0.2))
    # planters and bushes
    for i, (x, y) in enumerate(((-6.5, 9.0), (6.5, 9.0), (-11.4, 4.5), (11.4, 3.0), (11.4, -1.0))):
        house.append(cylinder(f"Pot{i}", 0.45, 0.8, (x, y, 0), M["pot"], r2=0.55, origin="bottom"))
        house.append(ico(f"Bush{i}", 0.75, (x, y, 1.25), M["bush"], sub=2, jitter=0.18, seed=i))
    # perimeter lights
    for i, x in enumerate((-12.2, 12.2)):
        for j, y in enumerate((-8, 1)):
            house.append(box(f"Lamp{i}{j}", (0.18, 0.18, 0.3), (x * 0.985, y, 2.0), M["dark"]))
    # front-yard props live in y < 0 and must disappear in cross-section shots
    shovel_h = cylinder("ShovelHandle", 0.035, 1.5, (0, 0, 0.75), M["wood"], verts=10)
    blade = box("ShovelBlade", (0.32, 0.04, 0.38), (0, 0, -0.08), M["steel"], bevel=0.01)
    shovel = empty("Shovel", (1.0, -1.0, 0.2))
    parent(shovel_h, shovel, keep=False)
    shovel_h.location = (0, 0, 0.75)
    parent(blade, shovel, keep=False)
    blade.location = (0, 0, -0.1)
    # wheelbarrow beside the dirt pile
    wb = empty("Wheelbarrow", (-7.6, 2.6, 0))
    tray = box("WB_tray", (1.3, 0.75, 0.45), (0, 0, 0.62), M["pump_blue"], bevel=0.06)
    parent(tray, wb, keep=False)
    tray.location = (0, 0, 0.62)
    wh = cylinder("WB_wheel", 0.22, 0.1, (0.85, 0, 0.22), M["dark"], rot=(math.pi / 2, 0, 0))
    parent(wh, wb, keep=False)
    wh.location = (0.85, 0, 0.22)
    for s in (-1, 1):
        h = cylinder(f"WB_handle{s}", 0.025, 1.6, (-0.4, 0.3 * s, 0.6), M["steel"], rot=(0, math.radians(80), 0))
        parent(h, wb, keep=False)
        h.location = (-0.4, 0.3 * s, 0.6)
    wb.rotation_euler = (0, 0, math.radians(20))
    return dict(soil=soil, plug=plug, house=house, walls=walls, palms=palms, shovel=shovel, wheelbarrow=wb)


# ============================================================== section cutting
class Section:
    """A cross-section rig: every registered object gets a boolean cutter that
    removes the half y < ctrl.y.  ctrl.y animates to slice the scene open."""
    OFF = -30.0

    def __init__(self):
        self.ctrl = empty("SectionCtrl", (0, self.OFF, 0))
        self.windows = []

    def add(self, ob, mat, offset=0.0):
        cut = box(f"cut_{ob.name}", (400, 200, 400), (0, -100 + offset, 0))
        cut.parent = self.ctrl
        cut.hide_render = True
        cut.display_type = "WIRE"
        cut.data.materials.append(mat)
        cut.visible_camera = False
        cut.visible_shadow = False
        m = ob.modifiers.new("Section", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.object = cut
        m.solver = "EXACT"
        try:
            m.material_mode = "TRANSFER"
        except AttributeError:
            pass
        # keep bevel/other modifiers before the cut
        return cut

    def window(self, t0, t1, slide=0.7, start=-6.0):
        self.windows.append((t0, t1, slide, start))

    def finalize(self):
        """Keyframe the cut plane; back-to-back windows stay open across the cut."""
        c = self.ctrl
        ws = sorted(self.windows)
        key(c, "location", 0, (0, self.OFF, 0))
        prev_end = None
        for i, (t0, t1, slide, start) in enumerate(ws):
            if prev_end is None or abs(t0 - prev_end) > 0.05:
                hold(c, "location", t0, (0, self.OFF, 0), (0, start, 0))
                key(c, "location", t0 + slide, (0, 0, 0))
            else:
                key(c, "location", t0, (0, 0, 0))
            nxt = ws[i + 1][0] if i + 1 < len(ws) else None
            if nxt is None or abs(nxt - t1) > 0.05:
                hold(c, "location", t1, (0, 0, 0), (0, self.OFF, 0))
            prev_end = t1
        self.windows = [(a, b) for a, b, _, _ in ws]


# ============================================================== pool
def build_pool(M, sec):
    use_collection(collection("Pool"))
    body = empty("PoolBody", (0, 0, 0))
    # shotcrete shell (open box)
    shell = box("Shell", (2 * OX, 2 * OY, -OB), (0, 0, OB), M["shell"], origin="bottom")
    inner = box("shell_in", (2 * IX, 2 * IY, 3), (0, 0, -DEPTH), origin="bottom")
    lib.boolean(shell, inner)
    bv = shell.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.03
    bv.segments = 2
    shell.data.materials.append(M["concrete_cut"])
    parent(shell, body)
    sec.add(shell, M["concrete_cut"])
    # shell invisible until sprayed
    m = M["shell"]
    key_value(m, "spray_front", 0, -6.0)
    key_value(m, "spray_front", E["spray"], -6.0)
    key_value(m, "spray_front", E["shell_done"], 5.5)
    vis(shell, [(0, False), (E["spray"] - 0.05, True)])

    # rebar cage in four groups
    groups = {"floor_x": [], "floor_y": [], "walls_v": [], "walls_h": []}
    r = 0.028
    zf = OB + TH / 2
    sp = 0.45
    nx = int(2 * IX / sp)
    ny = int(2 * IY / sp)
    for i in range(nx + 1):
        x = -IX + i * (2 * IX / nx)
        groups["floor_y"].append(cylinder(f"rb_fy{i}", r, 2 * (OY - 0.12), (x, 0, zf), M["rebar"], verts=8, rot=(math.pi / 2, 0, 0)))
    for j in range(ny + 1):
        y = -IY + j * (2 * IY / ny)
        groups["floor_x"].append(cylinder(f"rb_fx{j}", r, 2 * (OX - 0.12), (0, y, zf + 0.06), M["rebar"], verts=8, rot=(0, math.pi / 2, 0)))
    wx, wy = IX + TH / 2, IY + TH / 2
    hz = DEPTH + TH - 0.1
    for i in range(nx + 1):
        x = -IX + i * (2 * IX / nx)
        for y in (-wy, wy):
            groups["walls_v"].append(cylinder(f"rb_v{i}{y}", r, hz, (x, y, OB + 0.05), M["rebar"], verts=8, origin="bottom"))
    for j in range(ny + 1):
        y = -IY + j * (2 * IY / ny)
        for x in (-wx, wx):
            groups["walls_v"].append(cylinder(f"rb_v2{j}{x}", r, hz, (x, y, OB + 0.05), M["rebar"], verts=8, origin="bottom"))
    for k in range(5):
        z = OB + 0.3 + k * 0.45
        for y in (-wy, wy):
            groups["walls_h"].append(cylinder(f"rb_h{k}{y}", r, 2 * wx, (0, y, z), M["rebar"], verts=8, rot=(0, math.pi / 2, 0)))
        for x in (-wx, wx):
            groups["walls_h"].append(cylinder(f"rb_h2{k}{x}", r, 2 * wy, (x, 0, z), M["rebar"], verts=8, rot=(math.pi / 2, 0, 0)))
    rebar = []
    for gi, (g, objs) in enumerate(groups.items()):
        ob = lib.join(objs, f"Rebar_{g}")
        parent(ob, body)
        sec.add(ob, M["rebar"])
        t = E["rebar"] + gi * 0.16
        vis(ob, [(0, False), (t - 0.01, True)])
        drop_in(ob, t, height=3.5, dur=0.45, bounce=0.06)
        rebar.append(ob)

    # water volume (not parented: it stays when the shell lifts)
    water = box("Water", (1, 1, 1), (0, 0, OB), M["water"], origin="bottom")
    water.data.materials.append(M["water"])
    sec.add(water, M["water"])
    water.visible_shadow = False

    # hydrostatic relief valve (centre of floor)
    valve = empty("Valve", (-1.2, 0, -DEPTH), parent=None)
    parts = [cylinder("ValveBody", 0.17, 0.5, (0, 0, -0.25), M["white_plastic"], verts=32),
             cylinder("ValveRim", 0.21, 0.04, (0, 0, 0.0), M["steel"], verts=32),
             cylinder("ValveScreen", 0.15, 0.25, (0, 0, -0.55), M["gravel"], verts=24)]
    for p in parts:
        loc = tuple(p.location)
        parent(p, valve, keep=False)
        p.location = loc
        sec.add(p, p.data.materials[0])
    hinge = empty("ValveHinge", (-0.14, 0, 0.025))
    parent(hinge, valve, keep=False)
    hinge.location = (-0.14, 0, 0.025)
    flap = cylinder("ValveFlap", 0.135, 0.03, (0.14, 0, 0), M["brass"], verts=32)
    parent(flap, hinge, keep=False)
    flap.location = (0.14, 0, 0)
    vglow = torus("ValveGlow", 0.25, 0.02, (0, 0, 0.04), M["glow"], seg=48, ring=8)
    parent(vglow, valve, keep=False)
    vglow.location = (0, 0, 0.04)
    parent(valve, body)

    # skimmer (wall at +x, near +y corner)
    sk = empty("Skimmer", (IX - 0.01, 1.0, WL))
    sk_parts = [box("SkimmerFace", (0.06, 0.62, 0.36), (0, 0, 0), M["white_plastic"], bevel=0.02),
                box("SkimmerMouth", (0.07, 0.5, 0.24), (0.01, 0, -0.01), M["dark"]),
                box("SkimmerWeir", (0.03, 0.46, 0.18), (-0.03, 0, 0.01), M["white_plastic"], rot=(0, math.radians(-20), 0))]
    for p in sk_parts:
        loc, rot = tuple(p.location), tuple(p.rotation_euler)
        parent(p, sk, keep=False)
        p.location, p.rotation_euler = loc, rot
    skglow = torus("SkimmerGlow", 0.42, 0.02, (-0.05, 0, 0), M["glow"], rot=(0, math.pi / 2, 0), seg=48, ring=8)
    parent(skglow, sk, keep=False)
    skglow.location = (-0.05, 0, 0)
    skglow.rotation_euler = (0, math.pi / 2, 0)
    skglow.scale = (0.6, 1.0, 1.0)
    parent(sk, body)

    # main drain (deepest point)
    dr = empty("MainDrain", (2.2, 0, -DEPTH + 0.01))
    dparts = [cylinder("DrainPlate", 0.3, 0.03, (0, 0, 0), M["white_plastic"], verts=40)]
    for i in range(7):
        dparts.append(box(f"DrainSlot{i}", (0.42 - abs(i - 3) * 0.07, 0.035, 0.035), (0, -0.18 + i * 0.06, 0.012), M["dark"]))
    for p in dparts:
        loc = tuple(p.location)
        parent(p, dr, keep=False)
        p.location = loc
    drglow = torus("DrainGlow", 0.4, 0.025, (0, 0, 0.03), M["glow"], seg=48, ring=8)
    parent(drglow, dr, keep=False)
    drglow.location = (0, 0, 0.03)
    parent(dr, body)

    # return jets on the -x wall and the long walls (angled)
    jets = []
    for i, (x, y, rz) in enumerate(((-IX + 0.01, -1.2, 0.0), (-IX + 0.01, 1.2, 0.0), (-1.5, -IY + 0.01, math.pi / 2), (1.5, IY - 0.01, -math.pi / 2))):
        j = empty(f"Jet{i}", (x, y, -0.6))
        j.rotation_euler = (0, 0, rz)
        nb = cylinder(f"JetBase{i}", 0.08, 0.05, (0.025, 0, 0), M["white_plastic"], rot=(0, math.pi / 2, 0))
        ey = sphere(f"JetEye{i}", 0.05, (0.06, 0, 0), M["steel"], seg=16, rings=10)
        for p in (nb, ey):
            loc, rot = tuple(p.location), tuple(p.rotation_euler)
            parent(p, j, keep=False)
            p.location, p.rotation_euler = loc, rot
        parent(j, body)
        jets.append(j)

    return dict(body=body, shell=shell, rebar=rebar, water=water, valve=valve, flap_hinge=hinge,
                valve_glow=vglow, skimmer=sk, skimmer_glow=skglow, drain=dr, drain_glow=drglow, jets=jets)


def water_state(water, t, hx, hy, bottom, top):
    key(water, "location", t, (0, 0, bottom))
    key(water, "scale", t, (2 * hx, 2 * hy, max(top - bottom, 0.001)))


def water_cut(water, t, old, new):
    key(water, "location", t - 0.02, (0, 0, old[2]))
    key(water, "scale", t - 0.02, (2 * old[0], 2 * old[1], max(old[3] - old[2], 0.001)))
    water_state(water, t, *new)


# ============================================================== story animation
def animate_story(M, Y, P, sec, sun, sky):
    water = P["water"]
    body = P["body"]
    # ---------------- 1. digging + filling
    pit = (OX - 0.005, OY - 0.005)
    water_state(water, 0, pit[0], pit[1], OB + 0.005, OB + 0.006)
    vis(water, [(0, False), (E["fill"] - 0.05, True), (E["fix"], False), (E["holds"] - 0.05, True),
                (E["drain"] + 1.2, False), (E["valve_open"], True)])
    water_state(water, E["fill"], pit[0], pit[1], OB + 0.005, OB + 0.006)
    water_state(water, E["pool"] - 0.3, pit[0], pit[1], OB + 0.005, WL)
    # seeping away
    water_state(water, E["seep"], pit[0], pit[1], OB + 0.005, WL)
    water_state(water, E["collapse_end"], pit[0], pit[1], OB + 0.005, OB + 0.35)
    # shell era: refill inside the shell
    water_cut(water, E["holds"] - 0.05, (pit[0], pit[1], OB + 0.005, OB + 0.35), (IX - 0.005, IY - 0.005, -DEPTH + 0.002, -DEPTH + 0.004))
    water_state(water, E["holds"] + 1.0, IX - 0.005, IY - 0.005, -DEPTH + 0.002, WL)
    water_state(water, E["drain"], IX - 0.005, IY - 0.005, -DEPTH + 0.002, WL)
    water_state(water, E["drain"] + 1.15, IX - 0.005, IY - 0.005, -DEPTH + 0.002, -DEPTH + 0.004)
    # valve lets groundwater in -> small amount inside
    water_state(water, E["valve_open"], IX - 0.005, IY - 0.005, -DEPTH + 0.002, -DEPTH + 0.004)
    water_state(water, E["no_lift"] + 0.6, IX - 0.005, IY - 0.005, -DEPTH + 0.002, -DEPTH + 0.32)
    water_cut(water, E["week"] - 0.4, (IX - 0.005, IY - 0.005, -DEPTH + 0.002, -DEPTH + 0.32),
              (IX - 0.005, IY - 0.005, -DEPTH + 0.002, WL))

    # shovel strokes
    sh = Y["shovel"]
    t = E["dig"]
    strokes = 4
    span = (E["dig_end"] - E["dig"]) / strokes
    for i in range(strokes):
        x = 1.6 - i * 1.0
        key(sh, "location", t + i * span, (x, -0.6, 0.6))
        key(sh, "rotation_euler", t + i * span, (math.radians(-25), math.radians(15), 0))
        key(sh, "location", t + i * span + span * 0.45, (x + 0.2, -0.3, -0.25 - i * 0.35))
        key(sh, "rotation_euler", t + i * span + span * 0.45, (math.radians(-5), 0, 0))
        key(sh, "location", t + (i + 1) * span - 0.02, (x - 0.5, -0.9, 0.8))
        key(sh, "rotation_euler", t + (i + 1) * span - 0.02, (math.radians(-60), math.radians(-30), 0))
    key(sh, "location", E["dig_end"] + 0.3, (-4.8, -2.9, 0.75))
    key(sh, "rotation_euler", E["dig_end"] + 0.3, (math.radians(-12), math.radians(20), math.radians(30)))
    vis(sh, [(0, True), (E["next_day"] + 0.3, False)])
    # dirt thrown to a growing pile
    clump = particle_shape("tpl_clump", "chunk", M["dirt"], 1.0)
    emitter("DirtThrow", clump, E["dig"] + 0.1, E["dig_end"], rate=55, life=0.75,
            origin=(0.5, -0.5, 0.2), jitter=(1.6, 0.6, 0.1), direction=(-1.0, 0.45, 1.25), spread=0.25,
            speed=7.2, speed_var=0.2, gravity=(0, 0, -9.8), floor_z=0.05, size=0.09, spin=6, seed=3)
    pile = ico("DirtPile", 1.0, (-6.4, 1.2, -0.15), M["dirt"], sub=3, jitter=0.12, seed=4)
    pile.scale = (0.001, 0.001, 0.001)
    keys(pile, "scale", [(E["dig"], (0.001, 0.001, 0.001)), (E["dig_end"] + 0.5, (1.9, 1.5, 0.95))])
    # water pour from a hose
    hose = curve_path("Hose", [(-5.5, -3.2, 0.02), (-4.6, -2.2, 0.05), (-3.9, -1.6, 0.35), (-3.6, -1.2, 0.55)],
                      bevel=0.05, mat=M["pump_blue"])
    show_between(hose, E["fill"] - 0.2, E["next_day"] + 0.3)
    drop = particle_shape("tpl_drop", "drop", M["drop"], 1.0)
    emitter("PourStream", drop, E["fill"], E["pool"] - 0.3, rate=160, life=0.45,
            origin=(-3.6, -1.2, 0.55), direction=(0.8, 0.5, 0.2), spread=0.06, speed=3.0,
            speed_var=0.1, size=0.05, floor_z=OB, seed=5)
    # confetti for "مبروك"
    for i, c in enumerate(("confetti_a", "confetti_b", "confetti_c")):
        flake = particle_shape(f"tpl_conf{i}", "flake", M[c], 1.0)
        emitter(f"Confetti{i}", flake, E["congrats"], E["congrats"] + 0.35, rate=120, life=1.6,
                origin=(0, 0, 0.5), jitter=(3, 1.2, 0.2), direction=(0, 0, 1), spread=0.6, speed=6.5,
                gravity=(0, 0, -6), size=0.07, spin=8, drag=1.2, seed=10 + i)
        emitter(f"ConfettiEnd{i}", flake, E["final"] + 0.1, E["final"] + 0.6, rate=140, life=2.2,
                origin=(0, 0, 0.3), jitter=(3.5, 1.5, 0.2), direction=(0, 0, 1), spread=0.6, speed=7.5,
                gravity=(0, 0, -6), size=0.08, spin=8, drag=1.2, seed=20 + i)
    # rubber ring dropped into the new pool
    ring = empty("RubberRing", (1.2, -0.4, WL + 0.05))
    for k in range(8):
        seg = torus(f"RingSeg{k}", 0.42, 0.13, (0, 0, 0), M["ring_red" if k % 2 else "ring_white"],
                    seg=8, ring=14, arc=math.pi / 4 + 0.001)
        seg.rotation_euler = (0, 0, k * math.pi / 4)
        parent(seg, ring, keep=False)
    ring_drop = E["pool"]
    key(ring, "location", ring_drop - 0.01, (1.2, -0.4, 4.0))
    key(ring, "location", ring_drop + 0.35, (1.2, -0.4, WL + 0.02))
    for i in range(6):
        key(ring, "location", ring_drop + 0.5 + i * 0.3, (1.2 + i * 0.05, -0.4, WL + 0.04 + 0.03 * (-1) ** i))
    vis(ring, [(0, False), (ring_drop - 0.02, True), (E["next_day"] + 0.3, False), (E["final"] + 0.6, True)])
    key(ring, "location", E["final"] + 0.6, (-1.5, 0.5, 4.0))
    key(ring, "location", E["final"] + 1.0, (-1.5, 0.5, WL + 0.02))
    for i in range(8):
        key(ring, "location", E["final"] + 1.2 + i * 0.35, (-1.5 + i * 0.06, 0.5 + i * 0.03, WL + 0.04 + 0.025 * (-1) ** i))
    key(ring, "rotation_euler", E["final"] + 1.0, (0, 0, 0))
    key(ring, "rotation_euler", SP.DURATION, (0, 0, 1.2))
    splash = particle_shape("tpl_splash", "drop", M["drop"], 1.0)
    for nm, t0, loc in (("Splash1", ring_drop + 0.33, (1.2, -0.4, WL)), ("Splash2", E["final"] + 0.98, (-1.5, 0.5, WL)),
                        ("Splash3", E["boat"] + 0.05, (0, -2.6, -0.95))):
        emitter(nm, splash, t0, t0 + 0.12, rate=500, life=0.7, origin=loc, jitter=(0.3, 0.3, 0),
                direction=(0, 0, 1), spread=0.7, speed=3.0, size=0.045, floor_z=WL - 0.05, seed=hash(nm) % 99)

    # ---------------- 2. next day: seeping + collapsing walls
    sec.window(E["next_day"] + 0.35, E["fix"])
    seep = particle_shape("tpl_seep", "drop", M["drop"], 1.0)
    emitter("Seep", seep, E["seep"], E["collapse_end"], rate=90, life=1.5,
            origin=(0, -0.05, OB - 0.1), jitter=(OX, 0.03, 0.05), direction=(0, 0, -1), spread=0.25,
            speed=1.2, gravity=(0, 0, -0.3), size=0.05, seed=31)
    emitter("SeepSide", seep, E["seep"] + 0.3, E["collapse_end"], rate=50, life=1.4,
            origin=(OX + 0.1, -0.05, -1.0), jitter=(0.05, 0.03, 0.8), direction=(1, 0, -0.6), spread=0.25,
            speed=0.9, gravity=(0, 0, -0.3), size=0.045, seed=32)
    emitter("SeepSide2", seep, E["seep"] + 0.3, E["collapse_end"], rate=50, life=1.4,
            origin=(-OX - 0.1, -0.05, -1.0), jitter=(0.05, 0.03, 0.8), direction=(-1, 0, -0.6), spread=0.25,
            speed=0.9, gravity=(0, 0, -0.3), size=0.045, seed=33)
    # collapsing rim chunks
    chunks = []
    for i in range(18):
        side = i % 4
        u = RND.uniform(-0.85, 0.85)
        if side == 0:
            p0 = Vector((u * OX, OY - 0.15, -0.25))
        elif side == 1:
            p0 = Vector((u * OX, -OY + 0.15, -0.25))
        elif side == 2:
            p0 = Vector((OX - 0.15, u * OY, -0.25))
        else:
            p0 = Vector((-OX + 0.15, u * OY, -0.25))
        if p0.y < 0.1:
            p0.y = max(p0.y, 0.25)
        ch = ico(f"Chunk{i}", RND.uniform(0.3, 0.55), tuple(p0), M["mud"], sub=1, smooth=False, jitter=0.3, seed=i)
        t0 = E["collapse"] + RND.uniform(0.0, 0.9)
        inward = Vector((-p0.x * 0.25, -p0.y * 0.25 + 0.05, 0))
        land = p0 + inward + Vector((0, 0, OB + 0.55 - p0.z + RND.uniform(0, 0.4)))
        key(ch, "location", t0, tuple(p0))
        key(ch, "rotation_euler", t0, (0, 0, 0))
        key(ch, "location", t0 + 0.55, tuple(land))
        key(ch, "rotation_euler", t0 + 0.55, (RND.uniform(-2, 2), RND.uniform(-2, 2), RND.uniform(-1, 1)))
        vis(ch, [(0, False), (E["next_day"], True), (E["fix"], False)])
        chunks.append(ch)
    slumps = []
    for i in range(8):
        x = -OX + 0.6 + i * (2 * OX - 1.2) / 7
        s = sphere(f"Slump{i}", 1.0, (x, OY - 0.3, OB + 0.1), M["mud"], seg=16, rings=10)
        sc = (0.8, 0.6, 0.5)
        key(s, "scale", E["collapse"] + 0.2 + i * 0.07, (0.001, 0.001, 0.001))
        key(s, "scale", E["collapse"] + 0.9 + i * 0.07, sc)
        vis(s, [(0, False), (E["collapse"], True), (E["fix"], False)])
        slumps.append(s)
    M["water"].node_tree.nodes["green"].outputs[0].default_value = 0
    key_value(M["water"], "green", E["collapse"], 0.0)
    key_value(M["water"], "green", E["collapse_end"], 0.55)
    key_value(M["water"], "green", E["fix"] - 0.02, 0.55)
    key_value(M["water"], "green", E["fix"], 0.0)

    # ---------------- 3. rebar + shotcrete
    nozzle = empty("Nozzle", (-4.2, -1.2, 0.6))
    gun = cylinder("NozzleGun", 0.07, 0.8, (0, 0, 0), M["steel"], rot=(math.radians(-60), 0, 0))
    tip = cylinder("NozzleTip", 0.09, 0.2, (0, 0.35, -0.2), M["dark"], r2=0.05, rot=(math.radians(-60), 0, 0))
    hoseN = curve_path("ShotcreteHose", [(0, -0.35, 0.2), (0, -1.4, 0.9), (-0.4, -3.0, 0.6), (-1, -5.0, 0.2)],
                       bevel=0.06, mat=M["dark"])
    for p in (gun, tip, hoseN):
        loc, rot = tuple(p.location), tuple(p.rotation_euler)
        parent(p, nozzle, keep=False)
        p.location, p.rotation_euler = loc, rot
    t0, t1 = E["spray"], E["shell_done"]
    n = 10
    for i in range(n + 1):
        u = i / n
        x = -4.6 + 9.2 * u
        z = 0.2 if i % 2 == 0 else -1.2
        key(nozzle, "location", t0 + (t1 - t0) * u, (x, -1.2, z))
    vis(nozzle, [(0, False), (t0 - 0.3, True), (E["holds"], False)])
    spray = particle_shape("tpl_spray", "chunk", M["concrete"], 1.0)
    em = emitter("Spray", spray, t0, t1, rate=260, life=0.32, origin=(-4.6, -0.85, -0.2),
                 direction=(0, 1, -0.55), spread=0.22, speed=9.0, gravity=(0, 0, -4), size=0.04,
                 floor_z=OB + 0.2, seed=40)
    for i in range(n + 1):
        u = i / n
        x = -4.6 + 9.2 * u
        z = 0.2 if i % 2 == 0 else -1.2
        lib.key_emitter(em, "Origin", t0 + (t1 - t0) * u, (x, -0.85, z - 0.25))

    # ---------------- 4. emptied pool floats up on groundwater
    sec.window(E["drain"] - 0.1, E["solution"])
    gw = box("GroundWater", (30, 30, 1), (0, 0, -7.0), M["groundwater"], origin="bottom")
    gw.data.materials.append(M["groundwater"])
    sec.add(gw, M["groundwater"], offset=-0.03)
    gw.visible_shadow = False

    def gw_level(t, top):
        key(gw, "scale", t, (1, 1, max(top + 7.0, 0.01)))

    gw_level(0, -5.0)
    gw_level(E["ground_water"], -5.0)
    gw_level(E["push_up"], OB - 0.05)
    gw_level(E["lift"], OB - 0.05)
    gw_level(E["lift"] + 1.4, -0.95)
    gw_level(E["solution"] - 0.02, -0.95)
    gw_level(E["solution"], -5.0)
    gw_level(E["pressure"], -5.0)
    gw_level(E["valve_open"] - 0.1, OB - 0.08)
    gw_level(E["no_lift"] + 0.6, OB - 0.08)
    gw_level(E["week"] - 0.42, -5.0)
    vis(gw, [(0, False), (E["drain"], True), (E["week"] - 0.4, False)])
    # upward pressure arrows under the floor
    arrows = []
    for i, x in enumerate((-3.0, -1.0, 1.0, 3.0)):
        a = empty(f"PushArrow{i}", (x, -0.15, OB - 0.9))
        shaft = cylinder(f"PushShaft{i}", 0.07, 0.6, (0, 0, -0.3), M["arrow_up"], verts=16)
        head = cylinder(f"PushHead{i}", 0.17, 0.3, (0, 0, 0.12), M["arrow_up"], verts=16, r2=0.0)
        for p in (shaft, head):
            loc = tuple(p.location)
            parent(p, a, keep=False)
            p.location = loc
        arrows.append(a)
        t0 = E["push_up"] + i * 0.08
        a.scale = (1, 1, 1)
        vis(a, [(0, False), (t0, True), (E["lift"] + 1.2, False), (E["pressure"] + 0.1, True), (E["no_lift"] + 0.9, False)])
        for j in range(7):
            key(a, "location", t0 + j * 0.2, (x, -0.15, OB - 0.9 + (0.25 if j % 2 else 0)))
        key(a, "location", E["lift"], (x, -0.15, OB - 0.7))
        key(a, "location", E["lift"] + 1.2, (x, -0.15, -0.6))
        # second appearance: valve scene (pressure builds, arrows converge to the valve)
        key(a, "location", E["pressure"] + 0.09, (x * 0.5 - 1.2, -0.15, OB - 1.3))
        for j in range(6):
            key(a, "location", E["pressure"] + 0.2 + j * 0.2, (x * 0.35 - 1.2, -0.15, OB - 1.1 + (0.2 if j % 2 else 0)))
        key(a, "location", E["valve_open"], (x * 0.12 - 1.2, -0.15, OB - 0.7))
        key(a, "scale", E["valve_open"], (1, 1, 1))
        key(a, "scale", E["no_lift"] + 0.8, (0.3, 0.3, 0.3))
    # the lift and the boat rocking
    key(body, "location", E["lift"], (0, 0, 0))
    key(body, "location", E["lift"] + 1.4, (0, 0, 1.7))
    key(body, "rotation_euler", E["lift"], (0, 0, 0))
    key(body, "rotation_euler", E["lift"] + 1.4, (0, math.radians(2.5), 0))
    for i in range(int((E["solution"] - E["boat"]) / 0.18) + 1):
        tt = E["boat"] + i * 0.18
        key(body, "rotation_euler", tt, (math.radians(2.5 * (-1) ** i), math.radians(3.5 * (-1) ** (i + 1)), 0))
        key(body, "location", tt, (0, 0, 1.7 + 0.08 * (-1) ** i))
    hold(body, "location", E["solution"], tuple(body.location), (0, 0, 0))
    hold(body, "rotation_euler", E["solution"], tuple(body.rotation_euler), (0, 0, 0))
    # valve installation (drops into the floor) and opening
    sec.window(E["solution"], E["week"] - 0.4, slide=0.5, start=-3.0)
    valve = P["valve"]
    vloc = tuple(valve.location)
    vis(valve, [(0, False), (E["valve_in"] - 0.02, True)])
    key(valve, "location", E["valve_in"] - 0.01, (vloc[0], vloc[1], vloc[2] + 2.4))
    key(valve, "location", E["valve_in"] + 0.55, (vloc[0], vloc[1], vloc[2] - 0.02))
    key(valve, "location", E["valve_in"] + 0.7, vloc)
    for ch in [c for c in P["valve"].children_recursive if "Glow" not in c.name]:
        vis(ch, [(0, False), (E["valve_in"] - 0.02, True)])
    hinge = P["flap_hinge"]
    key(hinge, "rotation_euler", E["valve_open"] - 0.05, (0, 0, 0))
    key(hinge, "rotation_euler", E["valve_open"] + 0.35, (0, math.radians(-75), 0))
    key(hinge, "rotation_euler", E["no_lift"] + 1.5, (0, math.radians(-75), 0))
    key(hinge, "rotation_euler", E["no_lift"] + 2.0, (0, 0, 0))
    vg = P["valve_glow"]
    vis(vg, [(0, False), (E["valve_name"] - 0.1, True), (E["week"] - 0.4, False)])
    for i in range(8):
        key(vg, "scale", E["valve_name"] + i * 0.25, (1.0 + 0.25 * (i % 2),) * 3)
    bub = particle_shape("tpl_bubble", "sphere", M["drop"], 1.0)
    emitter("ValveJet", bub, E["valve_open"] + 0.15, E["no_lift"] + 1.4, rate=110, life=0.9,
            origin=(vloc[0], 0, -DEPTH + 0.05), jitter=(0.08, 0.03, 0), direction=(0, 0, 1), spread=0.35,
            speed=2.2, gravity=(0, 0, -1.5), size=0.035, seed=50)
    # pool tries to rise but stays down
    key(body, "location", E["no_lift"] - 0.2, (0, 0, 0))
    key(body, "location", E["no_lift"] + 0.05, (0, 0, 0.06))
    key(body, "location", E["no_lift"] + 0.3, (0, 0, 0))
    key(body, "location", E["no_lift"] + 0.45, (0, 0, 0.015))
    key(body, "location", E["no_lift"] + 0.6, (0, 0, 0))

    # ---------------- 5. a week in the sun: water turns green
    key(sun, "rotation_euler", E["week"] - 0.4, (math.radians(42), 0, math.radians(-28)))
    sweep = [(-75, 70), (-28, 42), (40, 70), (110, 20)]
    for i, (rz, rx) in enumerate(sweep):
        key(sun, "rotation_euler", E["week"] + i * 0.5, (math.radians(rx), 0, math.radians(rz)))
    key(sun, "rotation_euler", E["green"] + 0.4, (math.radians(42), 0, math.radians(-28)))
    key(sun.data, "energy", E["week"], 4.2)
    for i in range(4):
        key(sun.data, "energy", E["week"] + 0.25 + i * 0.5, 2.0 if i % 2 else 5.0)
    key(sun.data, "energy", E["green"] + 0.4, 4.2)
    key_value(M["water"], "green", E["green"] - 0.6, 0.0)
    key_value(M["water"], "green", E["green"] + 0.9, 1.0)
    key_value(M["water"], "green", E["clean"], 1.0)
    key_value(M["water"], "green", E["clean"] + 1.2, 0.0)
    key_value(M["shell"], "algae", E["green"] - 0.6, 0.0)
    key_value(M["shell"], "algae", E["green"] + 0.9, 1.0)
    key_value(M["shell"], "algae", E["clean"], 1.0)
    key_value(M["shell"], "algae", E["clean"] + 1.2, 0.0)
    algae_puff = particle_shape("tpl_algae", "puff", M["flow_dirty"], 1.0)
    emitter("AlgaeBloom", algae_puff, E["green"] - 0.3, E["suck"], rate=30, life=1.4,
            origin=(0, 0, -1.2), jitter=(3.6, 1.7, 0.7), direction=(0, 0, 1), spread=1, speed=0.12,
            gravity=(0, 0, 0), size=0.06, growth=0.8, seed=60)

    # ---------------- 6. leaves float, heavy debris sinks, skimmer + main drain
    leaves = []
    leaf_shape = []
    for k in range(2):
        cu = curve_path(f"tpl_leafcurve{k}", [(-0.15, 0, 0), (0, 0, 0.012), (0.15, 0, 0)], bevel=0)
        cu.data.extrude = 0.055
        cu.hide_render = True
        leaf_shape.append(cu)
    for i in range(12):
        lf = box(f"Leaf{i}", (0.26, 0.11, 0.012), (0, 0, 0), M["leaf" if i % 3 else "leaf2"], bevel=0.02)
        lf.rotation_euler = (0, 0, RND.uniform(0, 6.28))
        leaves.append(lf)
    t_l = E["leaves"]
    sk_pos = Vector((IX - 0.2, 1.0, WL + 0.01))
    for i, lf in enumerate(leaves):
        p_land = Vector((RND.uniform(-3.2, 2.8), RND.uniform(-1.5, 1.5), WL + 0.01))
        t_land = t_l - 0.3 + i * 0.08
        key(lf, "location", t_land - 1.0, tuple(p_land + Vector((RND.uniform(-1, 1), -0.6, 3.5))))
        key(lf, "rotation_euler", t_land - 1.0, (RND.uniform(-1, 1), RND.uniform(-1, 1), RND.uniform(0, 6)))
        key(lf, "location", t_land, tuple(p_land))
        key(lf, "rotation_euler", t_land, (0, 0, RND.uniform(0, 6)))
        for j in range(1, 8):
            key(lf, "location", t_land + j * 0.45, tuple(p_land + Vector((0.05 * j, 0.03 * math.sin(j), 0.01 * (-1) ** j))))
        t_go = E["skimmer_suck"] + i * 0.11
        key(lf, "location", t_go, tuple(p_land + Vector((0.35, 0.21, 0))))
        key(lf, "location", t_go + 0.8, tuple(sk_pos + Vector((-0.1, RND.uniform(-0.15, 0.15), 0))))
        key(lf, "scale", t_go + 0.6, (1, 1, 1))
        key(lf, "scale", t_go + 0.95, (0.001, 0.001, 0.001))
        vis(lf, [(0, False), (t_land - 1.05, True), (t_go + 1.0, False)])
    pebbles = []
    drain_pos = Vector((2.2, 0, -DEPTH + 0.06))
    for i in range(7):
        pb = ico(f"Pebble{i}", RND.uniform(0.06, 0.11), (0, 0, 0), M["pebble"], sub=2, jitter=0.25, seed=70 + i)
        x = RND.uniform(-2.5, 3.0)
        y = RND.uniform(-1.2, 1.2)
        t0 = E["sink"] + 0.2 + i * 0.12
        key(pb, "location", t0 - 0.6, (x, y - 0.5, 2.5))
        key(pb, "location", t0, (x, y, WL))
        key(pb, "location", t0 + 1.3, (x + 0.1, y, -DEPTH + 0.07))
        key(pb, "location", E["drain_suck"] + i * 0.1, (x + 0.1, y, -DEPTH + 0.07))
        key(pb, "location", E["drain_suck"] + 0.9 + i * 0.1, tuple(drain_pos + Vector((RND.uniform(-0.1, 0.1), RND.uniform(-0.1, 0.1), 0))))
        key(pb, "scale", E["drain_suck"] + 0.85 + i * 0.1, (1, 1, 1))
        key(pb, "scale", E["drain_suck"] + 1.05 + i * 0.1, (0.001, 0.001, 0.001))
        vis(pb, [(0, False), (t0 - 0.62, True), (E["jets"], False)])
        pebbles.append(pb)
    sinkb = particle_shape("tpl_sinkbubble", "sphere", M["drop"], 1.0)
    emitter("SinkBubbles", sinkb, E["sink"] + 0.3, E["sink"] + 1.3, rate=40, life=0.8,
            origin=(0, 0, -0.6), jitter=(2.5, 1.2, 0.4), direction=(0, 0, 1), spread=0.3, speed=0.8,
            gravity=(0, 0, 0.5), size=0.02, seed=71)
    sk = P["skimmer"]
    vis(sk, [(0, False), (E["skimmer"] - 0.02, True)])
    for ch in [c for c in sk.children_recursive if "Glow" not in c.name]:
        vis(ch, [(0, False), (E["skimmer"] - 0.02, True)])
    pop_in(sk, E["skimmer"], dur=0.4)
    skg = P["skimmer_glow"]
    vis(skg, [(0, False), (E["skimmer_name"] - 0.1, True), (E["drain_hole"], False)])
    for i in range(6):
        key(skg, "scale", E["skimmer_name"] + i * 0.15, (0.6 * (1.0 + 0.25 * (i % 2)), 1.0 + 0.25 * (i % 2), 1.0 + 0.25 * (i % 2)))
    dr = P["drain"]
    for ch in [dr] + [c for c in dr.children_recursive if "Glow" not in c.name]:
        vis(ch, [(0, False), (E["drain_hole"] - 0.02, True)])
    pop_in(dr, E["drain_hole"], dur=0.4)
    drg = P["drain_glow"]
    vis(drg, [(0, False), (E["drain_hole"] + 0.1, True), (E["jets"], False)])
    for i in range(8):
        key(drg, "scale", E["drain_hole"] + 0.2 + i * 0.2, (1.0 + 0.2 * (i % 2),) * 3)
    skflow = particle_shape("tpl_skflow", "sphere", M["flow"], 1.0)
    emitter("SkimmerPull", skflow, E["skimmer_suck"], E["skimmer_name"] + 0.8, rate=45, life=1.0,
            origin=(1.5, 0.6, WL + 0.02), jitter=(1.5, 1.0, 0), direction=(1, 0.2, 0), spread=0.15,
            speed=2.4, gravity=(0, 0, 0), size=0.025, seed=80)
    emitter("DrainPull", skflow, E["drain_suck"], E["jets"], rate=40, life=0.9,
            origin=(2.2, 0, -DEPTH + 0.7), jitter=(0.8, 0.8, 0.3), direction=(0, 0, -1), spread=0.2,
            speed=0.9, gravity=(0, 0, -0.5), floor_z=-DEPTH + 0.03, size=0.022, seed=81)

    # ---------------- 7. return jets drive a circulation
    for i, j in enumerate(P["jets"]):
        for ch in [j] + list(j.children_recursive):
            vis(ch, [(0, False), (E["jets"] + i * 0.12, True)])
        pop_in(j, E["jets"] + i * 0.12, dur=0.3)
    jet_shape = particle_shape("tpl_jet", "sphere", M["flow"], 1.0)
    jet_dirs = [((-IX + 0.1, -1.2, -0.6), (1, 0.5, 0)), ((-IX + 0.1, 1.2, -0.6), (1, -0.15, 0)),
                ((-1.5, -IY + 0.1, -0.6), (0.6, 1, 0)), ((1.5, IY - 0.1, -0.6), (-0.6, -1, 0))]
    # circulation: anticlockwise when viewed from above; jets angled along it
    jet_dirs = [((-IX + 0.1, -1.2, -0.6), (0.5, -1, 0)), ((-IX + 0.1, 1.2, -0.6), (1, 0.2, 0)),
                ((-1.5, -IY + 0.1, -0.6), (1, 0.45, 0)), ((1.5, IY - 0.1, -0.6), (-1, -0.45, 0))]
    for i, (o, d) in enumerate(jet_dirs):
        emitter(f"JetStream{i}", jet_shape, E["jets"] + 0.3 + i * 0.12, E["bacteria"] - 0.2, rate=70, life=0.9,
                origin=o, direction=d, spread=0.12, speed=3.2, gravity=(0, 0, 0), size=0.03, drag=1.0, seed=90 + i)
    circ = empty("CirculationArrows", (0, 0, WL + 0.08))
    for k in range(3):
        a0 = k * 2 * math.pi / 3
        arc = torus(f"CircArc{k}", 1.0, 0.04, (0, 0, 0), M["arrow"], seg=24, ring=8, arc=1.5)
        arc.rotation_euler = (0, 0, a0)
        head = cylinder(f"CircHead{k}", 0.12, 0.25, (0, 0, 0), M["arrow"], verts=16, r2=0.0)
        a1 = a0 + 1.5
        head.location = (math.cos(a1), math.sin(a1), 0)
        head.rotation_euler = (math.pi / 2, 0, a1 + math.pi)
        head.rotation_mode = "XYZ"
        for p in (arc, head):
            loc, rot = tuple(p.location), tuple(p.rotation_euler)
            parent(p, circ, keep=False)
            p.location, p.rotation_euler = loc, rot
    circ.scale = (3.0, 1.5, 1.0)
    for ch in [circ] + list(circ.children_recursive):
        vis(ch, [(0, False), (E["swirl"] - 0.1, True), (E["bacteria"] - 0.2, False)])
    pop_in(circ, E["swirl"], dur=0.4, final=(3.0, 1.5, 1.0))
    key(circ, "rotation_euler", E["swirl"], (0, 0, 0))
    key(circ, "rotation_euler", E["bacteria"], (0, 0, 2.6))
    fcs = circ.animation_data.action.fcurves
    for fc in fcs:
        if fc.data_path == "rotation_euler":
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    # floating debris carried around to the skimmer
    for i in range(10):
        lf = box(f"SwirlLeaf{i}", (0.24, 0.1, 0.012), (0, 0, 0), M["leaf2" if i % 2 else "leaf"], bevel=0.02)
        a0 = RND.uniform(0, 2 * math.pi)
        r0 = RND.uniform(0.55, 0.95)
        t_s = E["jets"]
        t_end = E["bacteria"] - 0.2
        steps = int((t_end - t_s) / 0.2)
        for s in range(steps + 1):
            tt = t_s + s * 0.2
            prog = max(0.0, (tt - E["swirl"]) / (t_end - E["swirl"]))
            ang = a0 + max(0.0, tt - E["swirl"]) * 1.15
            rr = r0
            pos = Vector((math.cos(ang) * 3.3 * rr, math.sin(ang) * 1.6 * rr, WL + 0.01))
            if tt > E["push_skimmer"] + i * 0.12:
                k2 = min(1.0, (tt - E["push_skimmer"] - i * 0.12) / 1.2)
                pos = pos.lerp(sk_pos, k2)
                if k2 >= 0.99:
                    lf.scale = (0.001, 0.001, 0.001)
                    lf.keyframe_insert("scale", frame=F(tt))
                    continue
            key(lf, "location", tt, tuple(pos))
            key(lf, "rotation_euler", tt, (0, 0, ang + 1.57))
            if prog >= 0:
                key(lf, "scale", tt, (1, 1, 1))
        vis(lf, [(0, False), (E["jets"], True), (E["bacteria"] - 0.2, False)])

    # ---------------- 10. smell: vapour from the water
    vap = particle_shape("tpl_vapor", "puff", M["vapor"], 1.0)
    emitter("Vapor", vap, E["smell"] - 0.1, E["not_chlorine"] + 0.2, rate=28, life=2.0,
            origin=(-2.0, 0, WL + 0.05), jitter=(2.5, 1.5, 0), direction=(0, 0, 1), spread=0.3, speed=0.6,
            gravity=(0, 0, 0.15), size=0.09, growth=1.3, seed=100)
    sweat = particle_shape("tpl_sweat", "sphere", M["flow_dirty"], 1.0)
    emitter("Organics", sweat, E["smell"] - 0.1, E["not_chlorine"] + 0.2, rate=40, life=1.6,
            origin=(-2.0, 0, WL - 0.3), jitter=(2.5, 1.5, 0.2), direction=(0, 0, 1), spread=0.6, speed=0.2,
            gravity=(0, 0, 0.1), size=0.03, seed=101)

    # ---------------- 11. finishing: tiles, coping, ladder, diving board
    key_value(M["shell"], "tile_front", 0, -6.0)
    key_value(M["shell"], "tile_front", E["tiles"], -4.6)
    key_value(M["shell"], "tile_front", E["tiles"] + 0.75, 4.8)
    coping = []
    cw = 0.55
    cid = 0
    for side, (y0, horiz) in enumerate(((OY + 0.05, True), (-OY - 0.05, True), (OX + 0.05, False), (-OX - 0.05, False))):
        L = 2 * OX + 0.6 if horiz else 2 * OY - 0.5
        nseg = int(L / cw)
        for k in range(nseg):
            c = -L / 2 + (k + 0.5) * L / nseg
            loc = (c, y0, 0.0) if horiz else (y0, c, 0.0)
            sz = (L / nseg - 0.02, 0.6, 0.08) if horiz else (0.6, L / nseg - 0.02, 0.08)
            b = box(f"Coping{cid}", sz, loc, M["tile_coping"], bevel=0.015, origin="bottom")
            tt = E["tiles"] + (cid % 22) * 0.03
            vis(b, [(0, False), (tt - 0.01, True)])
            drop_in(b, tt, height=1.2, dur=0.3, bounce=0.03)
            coping.append(b)
            cid += 1
    lad = empty("Ladder", (-2.6, IY - 0.05, 0.0))
    for s in (-0.28, 0.28):
        pts = [(s, 0.55, 0.05), (s, 0.55, 0.85), (s, 0.25, 1.0), (s, -0.05, 0.85), (s, -0.12, 0.1), (s, -0.12, -1.3)]
        rail = curve_path(f"LadderRail{s}", smooth_path_points(pts, 0.18), bevel=0.03, mat=M["chrome"])
        parent(rail, lad, keep=False)
    for k in range(3):
        st = box(f"LadderStep{k}", (0.6, 0.12, 0.04), (0, -0.2, -0.2 - k * 0.38), M["steel"], bevel=0.01)
        parent(st, lad, keep=False)
        st.location = (0, -0.2, -0.2 - k * 0.38)
    lad_parts = [lad] + list(lad.children_recursive)
    for p in lad_parts:
        vis(p, [(0, False), (E["ladder"] - 0.01, True)])
    drop_in(lad, E["ladder"], height=2.5, dur=0.4, bounce=0.05)
    board_root = empty("DivingBoard", (-OX - 0.6, 0.0, 0.08))
    base = box("BoardBase", (0.7, 0.6, 0.35), (-0.4, 0, 0), M["board_blue"], bevel=0.05, origin="bottom")
    parent(base, board_root, keep=False)
    base.location = (-0.4, 0, 0)
    pivot = empty("BoardPivot", (0, 0, 0.35))
    parent(pivot, board_root, keep=False)
    pivot.location = (-0.1, 0, 0.38)
    plank = box("BoardPlank", (2.6, 0.5, 0.06), (1.3, 0, 0.03), M["board"], bevel=0.02)
    parent(plank, pivot, keep=False)
    plank.location = (1.3, 0, 0.03)
    for p in (board_root, base, pivot, plank):
        vis(p, [(0, False), (E["board"] - 0.01, True)])
    drop_in(board_root, E["board"], height=2.0, dur=0.35, bounce=0.0)
    damped_rotation(pivot, 1, E["board"] + 0.35, 1.6, math.radians(7), 3.0)
    # loungers + umbrella for the final shot
    props = []
    for i, (x, y) in enumerate(((-2.2, -OY - 1.6), (0.2, -OY - 1.6))):
        lo = empty(f"Lounger{i}", (x, y, 0))
        seat = box(f"LoungerSeat{i}", (1.8, 0.7, 0.1), (0, 0, 0.35), M["lounger"], bevel=0.03)
        backr = box(f"LoungerBack{i}", (0.7, 0.7, 0.1), (-1.05, 0, 0.6), M["lounger"], bevel=0.03, rot=(0, math.radians(-50), 0))
        cush = box(f"LoungerCushion{i}", (1.7, 0.62, 0.07), (0.05, 0, 0.44), M["fabric"], bevel=0.03)
        legs = [cylinder(f"LoungerLeg{i}{k}", 0.025, 0.35, (lx, ly, 0), M["chrome"], verts=8, origin="bottom")
                for k, (lx, ly) in enumerate(((-0.8, -0.3), (-0.8, 0.3), (0.8, -0.3), (0.8, 0.3)))]
        for p in [seat, backr, cush] + legs:
            loc, rot = tuple(p.location), tuple(p.rotation_euler)
            parent(p, lo, keep=False)
            p.location, p.rotation_euler = loc, rot
        lo.rotation_euler = (0, 0, math.radians(90))
        props.append(lo)
    umb = empty("Umbrella", (1.9, -OY - 1.7, 0))
    pole = cylinder("UmbPole", 0.03, 2.4, (0, 0, 0), M["wood"], verts=10, origin="bottom")
    canopy = cylinder("UmbCanopy", 1.3, 0.45, (0, 0, 2.2), M["fabric2"], verts=10, r2=0.05, origin="bottom", smooth=False)
    ubase = cylinder("UmbBase", 0.25, 0.1, (0, 0, 0), M["dark"], verts=16, origin="bottom")
    for p in (pole, canopy, ubase):
        loc = tuple(p.location)
        parent(p, umb, keep=False)
        p.location = loc
    props.append(umb)
    for i, pr in enumerate(props):
        for p in [pr] + list(pr.children_recursive):
            vis(p, [(0, False), (E["final"] + 0.05 + i * 0.12, True)])
        pop_in(pr, E["final"] + 0.1 + i * 0.12, dur=0.4)
    # golden late-afternoon light for the finale
    key(sun, "rotation_euler", E["final"], (math.radians(42), 0, math.radians(-28)))
    key(sun, "rotation_euler", SP.DURATION, (math.radians(62), 0, math.radians(-40)))
    key(sun.data, "color", E["final"], (1.0, 0.96, 0.9))
    key(sun.data, "color", E["final"] + 1.5, (1.0, 0.82, 0.62))
    return dict(chunks=chunks, slumps=slumps, gw=gw, arrows=arrows, leaves=leaves, pebbles=pebbles,
                coping=coping, ladder=lad, board=board_root, props=props, pile=pile, hose=hose)


# ============================================================== equipment pad
def build_equipment(M):
    use_collection(collection("Equipment"))
    t_on = E["pump"]
    pad = box("Pad", (3.4, 2.8, 0.15), (8.2, 0.4, 0), M["concrete"], bevel=0.03, origin="bottom")
    # pump: motor + volute + strainer pot
    pump = empty("Pump", (7.3, 0.9, 0.15))
    parts = [cylinder("PumpMotor", 0.24, 0.6, (-0.35, 0, 0.3), M["pump_blue"], rot=(0, math.pi / 2, 0)),
             cylinder("PumpFanCover", 0.25, 0.08, (-0.68, 0, 0.3), M["dark"], rot=(0, math.pi / 2, 0)),
             cylinder("PumpVolute", 0.27, 0.22, (0.05, 0, 0.3), M["white_plastic"], rot=(0, math.pi / 2, 0)),
             cylinder("PumpPot", 0.2, 0.5, (0.42, 0, 0.25), M["white_plastic"], origin="center"),
             cylinder("PumpLid", 0.22, 0.06, (0.42, 0, 0.53), M["glass"], verts=32),
             box("PumpFoot", (1.2, 0.4, 0.06), (0, 0, 0.0), M["dark"], origin="bottom")]
    for i in range(8):
        a = i * math.pi / 4
        parts.append(box(f"PumpFin{i}", (0.5, 0.02, 0.05), (-0.35, math.cos(a) * 0.245, 0.3 + math.sin(a) * 0.245),
                         M["pump_blue"], rot=(a, 0, 0)))
    for p in parts:
        loc, rot = tuple(p.location), tuple(p.rotation_euler)
        parent(p, pump, keep=False)
        p.location, p.rotation_euler = loc, rot
    # sand filter tank with cutaway interior
    filt = empty("Filter", (8.9, 0.1, 0.15))
    tank_mat = M["glass_tank"]
    tank = cylinder("TankWall", 0.55, 1.2, (0, 0, 0.7), tank_mat, verts=48)
    dome = sphere("TankDome", 0.55, (0, 0, 1.3), tank_mat, seg=48, rings=24, scale=(1, 1, 0.55))
    bottom = sphere("TankBottom", 0.55, (0, 0, 0.1), tank_mat, seg=48, rings=24, scale=(1, 1, 0.3))
    valve_top = cylinder("MultiportValve", 0.2, 0.22, (0, 0, 1.6), M["white_plastic"], verts=24)
    gauge = cylinder("Gauge", 0.06, 0.03, (0.12, -0.12, 1.75), M["steel"], rot=(math.radians(50), 0, 0))
    handle = box("ValveHandle", (0.35, 0.06, 0.04), (0, 0, 1.75), M["dark"])
    legs = cylinder("TankStand", 0.45, 0.12, (0, 0, 0.0), M["dark"], verts=24, origin="bottom")
    inside = [cylinder("TankGravel", 0.5, 0.25, (0, 0, 0.25), M["gravel"], verts=40),
              cylinder("TankSand", 0.5, 0.65, (0, 0, 0.7), M["sand"], verts=40),
              cylinder("TankWaterIn", 0.5, 0.55, (0, 0, 1.3), M["water"], verts=40),
              cylinder("TankStandpipe", 0.04, 1.3, (0, 0, 0.85), M["white_plastic"], verts=12)]
    for k in range(6):
        a = k * math.pi / 3
        inside.append(cylinder(f"Lateral{k}", 0.025, 0.4, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.2), M["white_plastic"],
                               verts=8, rot=(0, math.pi / 2, a)))
    for p in [tank, dome, bottom, valve_top, gauge, handle, legs] + inside:
        loc, rot, sc = tuple(p.location), tuple(p.rotation_euler), tuple(p.scale)
        parent(p, filt, keep=False)
        p.location, p.rotation_euler, p.scale = loc, rot, sc
    # tank wall fades to reveal the sand bed
    bsdf = tank_mat.node_tree.nodes["Principled BSDF"]
    lib.set_blend(tank_mat)
    bsdf.inputs["Alpha"].default_value = 1.0
    bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=F(E["filter"]))
    bsdf.inputs["Alpha"].default_value = 0.12
    bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=F(E["filter"] + 0.6))
    bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=F(E["leaves"] - 0.3))
    bsdf.inputs["Alpha"].default_value = 1.0
    bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=F(E["leaves"] - 0.2))
    # trapped dirt accumulating on top of the sand
    specks = []
    for i in range(40):
        a = RND.uniform(0, 2 * math.pi)
        r = math.sqrt(RND.uniform(0, 1)) * 0.45
        s = ico(f"Speck{i}", RND.uniform(0.018, 0.035), (math.cos(a) * r, math.sin(a) * r, 1.03 + RND.uniform(0, 0.02)),
                M["grime"], sub=1, jitter=0.3, seed=i)
        loc = tuple(s.location)
        parent(s, filt, keep=False)
        s.location = loc
        t0 = E["sand_trap"] + i * 0.03
        key(s, "scale", t0 - 0.01, (0.001,) * 3)
        key(s, "scale", t0 + 0.2, (1, 1, 1))
        specks.append(s)
    # plumbing (rounded bends), above-ground parts + where they dive underground
    pipes = {}
    pipes["suction"] = smooth_path_points([(4.4, 1.0, -0.6), (6.2, 1.0, -0.6), (6.2, 1.0, 0.45), (7.9, 0.9, 0.45)], 0.25)
    pipes["to_filter"] = smooth_path_points([(7.35, 0.9, 0.45), (7.35, 0.9, 1.0), (8.4, 0.5, 1.0), (8.4, 0.1, 1.75), (8.75, 0.1, 1.75)], 0.18)
    pipes["return"] = smooth_path_points([(9.05, 0.1, 1.75), (9.6, 0.1, 1.75), (9.6, -0.6, 1.0), (9.6, -0.9, 0.3), (6.2, -0.9, 0.3),
                                          (6.2, -0.9, -0.6), (-IX - 0.3, -0.9, -0.6)], 0.25)
    pipe_obs = []
    for nm, pts in pipes.items():
        po = curve_path(f"Pipe_{nm}", pts, bevel=0.065, mat=M["pvc"])
        pipe_obs.append(po)
    # flow beads along the plumbing
    flow_items = []
    for nm, dirty in (("suction", True), ("to_filter", True), ("return", False)):
        path = bpy.data.objects[f"Pipe_{nm}"]
        for k in range(14):
            b = sphere(f"Flow_{nm}{k}", 0.075, (0, 0, 0), M["flow_dirty" if dirty else "flow"], seg=12, rings=8)
            b.scale = (1.6, 1, 1)
            follow_path(b, path, E["suck"], 2.2, offset0=k / 14)
            t_show = E["suck"] if nm != "return" else E["clean"] - 0.3
            vis(b, [(0, False), (t_show, True), (E["leaves"] - 0.3, False)])
            flow_items.append(b)
    eq = [pad, pump, filt] + parts + [tank, dome, bottom, valve_top, gauge, handle, legs] + inside + specks + pipe_obs
    for o in eq:
        vis(o, [(0, False), (t_on - 0.4, True)])
    pop_in(pump, t_on, dur=0.4)
    pop_in(filt, t_on + 0.25, dur=0.45)
    for i, po in enumerate(pipe_obs):
        po.data.bevel_factor_mapping_end = "SPLINE"
        po.data.bevel_factor_end = 0.0
        po.data.keyframe_insert("bevel_factor_end", frame=F(t_on + 0.3 + i * 0.25))
        po.data.bevel_factor_end = 1.0
        po.data.keyframe_insert("bevel_factor_end", frame=F(t_on + 0.9 + i * 0.25))
    return dict(pad=pad, pump=pump, filter=filt)


# ============================================================== macro sets
def build_macro(M):
    use_collection(collection("MacroSand"))
    C = Vector((200, 0, 0))
    bd = sphere("MacroBackdrop", 25, tuple(C), M["backdrop_macro"], seg=48, rings=24)
    bd.visible_shadow = False
    rnd = random.Random(11)
    grains = []
    for i in range(70):
        p = C + Vector((rnd.uniform(-2.3, 2.3), rnd.uniform(-0.2, 1.8), rnd.uniform(-2.6, 0.6)))
        g = ico(f"Grain{i}", rnd.uniform(0.32, 0.55), tuple(p), M["sand_macro"], sub=3, jitter=0.0, seed=200 + i)
        g.scale = (rnd.uniform(0.8, 1.2), rnd.uniform(0.8, 1.2), rnd.uniform(0.7, 1.0))
        g.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
        grains.append(g)
    # dirt particles trapped on top of the grains
    for i in range(14):
        p = C + Vector((rnd.uniform(-2.0, 2.0), rnd.uniform(-0.3, 0.6), rnd.uniform(1.6, 2.0)))
        d = ico(f"MacroDirt{i}", rnd.uniform(0.12, 0.2), tuple(p), M["grime"], sub=1, jitter=0.35, seed=300 + i)
        land = p - Vector((0, 0, rnd.uniform(0.9, 1.2)))
        key(d, "location", E["bacteria"] - 0.3, tuple(p + Vector((0, 0, 1.4))))
        key(d, "location", E["bacteria"] + 0.7 + i * 0.05, tuple(land))
    # bacteria wiggle down through the gaps
    bacteria = []
    gaps = [(-1.6, -0.45), (-0.6, -0.5), (0.4, -0.45), (1.3, -0.5), (-1.1, -0.4), (0.9, -0.45), (0.0, -0.6), (1.9, -0.4)]
    for i, (gx, gy) in enumerate(gaps):
        b = empty(f"Bacterium{i}", tuple(C))
        cap = sphere(f"BactBody{i}", 0.09, (0, 0, 0), M["bacteria"], seg=16, rings=10, scale=(2.4, 1, 1))
        parent(cap, b, keep=False)
        for f_ in range(3):
            fl = cylinder(f"BactFlag{i}{f_}", 0.008, 0.25, (-0.3, 0, -0.03 + 0.03 * f_), M["bacteria"], verts=6,
                          rot=(0, math.pi / 2, 0.3 * (f_ - 1)))
            parent(fl, b, keep=False)
            fl.location = (-0.3, 0, -0.03 + 0.03 * f_)
            fl.rotation_euler = (0, math.pi / 2, 0.3 * (f_ - 1))
        t0 = E["bacteria"] - 0.2 + i * 0.12
        t1 = E["chlorine"]
        steps = int((t1 - t0) / 0.15)
        z0 = 2.4
        for s in range(steps + 1):
            u = s / max(steps, 1)
            pos = C + Vector((gx + 0.12 * math.sin(s * 1.7 + i), gy, z0 - u * 3.6))
            key(b, "location", t0 + s * 0.15, tuple(pos))
            key(b, "rotation_euler", t0 + s * 0.15, (0.3 * math.sin(s + i), math.radians(-70) + 0.3 * math.sin(s * 1.3), 0.4 * math.cos(s)))
        t_kill = E["kill"] + i * 0.06
        key(b, "scale", t_kill, (1, 1, 1))
        key(b, "scale", t_kill + 0.12, (1.4, 1.4, 1.4))
        key(b, "scale", t_kill + 0.4, (0.001, 0.001, 0.001))
        bacteria.append(b)
    flash = particle_shape("tpl_flash", "sphere", M["flash"], 1.0)
    for i, b in enumerate(bacteria):
        gx, gy = gaps[i]
        emitter(f"KillPop{i}", flash, E["kill"] + i * 0.06 + 0.1, E["kill"] + i * 0.06 + 0.2, rate=80, life=0.35,
                origin=tuple(C + Vector((gx, gy, 2.4 - 3.6 * 0.85))), direction=(0, 0, 1), spread=1.0, speed=1.2,
                gravity=(0, 0, 0), size=0.03, seed=400 + i)
    chl = particle_shape("tpl_chlorine", "drop", M["chlorine"], 1.0)
    emitter("ChlorineRain", chl, E["chlorine"], E["kill"] + 0.9, rate=90, life=1.2, origin=tuple(C + Vector((0, -0.5, 3.0))),
            jitter=(2.4, 0.4, 0.2), direction=(0, 0, -1), spread=0.1, speed=3.0, gravity=(0, 0, -2), size=0.05, seed=410)
    for nm, loc, en in (("MacroKey", (196, -6, 6), 900), ("MacroRim", (204, 4, 3), 600)):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy = en
        ld.size = 4
        lo = bpy.data.objects.new(nm, ld)
        lib.link(lo)
        lo.location = loc
        lo.rotation_euler = look_at_rot(loc, tuple(C))

    use_collection(collection("MacroMolecule"))
    C2 = Vector((300, 0, 0.5))
    bd2 = sphere("MolBackdrop", 25, tuple(C2), M["backdrop_mol"], seg=48, rings=24)
    bd2.visible_shadow = False

    def atom(name, mat, r, loc, par):
        a = sphere(name, r, loc, mat, seg=24, rings=16)
        parent(a, par, keep=False)
        a.location = loc
        return a

    def bond(name, a, b, par):
        a, b = Vector(a), Vector(b)
        d = b - a
        c = cylinder(name, 0.06, d.length, tuple((a + b) / 2), M["bond"], verts=12)
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        rot = tuple(c.rotation_euler)
        loc = tuple(c.location)
        parent(c, par, keep=False)
        c.location, c.rotation_euler = loc, rot

    cl2 = empty("Cl2", tuple(C2 + Vector((-1.0, 0, 0.3))))
    atom("Cl_a", M["atom_cl"], 0.42, (-0.38, 0, 0), cl2)
    atom("Cl_b", M["atom_cl"], 0.42, (0.38, 0, 0), cl2)
    bond("Cl_bond", (-0.38, 0, 0), (0.38, 0, 0), cl2)
    urea = empty("Urea", tuple(C2 + Vector((3.2, 0, 0.0))))
    atom("U_C", M["atom_c"], 0.3, (0, 0, 0), urea)
    atom("U_O", M["atom_o"], 0.3, (0, 0, 0.58), urea)
    for s in (-1, 1):
        atom(f"U_N{s}", M["atom_n"], 0.3, (0.55 * s, 0, -0.32), urea)
        bond(f"U_bN{s}", (0, 0, 0), (0.55 * s, 0, -0.32), urea)
        for h in (-1, 1):
            hp = (0.55 * s + 0.35 * s, 0.25 * h, -0.62)
            atom(f"U_H{s}{h}", M["atom_h"], 0.17, hp, urea)
            bond(f"U_bH{s}{h}", (0.55 * s, 0, -0.32), hp, urea)
    bond("U_bO", (0, 0, 0), (0, 0, 0.58), urea)
    chloramine = empty("Chloramine", tuple(C2 + Vector((0.6, 0, 0.1))))
    atom("NC_N", M["atom_n"], 0.32, (0, 0, 0), chloramine)
    atom("NC_Cl", M["atom_cl"], 0.42, (-0.68, 0, 0.1), chloramine)
    bond("NC_b1", (0, 0, 0), (-0.68, 0, 0.1), chloramine)
    for h in (-1, 1):
        hp = (0.3, 0.32 * h, -0.3)
        atom(f"NC_H{h}", M["atom_h"], 0.17, hp, chloramine)
        bond(f"NC_bH{h}", (0, 0, 0), hp, chloramine)
    cross = empty("NotThisCross", tuple(C2 + Vector((-1.0, -0.7, 0.3))))
    for k, a in enumerate((math.radians(45), math.radians(-45))):
        bar = box(f"CrossBar{k}", (1.6, 0.14, 0.14), (0, 0, 0), M["cross"], bevel=0.04, rot=(0, a, 0))
        parent(bar, cross, keep=False)
        bar.rotation_euler = (0, a, 0)
    # timeline of the molecule story
    t_nc = E["not_chlorine"]
    pop_in(cl2, t_nc - 0.05, dur=0.4)
    for i in range(10):
        key(cl2, "rotation_euler", t_nc + i * 0.3, (0, 0.15 * math.sin(i), 0.3 * i))
    vis(cross, [(0, False), (t_nc + 0.6, True), (E["reaction"] + 0.3, False)])
    for ch in cross.children:
        vis(ch, [(0, False), (t_nc + 0.6, True), (E["reaction"] + 0.3, False)])
    pop_in(cross, t_nc + 0.6, dur=0.3)
    damped_rotation(cross, 1, t_nc + 0.9, 0.8, math.radians(12), 3)
    key(urea, "location", E["reaction"] - 0.6, tuple(C2 + Vector((3.2, 0, 0.0))))
    key(urea, "location", E["reaction"] + 0.4, tuple(C2 + Vector((0.4, 0, 0.2))))
    key(urea, "rotation_euler", E["reaction"] - 0.6, (0, 0, 0))
    key(urea, "rotation_euler", E["reaction"] + 0.4, (0.5, 0.8, 1.2))
    vis(urea, [(0, False), (E["reaction"] - 0.62, True), (E["sweat"] + 0.15, False)])
    for ch in urea.children:
        vis(ch, [(0, False), (E["reaction"] - 0.62, True), (E["sweat"] + 0.15, False)])
    key(cl2, "location", E["reaction"] - 0.2, tuple(C2 + Vector((-1.0, 0, 0.3))))
    key(cl2, "location", E["reaction"] + 0.4, tuple(C2 + Vector((-0.2, 0, 0.25))))
    vis(cl2, [(0, False), (t_nc - 0.07, True), (E["sweat"] + 0.15, False)])
    for ch in cl2.children:
        vis(ch, [(0, False), (t_nc - 0.07, True), (E["sweat"] + 0.15, False)])
    for p in [chloramine] + list(chloramine.children):
        vis(p, [(0, False), (E["sweat"] + 0.12, True)])
    pop_in(chloramine, E["sweat"] + 0.12, dur=0.35)
    key(chloramine, "location", E["sweat"] + 0.5, tuple(C2 + Vector((0.2, 0, 0.1))))
    key(chloramine, "location", E["finish"], tuple(C2 + Vector((0.0, 0, 1.6))))
    key(chloramine, "rotation_euler", E["sweat"] + 0.5, (0, 0, 0))
    key(chloramine, "rotation_euler", E["finish"], (0.4, 0.2, 2.0))
    fl = particle_shape("tpl_reactflash", "sphere", M["flash"], 1.0)
    emitter("ReactionFlash", fl, E["sweat"] + 0.05, E["sweat"] + 0.2, rate=200, life=0.5,
            origin=tuple(C2 + Vector((0.2, 0, 0.2))), direction=(0, 0, 1), spread=1.0, speed=2.2,
            gravity=(0, 0, 0), size=0.05, seed=500)
    vp = particle_shape("tpl_vapor2", "puff", M["vapor"], 1.0)
    emitter("ReactionVapor", vp, E["sweat"] + 0.3, E["finish"], rate=14, life=1.8,
            origin=tuple(C2 + Vector((0.2, 0, 0.8))), jitter=(0.4, 0.2, 0.1), direction=(0, 0, 1),
            spread=0.4, speed=0.8, gravity=(0, 0, 0), size=0.15, growth=1.4, seed=501)
    for nm, loc, en in (("MolKey", (296, -6, 5), 700), ("MolRim", (305, 3, 3), 500)):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy = en
        ld.size = 4
        lo = bpy.data.objects.new(nm, ld)
        lib.link(lo)
        lo.location = loc
        lo.rotation_euler = look_at_rot(loc, tuple(C2))


def look_at_rot(src, dst):
    return lib.look_at_rot(src, dst)


# ============================================================== cameras
def build_cameras():
    use_collection(collection("Cameras"))
    S = dict((n, t) for n, t in SP.SHOTS)
    names = [n for n, _ in SP.SHOTS]
    ends = {n: (SP.SHOTS[i + 1][1] if i + 1 < len(SP.SHOTS) else SP.DURATION) for i, n in enumerate(names)}
    plans = {
        "cam_yard": lambda a, b: [(a, (1.5, -12.0, 10.0), (0, 0.3, -1.0), 24), (E["dig_end"], (1.2, -9.5, 8.0), (-0.5, 0, -1.2), 24),
                                  (E["pool"] - 0.4, (0.5, -8.5, 6.5), (0, 0.2, -0.8), 24), (b, (0.0, -7.6, 5.2), (0.3, 0.2, -0.5), 25)],
        "cam_section_seep": lambda a, b: [(a, (0.4, -13.0, 0.6), (0, 0, -2.6), 26), (E["collapse"], (0.2, -12.0, 0.4), (0, 0, -2.4), 26),
                                          (b, (0.0, -11.4, 0.3), (0, 0, -2.2), 27)],
        "cam_rebar": lambda a, b: [(a, (6.0, -6.5, 7.5), (0, 0, -1.6), 22), (b, (4.2, -5.6, 6.4), (0, 0.2, -1.6), 22)],
        "cam_spray": lambda a, b: [(a, (-4.2, -5.2, 2.4), (-3.0, 1.0, -1.2), 24), (E["shell_done"] - 0.6, (3.4, -5.2, 2.4), (3.0, 1.0, -1.2), 24),
                                   (b, (4.4, -5.8, 3.4), (1.5, 0.6, -1.2), 24)],
        "cam_full_pool": lambda a, b: [(a, (-6.4, -4.6, 2.6), (0, 0.4, -1.2), 24), (b, (-4.8, -5.8, 2.8), (0.5, 0.4, -1.0), 24)],
        "cam_section_lift": lambda a, b: [(a, (0.0, -13.0, 0.8), (0, 0, -2.4), 26), (E["lift"], (0.0, -13.4, 1.0), (0, 0, -2.0), 26),
                                          (E["boat"], (0.4, -12.8, 1.8), (0, 0, -1.0), 26), (b, (0.6, -12.4, 2.0), (0, 0, -0.9), 26)],
        "cam_valve": lambda a, b: [(a, (-1.2, -8.0, 0.8), (-1.2, 0, -2.0), 26), (E["valve_in"] + 0.8, (-1.0, -5.0, -1.2), (-1.2, 0, -2.4), 30),
                                   (E["pressure"], (-1.0, -7.0, -1.6), (-1.2, 0, -3.0), 28), (E["no_lift"], (-0.5, -10.0, 0.2), (-0.5, 0, -1.8), 26),
                                   (E["valve_name"], (-0.7, -3.2, -1.4), (-1.2, 0.0, -2.15), 34), (b, (-1.8, -2.9, -1.3), (-1.2, 0.0, -2.1), 36)],
        "cam_sun_week": lambda a, b: [(a, (-7.0, -9.0, 9.0), (0, 0.5, -0.8), 24), (b, (-5.0, -8.6, 6.8), (0.4, 0.5, -0.8), 24)],
        "cam_equipment": lambda a, b: [(a, (12.0, -6.0, 4.2), (7.6, 0.5, 0.5), 24), (b, (11.2, -4.8, 3.2), (8.0, 0.4, 0.6), 26)],
        "cam_filter_cut": lambda a, b: [(a, (10.4, -2.9, 2.5), (8.9, 0.1, 1.0), 32), (E["clean"], (9.8, -3.0, 2.2), (8.8, 0.1, 0.95), 34),
                                        (b, (8.2, -3.2, 2.5), (8.6, 0.2, 0.9), 32)],
        "cam_debris": lambda a, b: [(a, (-2.5, -5.6, 3.0), (0.0, 0.2, -0.8), 24), (E["sink"] + 0.6, (-1.0, -5.0, 2.4), (0.5, 0.0, -1.2), 24),
                                    (E["skimmer"], (1.4, -3.8, 1.6), (3.8, 0.9, -0.3), 28), (b, (2.2, -3.2, 1.3), (4.0, 0.9, -0.2), 30)],
        "cam_drain": lambda a, b: [(a, (4.0, -2.9, 1.8), (2.2, 0, -1.9), 28), (b, (3.4, -2.2, 1.0), (2.2, 0, -2.0), 30)],
        "cam_topdown": lambda a, b: [(a, (0.0, -3.4, 11.0), (0, 0.2, -0.8), 32), (b, (0.0, -2.2, 10.0), (0, 0.2, -0.8), 32)],
        "cam_macro": lambda a, b: [(a, (200.0, -6.2, 1.0), (200, 0.4, -0.2), 30), (b, (200.4, -5.2, 0.6), (200, 0.4, -0.3), 32)],
        "cam_smell": lambda a, b: [(a, (-5.2, -3.8, 1.0), (-1.6, 0.3, 0.6), 28), (b, (-4.4, -4.2, 1.3), (-1.6, 0.3, 0.9), 28)],
        "cam_molecule": lambda a, b: [(a, (299.6, -6.2, 1.0), (299.9, 0, 0.6), 27), (b, (300.3, -5.0, 1.2), (300.1, 0, 0.9), 29)],
        "cam_finish": lambda a, b: [(a, (-6.5, -7.5, 5.5), (0, 0.3, -0.8), 24), (b, (-4.5, -8.0, 4.2), (0, 0.3, -0.6), 24)],
        "cam_final": lambda a, b: [(a, (-8.0, -6.5, 4.5), (0, 0, -0.6), 24), (a + (b - a) * 0.5, (-1.5, -9.5, 3.8), (0, 0, -0.6), 24),
                                   (b, (6.5, -7.0, 4.5), (0, 0.3, -0.6), 24)],
    }
    scn = bpy.context.scene
    for name in names:
        cam, tgt = camera(name)
        moves = plans[name](S[name], ends[name])
        camera_moves(cam, tgt, moves)
        m = scn.timeline_markers.new(name, frame=int(round(F(S[name]))))
        m.camera = cam
        if name in ("cam_valve", "cam_filter_cut", "cam_macro", "cam_molecule", "cam_drain"):
            cam.data.dof.use_dof = True
            cam.data.dof.focus_object = tgt
            cam.data.dof.aperture_fstop = 4.0
    first = bpy.data.objects[names[0]]
    scn.camera = first


# ============================================================== section visibility of props
def hide_in_sections(objs, sec):
    for o in objs:
        pairs = [(0, True)]
        for t0, t1 in sec.windows:
            pairs += [(t0, False), (t1, True)]
        vis(o, pairs)


# ============================================================== main
def main():
    scn = lib.reset_scene()
    scn.render.fps = SP.FPS
    scn.frame_start = 1
    scn.frame_end = SP.TOTAL_FRAMES
    M = build_materials()
    sun, sky, bg = build_world()
    Y = build_yard(M)
    use_collection(collection("Section"))
    sec = Section()
    sec.add(Y["soil"], M["soil"])
    sec.add(Y["plug"], M["dirt"])
    for w in Y["walls"]:
        sec.add(w, M["wall"])
    P = build_pool(M, sec)
    use_collection(collection("Story"))
    S = animate_story(M, Y, P, sec, sun, sky)
    sec.finalize()
    build_equipment(M)
    build_macro(M)
    build_cameras()
    # props in front of the cut plane disappear while a section is open
    front = [S["pile"], S["hose"]] + [o for o in bpy.data.objects if o.name.startswith(("WB_", "Wheelbarrow", "Lounger", "Umb", "Coping", "PalmC"))]
    front = [o for o in front if o.location.y < 0.5 or o.name.startswith(("WB_", "Wheelbarrow", "PalmC"))]
    for o in front:
        if o.animation_data and o.animation_data.action and any(fc.data_path == "hide_render" for fc in o.animation_data.action.fcurves):
            continue
        hide_in_sections([o], sec)
    # colour management / film
    scn.view_settings.view_transform = "AgX"
    try:
        scn.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scn.view_settings.exposure = -0.6
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    out = os.path.join(ROOT, "build", "pool.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print(f"[build] saved {out}  frames 1-{SP.TOTAL_FRAMES}  objects {len(bpy.data.objects)}")


if __name__ == "__main__":
    main()
