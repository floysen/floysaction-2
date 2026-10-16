"""Procedural modelling, material and animation helpers for the pool video.

Runs inside Blender 4.2 LTS (bundled Python).  Everything is built from code:
no external meshes or textures are required.
"""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

FPS = 30


def F(t):
    """Seconds -> Blender frame (frame 1 = t 0)."""
    return t * FPS + 1


# ------------------------------------------------------------------ scene setup
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    return scn


def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(col)
    return col


_ACTIVE_COL = [None]


def use_collection(col):
    _ACTIVE_COL[0] = col


def link(obj):
    (_ACTIVE_COL[0] or bpy.context.scene.collection).objects.link(obj)
    return obj


# ------------------------------------------------------------------ materials
def _sock(node, *names):
    for n in names:
        if n in node.inputs:
            return node.inputs[n]
    return None


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def principled(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, transmission=0.0,
               alpha=1.0, emission=None, emission_strength=0.0, ior=1.45, coat=0.0,
               subsurface=0.0, bump=None):
    mat = new_material(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["IOR"].default_value = ior
    s = _sock(bsdf, "Transmission Weight", "Transmission")
    if s:
        s.default_value = transmission
    bsdf.inputs["Alpha"].default_value = alpha
    if coat:
        s = _sock(bsdf, "Coat Weight", "Clearcoat")
        if s:
            s.default_value = coat
    if subsurface:
        s = _sock(bsdf, "Subsurface Weight", "Subsurface")
        if s:
            s.default_value = subsurface
    if emission is not None:
        _sock(bsdf, "Emission Color", "Emission").default_value = (*emission[:3], 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if bump:
        add_noise_bump(mat, scale=bump[0], strength=bump[1])
    if alpha < 1.0 or transmission > 0:
        set_blend(mat)
    mat.diffuse_color = (*color[:3], 1)
    return mat


def set_blend(mat):
    try:
        mat.surface_render_method = "DITHERED"
    except AttributeError:
        mat.blend_method = "HASHED"
    try:
        mat.use_transparent_shadow = True
    except AttributeError:
        pass


def add_noise_bump(mat, scale=20.0, strength=0.2, coord="Object"):
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs[coord], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return nz


def color_variation(mat, c1, c2, scale=4.0, coord="Object", detail=4.0):
    """Drive base colour with noise between two colours (surface variation)."""
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tc.outputs[coord], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return ramp


def value_node(mat, name, value):
    n = mat.node_tree.nodes.new("ShaderNodeValue")
    n.name = n.label = name
    n.outputs[0].default_value = value
    return n


def key_value(mat, name, t, value, interp=None):
    n = mat.node_tree.nodes[name]
    n.outputs[0].default_value = value
    n.outputs[0].keyframe_insert("default_value", frame=F(t))
    if interp:
        _set_last_interp(mat.node_tree.animation_data.action, interp)


# ------------------------------------------------------------------ mesh helpers
def mesh_object(name, bm, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth=False, mats=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    for m in (mats or ([mat] if mat else [])):
        me.materials.append(m)
    ob.location = loc
    ob.rotation_euler = rot
    link(ob)
    if smooth:
        es = ob.modifiers.new("EdgeSplit", "EDGE_SPLIT")
        es.split_angle = math.radians(35)
    return ob


def bm_box(sx, sy, sz, origin="center"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    off = Vector((0, 0, 0.5)) if origin == "bottom" else Vector((0, 0, -0.5)) if origin == "top" else Vector()
    for v in bm.verts:
        v.co = Vector(((v.co.x) * sx, (v.co.y) * sy, (v.co.z + off.z) * sz))
    return bm


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, origin="center", rot=(0, 0, 0), segments=2):
    ob = mesh_object(name, bm_box(*size, origin=origin), mat, loc, rot)
    if bevel:
        bv = ob.modifiers.new("Bevel", "BEVEL")
        bv.width = bevel
        bv.segments = segments
        bv.limit_method = "ANGLE"
        try:
            bv.harden_normals = True
        except AttributeError:
            pass
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def cylinder(name, r, depth, loc=(0, 0, 0), mat=None, verts=24, rot=(0, 0, 0), r2=None,
             origin="center", smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth)
    if origin == "bottom":
        bmesh.ops.translate(bm, vec=(0, 0, depth / 2), verts=bm.verts)
    elif origin == "top":
        bmesh.ops.translate(bm, vec=(0, 0, -depth / 2), verts=bm.verts)
    return mesh_object(name, bm, mat, loc, rot, smooth=smooth)


def sphere(name, r, loc=(0, 0, 0), mat=None, seg=24, rings=14, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    ob = mesh_object(name, bm, mat, loc)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.scale = scale
    return ob


def ico(name, r, loc=(0, 0, 0), mat=None, sub=2, smooth=True, jitter=0.0, seed=0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    if jitter:
        rnd = random.Random(seed)
        for v in bm.verts:
            v.co *= 1 + rnd.uniform(-jitter, jitter)
    ob = mesh_object(name, bm, mat, loc)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def torus(name, R, r, loc=(0, 0, 0), mat=None, seg=48, ring=16, arc=2 * math.pi, rot=(0, 0, 0)):
    bm = bmesh.new()
    closed = abs(arc - 2 * math.pi) < 1e-4
    nseg = seg if closed else seg + 1
    rings = []
    for i in range(nseg):
        a = arc * i / seg
        c = Vector((math.cos(a) * R, math.sin(a) * R, 0))
        ring_v = []
        for j in range(ring):
            b = 2 * math.pi * j / ring
            d = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b)))
            ring_v.append(bm.verts.new(c + d * r))
        rings.append(ring_v)
    for i in range(seg if closed else seg):
        a, b2 = rings[i], rings[(i + 1) % nseg]
        for j in range(ring):
            bm.faces.new((a[j], a[(j + 1) % ring], b2[(j + 1) % ring], b2[j]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bm.normal_update()
    ob = mesh_object(name, bm, mat, loc, rot)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def join(objs, name):
    """Join meshes into one object (keeps world transforms)."""
    bm = bmesh.new()
    mats = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me2 = me.copy()
        o.evaluated_get(dg).to_mesh_clear()
        me2.transform(o.matrix_world)
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
        remap = [mats.index(m) for m in o.data.materials] or [0]
        for p in me2.polygons:
            p.material_index = remap[min(p.material_index, len(remap) - 1)]
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
        bpy.data.objects.remove(o)
    ob = mesh_object(name, bm, mats=mats)
    return ob


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def boolean(ob, cutter, op="DIFFERENCE", apply=True):
    m = ob.modifiers.new("Bool", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"
    if apply:
        apply_modifiers(ob)
        bpy.data.objects.remove(cutter)
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    link(e)
    if parent:
        e.parent = parent
    return e


def parent(child, par, keep=True):
    if keep:
        bpy.context.view_layer.update()  # matrix_world is stale for new objects
    mw = child.matrix_world.copy()
    child.parent = par
    if keep:
        child.matrix_parent_inverse = par.matrix_world.inverted()
        child.matrix_world = mw


def curve_path(name, pts, bevel=0.0, mat=None, resolution=4, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_cyclic_u = cyclic
    cu.bevel_depth = bevel
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    cu.use_path = True
    cu.path_duration = 100
    ob = bpy.data.objects.new(name, cu)
    if mat:
        cu.materials.append(mat)
    link(ob)
    return ob


def smooth_path_points(pts, r=0.35, steps=5):
    """Round the corners of a polyline (pipes with bends)."""
    if len(pts) < 3:
        return pts
    out = [Vector(pts[0])]
    for i in range(1, len(pts) - 1):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        d1 = (a - b)
        d2 = (c - b)
        rr = min(r, d1.length / 2, d2.length / 2)
        p1 = b + d1.normalized() * rr
        p2 = b + d2.normalized() * rr
        for s in range(steps + 1):
            u = s / steps
            out.append((1 - u) ** 2 * p1 + 2 * (1 - u) * u * b + u * u * p2)
    out.append(Vector(pts[-1]))
    return [tuple(p) for p in out]


# ------------------------------------------------------------------ animation
def _set_last_interp(action, interp, easing=None):
    if not action:
        return
    for fc in action.fcurves:
        if fc.keyframe_points:
            kp = fc.keyframe_points[-1]
            kp.interpolation = interp
            if easing:
                kp.easing = easing


def key(ob, path, t, value, interp=None, index=-1, easing=None):
    """Set and keyframe ob.<path> at time t (seconds)."""
    tgt = ob
    parts = path.split(".")
    for p in parts[:-1]:
        tgt = getattr(tgt, p)
    attr = parts[-1]
    if index >= 0:
        getattr(tgt, attr)[index] = value
    else:
        setattr(tgt, attr, value)
    ok = tgt.keyframe_insert(attr, frame=F(t), index=index)
    if interp:
        ad = (tgt.id_data.animation_data)
        if ad and ad.action:
            fr = F(t)
            for fc in ad.action.fcurves:
                if fc.data_path.endswith(attr):
                    for kp in fc.keyframe_points:
                        if abs(kp.co.x - fr) < 1e-3:
                            kp.interpolation = interp
                            if easing:
                                kp.easing = easing
    return ok


def keys(ob, path, pairs, interp=None, easing=None):
    for t, v in pairs:
        key(ob, path, t, v, interp=interp, easing=easing)


def vis(ob, pairs, recursive=True):
    """Visibility switches: pairs of (time, visible).  Children follow their
    parent, except highlight objects (name contains 'Glow') that animate on
    their own schedule."""
    targets = [ob]
    if recursive:
        targets += [c for c in ob.children_recursive if "Glow" not in c.name]
    for o in targets:
        for t, v in pairs:
            o.hide_render = not v
            o.hide_viewport = not v
            o.keyframe_insert("hide_render", frame=F(t))
            o.keyframe_insert("hide_viewport", frame=F(t))


def show_between(ob, t0, t1):
    pairs = []
    if t0 > 0:
        pairs.append((0, False))
    pairs.append((t0, True))
    pairs.append((t1, False))
    vis(ob, pairs)


def pop_in(ob, t, dur=0.35, final=None, overshoot=1.12):
    final = final or tuple(ob.scale)
    key(ob, "scale", t - 0.001, (0.0001, 0.0001, 0.0001))
    key(ob, "scale", t + dur * 0.65, tuple(c * overshoot for c in final))
    key(ob, "scale", t + dur, final)


def pop_out(ob, t, dur=0.25):
    cur = tuple(ob.scale)
    key(ob, "scale", t, cur)
    key(ob, "scale", t + dur, (0.0001, 0.0001, 0.0001))


def drop_in(ob, t, height=3.0, dur=0.45, bounce=0.08):
    end = Vector(ob.location)
    key(ob, "location", t - 0.001, tuple(end + Vector((0, 0, height))))
    key(ob, "location", t + dur * 0.7, tuple(end))
    key(ob, "location", t + dur * 0.85, tuple(end + Vector((0, 0, bounce))))
    key(ob, "location", t + dur, tuple(end))


def damped_rotation(ob, axis, t0, dur, amp, freq, base=0.0, step=1.0 / 15):
    """Decaying oscillation (springs, diving board, settling)."""
    n = int(dur / step)
    for i in range(n + 1):
        tt = i * step
        v = base + amp * math.exp(-3.0 * tt / dur) * math.sin(2 * math.pi * freq * tt)
        key(ob, "rotation_euler", t0 + tt, v, index=axis)


def follow_path(ob, path_ob, t0, period, offset0=0.0, follow=True, reverse=False):
    """Move ob along path_ob, one full lap every `period` seconds, forever (cyclic)."""
    con = ob.constraints.new("FOLLOW_PATH")
    con.target = path_ob
    con.use_fixed_location = True
    con.use_curve_follow = follow
    con.forward_axis = "FORWARD_X"
    con.up_axis = "UP_Z"
    a, b = (1.0, 0.0) if reverse else (0.0, 1.0)
    t_start = t0 - offset0 * period
    con.offset_factor = a
    con.keyframe_insert("offset_factor", frame=F(t_start))
    con.offset_factor = b
    con.keyframe_insert("offset_factor", frame=F(t_start + period))
    for fc in ob.animation_data.action.fcurves:
        if "offset_factor" in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
    return con


def look_at_rot(src, dst):
    d = Vector(dst) - Vector(src)
    return d.to_track_quat("-Z", "Y").to_euler()


# ------------------------------------------------------------------ cameras
def camera(name, lens=30.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start = 0.02
    cd.clip_end = 600
    cam = bpy.data.objects.new(name, cd)
    link(cam)
    tgt = empty(name + "_target")
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return cam, tgt


def camera_moves(cam, tgt, moves, dof=None):
    """moves: list of (t, cam_loc, target_loc, lens)."""
    for t, loc, look, lens in moves:
        key(cam, "location", t, loc)
        key(tgt, "location", t, look)
        if lens:
            key(cam.data, "lens", t, lens)
    if dof:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = tgt
        cam.data.dof.aperture_fstop = dof


# ------------------------------------------------------------------ stateless particles
_EMITTER_GROUP = None


def _emitter_group():
    """Geometry-nodes particle emitter whose state is a pure function of the
    current frame.  Any frame renders identically whether the render starts
    at frame 1 or resumes in the middle (no simulation cache needed)."""
    global _EMITTER_GROUP
    if _EMITTER_GROUP:
        return _EMITTER_GROUP
    ng = bpy.data.node_groups.new("StatelessEmitter", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    I.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    spec = [("Count", "NodeSocketInt", 100), ("Start", "NodeSocketFloat", 1.0),
            ("Rate", "NodeSocketFloat", 2.0), ("End", "NodeSocketFloat", 100.0),
            ("Life", "NodeSocketFloat", 1.0), ("Origin", "NodeSocketVector", (0, 0, 0)),
            ("Jitter", "NodeSocketVector", (0, 0, 0)), ("Direction", "NodeSocketVector", (0, 0, 1)),
            ("Spread", "NodeSocketFloat", 0.2), ("Speed", "NodeSocketFloat", 2.0),
            ("SpeedVar", "NodeSocketFloat", 0.3), ("Gravity", "NodeSocketVector", (0, 0, -9.8)),
            ("FloorZ", "NodeSocketFloat", -1000.0), ("Size", "NodeSocketFloat", 0.05),
            ("Growth", "NodeSocketFloat", 0.0), ("Spin", "NodeSocketFloat", 0.0),
            ("Shape", "NodeSocketObject", None), ("Seed", "NodeSocketInt", 0),
            ("FPS", "NodeSocketFloat", float(FPS)), ("Drag", "NodeSocketFloat", 0.0)]
    for n, st, dv in spec:
        s = I.new_socket(n, in_out="INPUT", socket_type=st)
        if dv is not None:
            s.default_value = dv
    N = ng.nodes
    L = ng.links
    gin = N.new("NodeGroupInput")
    gout = N.new("NodeGroupOutput")

    def math_(op, a, b=None, c=None):
        n = N.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]

    def vmath(op, a, b=None, scale=None):
        n = N.new("ShaderNodeVectorMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        if scale is not None:
            if isinstance(scale, (int, float)):
                n.inputs[3].default_value = scale
            else:
                L.new(scale, n.inputs[3])
        return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs["Vector"]

    def rnd(dtype, seed_off, lo, hi):
        n = N.new("FunctionNodeRandomValue")
        n.data_type = dtype
        ins = [s for s in n.inputs if s.enabled]
        mn = [s for s in ins if s.name == "Min"][0]
        mx = [s for s in ins if s.name == "Max"][0]
        mn.default_value = lo
        mx.default_value = hi
        sd = [s for s in ins if s.name == "Seed"][0]
        L.new(math_("ADD", gin.outputs["Seed"], seed_off), sd)
        outs = [s for s in n.outputs if s.enabled]
        return outs[0]

    idx = N.new("GeometryNodeInputIndex").outputs[0]
    st = N.new("GeometryNodeInputSceneTime")
    frame = st.outputs["Frame"]
    birth = math_("ADD", gin.outputs["Start"], math_("DIVIDE", idx, gin.outputs["Rate"]))
    age_f = math_("SUBTRACT", frame, birth)
    age = math_("DIVIDE", age_f, gin.outputs["FPS"])
    alive = math_("MULTIPLY",
                  math_("MULTIPLY", math_("GREATER_THAN", age, -0.0001),
                        math_("LESS_THAN", age, gin.outputs["Life"])),
                  math_("LESS_THAN", birth, math_("ADD", gin.outputs["End"], 0.001)))
    # drag-adjusted travel time: (1-exp(-k t))/k  (k=0 -> t)
    k = math_("MAXIMUM", gin.outputs["Drag"], 0.0001)
    travel = math_("DIVIDE", math_("SUBTRACT", 1.0, math_("EXPONENT", math_("MULTIPLY", math_("MULTIPLY", k, -1.0), age))), k)
    rdir = rnd("FLOAT_VECTOR", 1, (-1, -1, -1), (1, 1, 1))
    dirv = vmath("NORMALIZE", vmath("ADD", gin.outputs["Direction"], vmath("SCALE", rdir, scale=gin.outputs["Spread"])))
    rsp = rnd("FLOAT", 2, -1.0, 1.0)
    speed = math_("MULTIPLY", gin.outputs["Speed"], math_("ADD", 1.0, math_("MULTIPLY", rsp, gin.outputs["SpeedVar"])))
    rjit = rnd("FLOAT_VECTOR", 3, (-1, -1, -1), (1, 1, 1))
    start = vmath("ADD", gin.outputs["Origin"], vmath("MULTIPLY", rjit, gin.outputs["Jitter"]))
    vel = vmath("SCALE", dirv, scale=math_("MULTIPLY", speed, travel))
    grav = vmath("SCALE", gin.outputs["Gravity"], scale=math_("MULTIPLY", 0.5, math_("MULTIPLY", age, age)))
    pos = vmath("ADD", vmath("ADD", start, vel), grav)
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(pos, sep.inputs[0])
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(sep.outputs[0], comb.inputs[0])
    L.new(sep.outputs[1], comb.inputs[1])
    L.new(math_("MAXIMUM", sep.outputs[2], gin.outputs["FloorZ"]), comb.inputs[2])
    pts = N.new("GeometryNodePoints")
    L.new(gin.outputs["Count"], pts.inputs["Count"])
    L.new(comb.outputs[0], pts.inputs["Position"])
    oi = N.new("GeometryNodeObjectInfo")
    oi.transform_space = "ORIGINAL"
    try:
        oi.inputs["As Instance"].default_value = False
    except KeyError:
        pass
    L.new(gin.outputs["Shape"], oi.inputs["Object"])
    iop = N.new("GeometryNodeInstanceOnPoints")
    L.new(pts.outputs[0], iop.inputs["Points"])
    L.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    rsize = rnd("FLOAT", 4, 0.6, 1.3)
    fade = math_("MINIMUM", 1.0, math_("DIVIDE", math_("SUBTRACT", gin.outputs["Life"], age), 0.18))
    fade_in = math_("MINIMUM", 1.0, math_("DIVIDE", age, 0.06))
    size = math_("MULTIPLY", math_("MULTIPLY", gin.outputs["Size"], rsize),
                 math_("MULTIPLY", math_("MULTIPLY", fade, fade_in),
                       math_("ADD", 1.0, math_("MULTIPLY", gin.outputs["Growth"], age))))
    L.new(size, iop.inputs["Scale"])
    rrot = rnd("FLOAT_VECTOR", 5, (0, 0, 0), (6.283, 6.283, 6.283))
    spin = vmath("ADD", rrot, vmath("SCALE", rnd("FLOAT_VECTOR", 6, (-1, -1, -1), (1, 1, 1)),
                                        scale=math_("MULTIPLY", gin.outputs["Spin"], age)))
    L.new(spin, iop.inputs["Rotation"])
    # delete dead particles only after every per-particle field was evaluated
    # (deleting first would renumber the indices the fields depend on)
    dele = N.new("GeometryNodeDeleteGeometry")
    dele.domain = "INSTANCE"
    L.new(iop.outputs[0], dele.inputs["Geometry"])
    L.new(math_("LESS_THAN", alive, 0.5), dele.inputs["Selection"])
    L.new(dele.outputs[0], gout.inputs[0])
    _EMITTER_GROUP = ng
    return ng


def _ident(ng, name):
    return ng.interface.items_tree[name].identifier


def emitter(name, shape, t0, t1, rate, life, origin, direction=(0, 0, 1), spread=0.2,
            speed=2.0, speed_var=0.3, gravity=(0, 0, -9.8), jitter=(0, 0, 0), size=0.05,
            growth=0.0, spin=0.0, floor_z=-1000.0, seed=0, drag=0.0):
    """Create a deterministic particle emitter active between t0 and t1 (seconds).
    rate = particles per second."""
    ng = _emitter_group()
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    link(ob)
    md = ob.modifiers.new("Emitter", "NODES")
    md.node_group = ng
    count = int(math.ceil(rate * (t1 - t0))) + 1
    vals = {"Count": count, "Start": F(t0), "Rate": rate / FPS, "End": F(t1), "Life": life,
            "Origin": origin, "Jitter": jitter, "Direction": direction, "Spread": spread,
            "Speed": speed, "SpeedVar": speed_var, "Gravity": gravity, "FloorZ": floor_z,
            "Size": size, "Growth": growth, "Spin": spin, "Shape": shape, "Seed": seed,
            "FPS": float(FPS), "Drag": drag}
    for k, v in vals.items():
        md[_ident(ng, k)] = v
    # whole emitter hidden outside its active window (+ particle life)
    show_between(ob, max(0.0, t0 - 0.05), t1 + life + 0.1)
    return ob


def key_emitter(ob, socket, t, value):
    ng = _emitter_group()
    ident = _ident(ng, socket)
    md = ob.modifiers["Emitter"]
    md[ident] = value
    ob.keyframe_insert(f'modifiers["Emitter"]["{ident}"]', frame=F(t))


def particle_shape(name, kind, mat, r=1.0):
    """Hidden template mesh used as particle instance."""
    if kind == "sphere":
        ob = ico(name, r, mat=mat, sub=2)
    elif kind == "drop":
        ob = sphere(name, r, mat=mat, seg=12, rings=8, scale=(0.8, 0.8, 1.3))
        bpy.context.view_layer.update()
    elif kind == "chunk":
        ob = ico(name, r, mat=mat, sub=1, smooth=False, jitter=0.35, seed=hash(name) % 1000)
    elif kind == "flake":
        ob = box(name, (r * 1.6, r, r * 0.08), mat=mat)
    elif kind == "puff":
        ob = ico(name, r, mat=mat, sub=3)
    else:
        raise ValueError(kind)
    ob.location = (0, 0, -500)  # templates live far away
    ob.hide_render = True
    ob.hide_viewport = True
    return ob
