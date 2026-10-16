"""Join the rendered chunks + mixed audio into the final MP4, then verify it."""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import shotplan as SP  # noqa: E402

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")


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
    check(v and v[0]["codec_name"] == "h264", "video codec h264")
    check(v and (v[0]["width"], v[0]["height"]) == (1080, 1920), f"resolution {v[0]['width']}x{v[0]['height']}")
    n, d = (int(x) for x in v[0]["r_frame_rate"].split("/"))
    check(abs(n / d - SP.FPS) < 0.01, f"frame rate {n / d:.2f}")
    check(v[0].get("pix_fmt") == "yuv420p", "pixel format yuv420p")
    check(bool(au) and au[0]["codec_name"] == "aac", "audio aac")
    check(dur >= SP.TL["duration"] - 0.05, f"duration {dur:.2f}s (voiceover {SP.TL['duration']:.2f}s)")
    err = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-f", "null", "-"], stderr=subprocess.PIPE, text=True).stderr.strip()
    check(not err, "full decode without errors")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", default="full")
    a = ap.parse_args()
    chunks = sorted(glob.glob(os.path.join(ROOT, "build", f"chunks_{a.quality}", "chunk_*.mp4")))
    need = -(-SP.TOTAL_FRAMES // 90)
    if len(chunks) < need:
        sys.exit(f"[assemble] {need - len(chunks)} chunks missing - run render.sh again to resume")
    lst = os.path.join(ROOT, "build", f"chunks_{a.quality}.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write("file '" + c.replace("\\", "/").replace("'", "'\\''") + "'\n")
    out = os.path.join(ROOT, SP.CFG["output_file"] if a.quality == "full" else f"output/toilet_{a.quality}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part.mp4"
    vf = [] if a.quality == "full" else ["-vf", "scale=1080:1920:flags=lanczos"]
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", os.path.join(ROOT, "build", "mix.wav"), "-map", "0:v", "-map", "1:a"] + vf +
                   ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
                    "-r", str(SP.FPS), "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-af", f"loudnorm=I={SP.CFG['audio']['loudness_target_lufs']}:TP=-1.0:LRA=11",
                    "-t", f"{SP.DURATION:.3f}", tmp], check=True)
    os.replace(tmp, out)
    print("[verify]", os.path.relpath(out, ROOT))
    if not verify(out):
        sys.exit("[verify] the output did not pass all checks")
    print(f"[done] {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
