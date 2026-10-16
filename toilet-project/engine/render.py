"""Render the whole video with the 2D engine, then mux audio and verify.

    python engine/render.py --quality full      (render.sh calls this)

Frames are drawn with cairo in parallel worker processes, in chunks of
`chunk_frames` frames.  Each chunk is piped straight into FFmpeg as a small
lossless-quality H.264 file (no huge PNG folders).  Finished chunks are kept,
so an interrupted render resumes at the first missing chunk.
"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import shotplan as SP  # noqa: E402

CFG = SP.CFG
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")


def chunk_path(q, i):
    return os.path.join(ROOT, "build", f"chunks_{q}", f"chunk_{i:04d}.mp4")


def render_chunk(job):
    q, i, f0, f1, scale = job
    import frame  # imported in the worker
    out = chunk_path(q, i)
    tmp = out + ".part.mp4"
    w, h = int(1080 * scale), int(1920 * scale)
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}",
           "-r", str(SP.FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "10",
           "-pix_fmt", "yuv420p", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    stride_ok = None
    for f in range(f0, f1):
        t = f / SP.FPS
        surf = frame.render(t, scale)
        data = surf.get_data()
        if stride_ok is None:
            stride_ok = surf.get_stride() == w * 4
        if stride_ok:
            p.stdin.write(bytes(data))
        else:
            st = surf.get_stride()
            mv = bytes(data)
            p.stdin.write(b"".join(mv[r * st:r * st + w * 4] for r in range(h)))
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on chunk {i}")
    os.replace(tmp, out)
    return i, f1 - f0


def verify(path):
    info = json.loads(subprocess.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                                     check=True, stdout=subprocess.PIPE).stdout)
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    au = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + msg)
        ok &= bool(cond)

    print("[verify]", os.path.relpath(path, ROOT))
    check(v and v[0]["codec_name"] == "h264", f"video codec: {v[0]['codec_name'] if v else 'none'}")
    check(v and (v[0]["width"], v[0]["height"]) == (1080, 1920), f"resolution: {v[0]['width']}x{v[0]['height']}" if v else "resolution")
    num, den = (int(x) for x in v[0]["r_frame_rate"].split("/"))
    check(abs(num / den - SP.FPS) < 0.01, f"frame rate: {num / den:.2f}")
    check(v[0].get("pix_fmt") == "yuv420p", f"pixel format: {v[0].get('pix_fmt')}")
    check(au and au[0]["codec_name"] == "aac", f"audio: {au[0]['codec_name'] + ' ' + au[0]['sample_rate'] + ' Hz' if au else 'MISSING'}")
    check(dur >= SP.TL["duration"] - 0.05, f"duration: {dur:.2f}s (voiceover {SP.TL['duration']:.2f}s, not cut off)")
    err = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr.strip()
    check(not err, "full decode without errors" if not err else f"decode errors: {err[:300]}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", default="full", choices=sorted(CFG["quality"]))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--encode-only", action="store_true")
    a = ap.parse_args()
    q = CFG["quality"][a.quality]
    scale = q["scale"]
    n = SP.TOTAL_FRAMES
    size = CFG.get("chunk_frames", 120)
    jobs = [(a.quality, i, f0, min(n, f0 + size), scale) for i, f0 in enumerate(range(0, n, size))]
    os.makedirs(os.path.dirname(chunk_path(a.quality, 0)), exist_ok=True)
    todo = [j for j in jobs if not os.path.exists(chunk_path(a.quality, j[1]))]
    if a.encode_only and todo:
        sys.exit(f"[render] {len(todo)} chunks missing - run without --encode-only first")
    print(f"[render] {n} frames ({n / SP.FPS:.1f}s) at {int(1080 * scale)}x{int(1920 * scale)}, "
          f"{len(jobs)} chunks, {len(todo)} to render, {a.workers} worker processes", flush=True)
    t0 = time.time()
    done = 0
    if todo:
        with mp.Pool(a.workers) as pool:
            for i, k in pool.imap_unordered(render_chunk, todo):
                done += k
                el = time.time() - t0
                left = sum(j[3] - j[2] for j in todo) - done
                print(f"[render] chunk {i + 1}/{len(jobs)} done  {done / el:.1f} frames/s  ETA {left / max(done / el, 1e-6) / 60:.1f} min", flush=True)
    # audio
    import mix_audio
    mix_audio.main()
    # concatenate chunks + audio -> final mp4
    lst = os.path.join(ROOT, "build", f"chunks_{a.quality}.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for j in jobs:
            p = chunk_path(a.quality, j[1]).replace("\\", "/").replace("'", "'\\''")
            fh.write(f"file '{p}'\n")
    out = os.path.join(ROOT, CFG["output_file"] if a.quality == "full" else f"output/toilet_{a.quality}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part.mp4"
    vf = [] if scale == 1.0 else ["-vf", "scale=1080:1920:flags=lanczos"]
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
           "-i", os.path.join(ROOT, "build", "mix.wav"), "-map", "0:v", "-map", "1:a"] + vf + [
           "-c:v", "libx264", "-preset", "slow", "-crf", str(q.get("crf", 17)), "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-r", str(SP.FPS), "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", f"loudnorm=I={CFG['audio']['loudness_target_lufs']}:TP=-1.0:LRA=11",
           "-t", f"{SP.DURATION:.3f}", tmp]
    print("[encode] final MP4 ...", flush=True)
    subprocess.run(cmd, check=True)
    os.replace(tmp, out)
    if not verify(out):
        sys.exit("[verify] the output did not pass all checks")
    print(f"[done] {os.path.relpath(out, ROOT)}  ({(time.time() - t0) / 60:.1f} min)")


if __name__ == "__main__":
    mp.freeze_support()
    main()
