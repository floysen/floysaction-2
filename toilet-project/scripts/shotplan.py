"""Single source of truth for timing: shots, story events and sound-effect cues.

Every time below is derived from data/timeline.json (the voiceover alignment),
looked up by the actual spoken word, so visuals, sound effects and captions all
follow the real narration.  Imported by the Blender scene builder and by the
audio mixer.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))
TL = json.load(open(os.path.join(ROOT, "data", "timeline.json"), encoding="utf-8"))
FPS = CFG["fps"]
DURATION = TL["duration"] + CFG.get("tail_seconds", 1.0)
TOTAL_FRAMES = int(round(DURATION * FPS))

_STRIP = re.compile(r"[^ء-ي]")
_WORDS = [(_STRIP.sub("", w["text"]), w) for w in TL["words"]]


def _norm(s):
    return _STRIP.sub("", s)


def word(text, after=0.0, end=False):
    """Start (or end) time of the first spoken word matching `text` after `after` s."""
    key = _norm(text)
    for k, w in _WORDS:
        if w["start"] >= after - 1e-6 and (k == key or (len(key) > 3 and key in k)):
            return w["end"] if end else w["start"]
    raise KeyError(f"word not found in timeline: {text} after {after}")


def para(i, end=False):
    p = TL["paragraphs"][i]
    return p["end"] if end else p["start"]


# ---------------------------------------------------------------- story events
P = [para(i) for i in range(len(TL["paragraphs"]))]
E = {}
w = word
E["dig"] = w("حفرت")
E["build"] = w("وبنيت")
E["toilet0"] = w("صار")
E["problem"] = P[1]
E["smell"] = w("الريحة")
E["flies"] = w("والذباب")
E["fill"] = w("وتمتلي")
E["house"] = P[2]
E["seat_in"] = w("كرسي")
E["pipe"] = w("بأنبوب")
E["sewer"] = w("شبكة")
E["street"] = w("الشارع")
E["stuck"] = P[3]
E["still"] = w("تتحرك")
E["bucket"] = w("دلو")
E["push"] = w("يدفع")
E["problem2"] = P[4]
E["gas"] = w("غازات")
E["enter"] = w("وتدخل")
E["bend"] = w("تثني")
E["S"] = w("حرف")
E["seal"] = w("كمية", after=P[5])
E["block"] = w("تسد")
E["trap_name"] = w("مصيدة", after=P[5])
E["catch"] = w("تحجز")
E["bigflush"] = w("تنزل")
E["fills"] = w("تملأ")
E["rush"] = w("تندفع")
E["suck"] = w("تسحب", after=P[7])
E["empty"] = w("وتفضيه")
E["siphon_name"] = w("ظاهرة")
E["gurgle"] = w("القرقرة")
E["air"] = w("الهواء", after=P[8])
E["lazy"] = P[9]
E["tank"] = w("خزان")
E["flapper"] = w("سدادة")
E["handle"] = w("ومقبض")
E["lift"] = w("يرفعها")
E["float"] = w("وعوامة")
E["full"] = w("امتلأ")
E["rush2"] = P[10]
E["suckair"] = w("يسحب", after=P[10])
E["dry"] = w("تنشف")
E["gas_back"] = w("ترجع", after=P[10])
E["vent"] = w("تهوية")
E["roof"] = w("السطح", after=P[11])
E["air_in"] = w("يدخل", after=P[11])
E["balance"] = w("ويوازن")
E["see"] = P[12]
E["chimney"] = w("مدخنة")
E["breathe"] = w("تتنفس")
E["seat"] = w("المقعد")
E["lid"] = w("والغطاء")
E["final"] = P[14]
E["end"] = DURATION

SHOTS = []


def frame(t):
    return int(round(t * FPS)) + 1


def sfx_cues():
    c = []
    for i in range(4):
        c.append((E["dig"] + 0.05 + i * 0.3, "dig.wav", -2 - i))
    for i in range(5):
        c.append((E["build"] + i * 0.18, "tile_clack.wav", -6))
    c.append((E["toilet0"], "sparkle.wav", -7))
    c.append((E["smell"], "sniff.wav", -5))
    c.append((E["flies"], "flies.wav", -3))
    c.append((E["fill"], "drain_gurgle.wav", -7))
    c.append((E["house"] - 0.1, "whoosh.wav", -7))
    c.append((E["seat_in"] + 0.1, "tile_clack.wav", -4))
    c.append((E["pipe"], "pipe_flow.wav", -9))
    c.append((E["street"], "whoosh.wav", -9))
    c.append((E["bucket"], "water_pour.wav", -3))
    c.append((E["push"], "pipe_flow.wav", -5))
    c.append((E["gas"], "gas_hiss.wav", -5))
    c.append((E["enter"], "sniff.wav", -6))
    c.append((E["bend"], "whoosh.wav", -8))
    c.append((E["S"], "metal_clank.wav", -9))
    c.append((E["seal"], "water_shimmer.wav", -7))
    c.append((E["block"], "zap.wav", -9))
    c.append((E["trap_name"], "sparkle.wav", -8))
    c.append((E["catch"], "plop.wav", -5))
    c.append((E["bigflush"], "water_pour.wav", -3))
    c.append((E["fills"], "pipe_flow.wav", -5))
    c.append((E["suck"], "flush.wav", -2))
    c.append((E["siphon_name"], "sparkle.wav", -8))
    c.append((E["gurgle"], "drain_gurgle.wav", -2))
    c.append((E["air"], "bubbles.wav", -5))
    c.append((E["tank"] - 0.2, "whoosh.wav", -8))
    c.append((E["tank"] + 0.1, "tile_clack.wav", -4))
    c.append((E["lift"], "valve_click.wav", -3))
    c.append((E["lift"] + 0.15, "flush.wav", -6))
    c.append((E["float"], "water_pour.wav", -8))
    c.append((E["full"], "valve_click.wav", -4))
    c.append((E["rush2"], "flush.wav", -4))
    c.append((E["suckair"], "bubbles.wav", -5))
    c.append((E["gas_back"], "gas_hiss.wav", -5))
    c.append((E["vent"], "metal_clank.wav", -6))
    c.append((E["air_in"], "whoosh.wav", -7))
    c.append((E["see"] - 0.1, "whoosh.wav", -7))
    c.append((E["chimney"], "zap.wav", -8))
    c.append((E["breathe"], "breath.wav", -5))
    c.append((E["seat"], "tile_clack.wav", -3))
    c.append((E["lid"], "tile_clack.wav", -3))
    c.append((E["final"], "sparkle.wav", -4))
    return sorted(c)


if __name__ == "__main__":
    print(f"duration {DURATION:.2f}s, {TOTAL_FRAMES} frames")
    for k, v in E.items():
        print(f"{v:7.2f}  {k}")
