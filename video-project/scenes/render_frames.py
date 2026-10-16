"""Render the animation frames from build/pool.blend.

    blender -b build/pool.blend --python scenes/render_frames.py -- --quality full
        [--engine auto|eevee|cycles] [--device auto|cpu] [--frames 1-2400]
        [--step 1] [--out output/frames_full]

Resumable: frames that already exist on disk are skipped, and each frame is
written to a temporary file first and renamed only when complete, so an
interrupted render never leaves a half-written frame behind.
"""
import argparse
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", default="full", choices=sorted(CFG["quality"].keys()))
    ap.add_argument("--engine", default="auto", choices=["auto", "eevee", "cycles"])
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"])
    ap.add_argument("--frames", default=None, help="e.g. 1-2400 or 10,50,90")
    ap.add_argument("--step", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--resolution-percent", type=int, default=100)
    return ap.parse_args(argv)


def enable_cycles_gpu():
    """Return the GPU backend that was enabled, or None for CPU."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return None
    for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        try:
            prefs.refresh_devices()
        except AttributeError:
            prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            return f"{backend} ({', '.join(d.name for d in gpus)})"
    prefs.compute_device_type = "NONE"
    return None


def configure(args):
    scn = bpy.context.scene
    q = CFG["quality"][args.quality]
    engine = q["engine"] if args.engine == "auto" else args.engine.upper()
    r = scn.render
    r.resolution_x, r.resolution_y = q["resolution"]
    r.resolution_percentage = args.resolution_percent
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 15
    r.use_motion_blur = False
    r.film_transparent = False
    gpu = None
    if engine == "CYCLES":
        r.engine = "CYCLES"
        c = scn.cycles
        gpu = enable_cycles_gpu() if args.device != "cpu" else None
        c.device = "GPU" if gpu else "CPU"
        c.samples = q["samples"]
        c.use_adaptive_sampling = True
        c.adaptive_threshold = 0.02
        c.use_denoising = bool(q.get("denoise", True))
        try:
            c.denoiser = "OPENIMAGEDENOISE"
        except TypeError:
            pass
        c.max_bounces = 8
        c.transparent_max_bounces = 16
        c.transmission_bounces = 8
        c.caustics_reflective = False
        c.caustics_refractive = False
        c.blur_glossy = 1.0
        c.use_animated_seed = False
        r.use_persistent_data = True
    else:
        r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
        e = scn.eevee
        e.taa_render_samples = q["samples"]
        for attr, val in (("use_raytracing", True), ("use_shadows", True), ("shadow_ray_count", 2),
                          ("shadow_step_count", 8), ("use_gtao", True), ("gtao_distance", 1.5),
                          ("use_bloom", True), ("bloom_intensity", 0.03), ("use_ssr", True),
                          ("use_ssr_refraction", True), ("use_soft_shadows", True),
                          ("volumetric_tile_size", "8"), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
            try:
                setattr(e, attr, val)
            except (AttributeError, TypeError):
                pass
        try:
            e.ray_tracing_options.resolution_scale = "2"
            e.ray_tracing_method = "SCREEN"
        except (AttributeError, TypeError):
            pass
        # transmission / refraction on the water and the filter tank
        for m in bpy.data.materials:
            try:
                m.use_raytrace_refraction = m.name in ("water",)
            except AttributeError:
                pass
    return engine, gpu


def frame_list(args, scn):
    step = args.step or CFG["quality"][args.quality].get("frame_step", 1)
    if args.frames:
        out = []
        for part in args.frames.split(","):
            if "-" in part:
                a, b = part.split("-")
                out += list(range(int(a), int(b) + 1, step))
            else:
                out.append(int(part))
        return out
    return list(range(scn.frame_start, scn.frame_end + 1, step))


def main():
    args = parse()
    scn = bpy.context.scene
    engine, gpu = configure(args)
    out_dir = args.out or os.path.join(ROOT, "output", f"frames_{args.quality}")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    frames = frame_list(args, scn)
    todo = [f for f in frames if not os.path.exists(os.path.join(out_dir, f"frame_{f:05d}.png"))]
    print(f"[render] engine={engine} device={gpu or 'CPU'} quality={args.quality} "
          f"res={scn.render.resolution_x}x{scn.render.resolution_y}@{scn.render.resolution_percentage}% "
          f"frames={len(frames)} remaining={len(todo)} -> {out_dir}", flush=True)
    t_start = time.time()
    for i, f in enumerate(todo):
        final = os.path.join(out_dir, f"frame_{f:05d}.png")
        tmp = os.path.join(out_dir, f"_tmp_{f:05d}.png")
        scn.frame_set(f)
        scn.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, final)
        done = i + 1
        el = time.time() - t_start
        eta = el / done * (len(todo) - done)
        print(f"[render] frame {f} ({done}/{len(todo)})  {el / done:.1f}s/frame  ETA {eta / 60:.1f} min", flush=True)
    print("[render] all frames present", flush=True)


if __name__ == "__main__":
    main()
