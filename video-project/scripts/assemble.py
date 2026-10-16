"""Encode the final MP4: rendered frames + Arabic captions + mixed audio, then verify it.

    python scripts/assemble.py --quality full
(standard library only; also runs inside Blender's Python)
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import shotplan as SP  # noqa: E402


def ffmpeg():
    return os.environ.get("FFMPEG", "ffmpeg")


def ffprobe():
    return os.environ.get("FFPROBE", "ffprobe")


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def cq(path):
    """Quote a path for an ffconcat file (absolute, forward slashes, quote-safe)."""
    p = os.path.abspath(os.path.join(ROOT, path)).replace("\\", "/")
    return "'" + p.replace("'", "'\\''") + "'"


def caption_list():
    caps = json.load(open(os.path.join(ROOT, "data", "captions.json"), encoding="utf-8"))
    blank = "assets/captions/blank.png"
    lines = ["ffconcat version 1.0"]
    t = 0.0
    last = blank
    for e in caps["entries"]:
        if e["start"] > t + 0.001:
            lines += [f"file {cq(blank)}", f"duration {e['start'] - t:.3f}"]
            t = e["start"]
        dur = max(0.04, e["end"] - t)
        lines += [f"file {cq(e['file'])}", f"duration {dur:.3f}"]
        t += dur
        last = e["file"]
    tail = SP.DURATION - t
    lines += [f"file {cq(blank)}", f"duration {max(tail, 0.1):.3f}", f"file {cq(blank)}"]
    path = os.path.join(ROOT, "build", "captions.ffconcat")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return path, caps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", default="full")
    ap.add_argument("--frames", default=None)
    ap.add_argument("--out", default=None)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    q = SP.CFG["quality"][a.quality]
    step = q.get("frame_step", 1)
    frames = a.frames or os.path.join(ROOT, "output", f"frames_{a.quality}")
    out = a.out or os.path.join(ROOT, SP.CFG["output_file"] if a.quality == "full" else f"output/pool_{a.quality}.mp4")
    mix = os.path.join(ROOT, "build", "mix.wav")
    for p in (frames, mix):
        if not os.path.exists(p):
            sys.exit(f"[assemble] missing {p}")
    expected = list(range(1, SP.TOTAL_FRAMES + 1, step))
    missing = [f for f in expected if not os.path.exists(os.path.join(frames, f"frame_{f:05d}.png"))]
    if missing:
        sys.exit(f"[assemble] {len(missing)} frames missing (first: {missing[0]}). Re-run render.sh to resume.")
    # frames are numbered 1, 1+step, ... ; feed them through a list so steps work
    flist = os.path.join(ROOT, "build", f"frames_{a.quality}.ffconcat")
    with open(flist, "w", encoding="utf-8") as fh:
        fh.write("ffconcat version 1.0\n")
        for f in expected:
            fh.write(f"file {cq(os.path.join(frames, f'frame_{f:05d}.png'))}\nduration {step / SP.FPS:.6f}\n")
        fh.write(f"file {cq(os.path.join(frames, f'frame_{expected[-1]:05d}.png'))}\n")
    caplist, caps = caption_list()
    W, H = caps["width"], caps["height"]
    cap_y = int(H * (1 - caps["bottom_margin_ratio"])) - caps["caption_height"]
    fps = SP.FPS
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part.mp4"
    filt = (f"[0:v]scale={W}:{H}:flags=lanczos,fps={fps},format=yuv420p[bg];"
            f"[1:v]fps={fps},format=rgba[cap];"
            f"[bg][cap]overlay=x=0:y={cap_y}:eof_action=pass:shortest=0,format=yuv420p[v]")
    cmd = [ffmpeg(), "-hide_banner", "-y",
           "-f", "concat", "-safe", "0", "-i", flist,
           "-f", "concat", "-safe", "0", "-i", caplist,
           "-i", mix,
           "-filter_complex", filt,
           "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", "slow" if a.quality == "full" else "medium",
           "-crf", str(q.get("crf", 18)), "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-r", str(fps), "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", f"loudnorm=I={SP.CFG['audio']['loudness_target_lufs']}:TP=-1.0:LRA=11",
           "-t", f"{SP.DURATION:.3f}", tmp]
    print("[assemble] encoding", rel(out))
    subprocess.run(cmd, check=True, cwd=ROOT)
    os.replace(tmp, out)
    verify(out)


def verify(path):
    info = json.loads(subprocess.run([ffprobe(), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                                     check=True, stdout=subprocess.PIPE).stdout)
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    au = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + msg)
        ok &= bool(cond)

    print("[verify]", rel(path))
    check(v and v[0]["codec_name"] == "h264", f"video codec: {v[0]['codec_name'] if v else 'none'}")
    check(v and (v[0]["width"], v[0]["height"]) == (1080, 1920), f"resolution: {v[0]['width']}x{v[0]['height']}" if v else "resolution")
    fr = v[0]["r_frame_rate"] if v else "0/1"
    num, den = (int(x) for x in fr.split("/"))
    check(abs(num / den - SP.FPS) < 0.01, f"frame rate: {num / den:.2f}")
    check(v and v[0].get("pix_fmt") == "yuv420p", f"pixel format: {v[0].get('pix_fmt') if v else '-'}")
    check(au and au[0]["codec_name"] == "aac", f"audio: {au[0]['codec_name'] + ' ' + au[0]['sample_rate'] + ' Hz' if au else 'MISSING'}")
    voice = SP.TL["duration"]
    check(dur >= voice - 0.05, f"duration: {dur:.2f}s (voiceover {voice:.2f}s, not cut off)")
    err = subprocess.run([ffmpeg(), "-v", "error", "-i", path, "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr.strip()
    check(not err, "full decode without errors" if not err else f"decode errors: {err[:300]}")
    if not ok:
        sys.exit("[verify] the output did not pass all checks")
    print(f"[verify] all checks passed -> {rel(path)}")


if __name__ == "__main__":
    main()
