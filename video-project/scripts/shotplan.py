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
E["dig"] = word("حفرت")
E["dig_end"] = word("حوش", end=True) + 0.3
E["fill"] = word("وعبيتها")
E["congrats"] = word("مبروك")
E["pool"] = word("مسبح")
E["next_day"] = word("ثاني")
E["seep"] = word("تتسرب")
E["collapse"] = word("والجدران")
E["collapse_end"] = para(1, end=True) + 0.1
E["fix"] = word("عشان", after=P[2])
E["rebar"] = word("شبكة", after=P[2])
E["spray"] = word("وترش", after=P[2])
E["shell_done"] = word("الخرسانة", end=True)
E["holds"] = word("يمسك", after=P[2]) - 0.6
E["drain"] = word("فضيته")
E["ground_water"] = word("الجوفية", after=P[3])
E["push_up"] = word("تدفعه")
E["lift"] = word("تطلع")
E["boat"] = word("قارب")
E["solution"] = P[4]
E["valve_in"] = word("صمام", after=P[4])
E["pressure"] = word("ضغط", after=P[4])
E["valve_open"] = word("يفتح")
E["no_lift"] = word("يمنع")
E["valve_name"] = word("يسمونه")
E["week"] = word("أسبوع")
E["green"] = word("الراكدة")
E["pump"] = word("مضخة")
E["suck"] = word("تسحب", after=P[5])
E["filter"] = word("خزان")
E["sand_trap"] = word("يحجز")
E["clean"] = word("وترجع", after=P[5])
E["filter_name"] = word("فلتر")
E["leaves"] = word("الأوراق", after=P[6])
E["sink"] = word("الثقيلة")
E["skimmer"] = word("فتحة", after=P[6])
E["skimmer_suck"] = word("تسحب", after=word("فتحة", after=P[6]))
E["skimmer_name"] = word("السكيمر", after=P[6])
E["drain_hole"] = word("وفتحة")
E["drain_suck"] = word("تسحب", after=E["drain_hole"])
E["jets"] = P[7]
E["swirl"] = word("تدور")
E["push_skimmer"] = word("وتدفع", after=P[7])
E["bacteria"] = word("البكتيريا")
E["slip"] = word("الرمل", after=P[8])
E["chlorine"] = word("الكلور", after=P[8])
E["kill"] = word("يقضي")
E["smell"] = word("والريحة")
E["not_chlorine"] = word("مو", after=P[9])
E["reaction"] = word("تفاعله")
E["sweat"] = word("العرق")
E["finish"] = P[10]
E["tiles"] = word("البلاط")
E["ladder"] = word("والدرج")
E["board"] = word("القفز")
E["final"] = P[11]
E["end"] = DURATION


# ---------------------------------------------------------------- camera shots
# (name of camera rig in the Blender scene, start time).  A shot lasts until the
# next one begins.  Cuts happen on narration beats, never on a fixed grid.
SHOTS = [
    ("cam_yard", 0.0),
    ("cam_section_seep", E["next_day"] + 0.35),
    ("cam_rebar", E["fix"]),
    ("cam_spray", E["spray"]),
    ("cam_full_pool", E["holds"]),
    ("cam_section_lift", E["drain"] - 0.1),
    ("cam_valve", E["solution"]),
    ("cam_sun_week", E["week"] - 0.4),
    ("cam_equipment", E["pump"] - 0.3),
    ("cam_filter_cut", E["filter"] - 0.2),
    ("cam_debris", E["leaves"] - 0.3),
    ("cam_drain", E["drain_hole"] - 0.1),
    ("cam_topdown", E["jets"]),
    ("cam_macro", E["bacteria"] - 0.2),
    ("cam_smell", E["smell"] - 0.1),
    ("cam_molecule", E["not_chlorine"] - 0.1),
    ("cam_finish", E["finish"]),
    ("cam_final", E["final"]),
]


def frame(t):
    return int(round(t * FPS)) + 1


# ---------------------------------------------------------------- sound cues
# (time, sound file in assets/sound-effects, gain dB)
def sfx_cues():
    c = []
    for i in range(4):
        c.append((E["dig"] + 0.05 + i * 0.32, "dig.wav", -2 - i))
    c.append((E["fill"], "water_pour.wav", -3))
    c.append((E["congrats"], "sparkle.wav", -6))
    c.append((E["pool"] + 0.25, "splash.wav", -4))
    c.append((E["next_day"] - 0.1, "whoosh.wav", -8))
    c.append((E["seep"], "drips.wav", -6))
    c.append((E["collapse"] + 0.3, "crumble.wav", -2))
    for i in range(5):
        c.append((E["rebar"] + i * 0.22, "metal_clank.wav", -6 - i))
    c.append((E["spray"], "spray.wav", -5))
    c.append((E["holds"] + 0.2, "water_pour.wav", -6))
    c.append((E["drain"], "drain_gurgle.wav", -4))
    c.append((E["ground_water"], "underground_rumble.wav", -4))
    c.append((E["lift"], "lift_creak.wav", -3))
    c.append((E["boat"], "splash.wav", -7))
    c.append((E["solution"] - 0.05, "whoosh.wav", -8))
    c.append((E["valve_in"] + 0.6, "valve_click.wav", -2))
    c.append((E["valve_open"], "valve_click.wav", -4))
    c.append((E["valve_open"] + 0.2, "bubbles.wav", -4))
    c.append((E["week"] - 0.4, "whoosh.wav", -9))
    c.append((E["pump"], "pump_start.wav", -4))
    c.append((E["suck"], "pipe_flow.wav", -6))
    c.append((E["clean"], "water_shimmer.wav", -7))
    c.append((E["leaves"], "leaves.wav", -5))
    for i in range(3):
        c.append((E["sink"] + 0.2 + i * 0.35, "plop.wav", -5 - i))
    c.append((E["skimmer_suck"], "pipe_flow.wav", -7))
    c.append((E["drain_suck"], "drain_gurgle.wav", -7))
    c.append((E["jets"] + 0.3, "jets.wav", -6))
    c.append((E["swirl"], "swirl.wav", -6))
    c.append((E["bacteria"] - 0.2, "whoosh.wav", -9))
    c.append((E["chlorine"], "fizz.wav", -4))
    c.append((E["kill"] + 0.2, "zap.wav", -7))
    c.append((E["smell"], "sniff.wav", -5))
    c.append((E["reaction"], "reaction_pop.wav", -5))
    for i in range(6):
        c.append((E["tiles"] + i * 0.12, "tile_clack.wav", -6 - (i % 3)))
    c.append((E["ladder"] + 0.15, "metal_clank.wav", -5))
    c.append((E["board"] + 0.35, "board_boing.wav", -4))
    c.append((E["final"] + 0.1, "sparkle.wav", -5))
    c.append((E["final"] + 0.9, "splash.wav", -5))
    return sorted(c)


if __name__ == "__main__":
    print(f"duration {DURATION:.2f}s, {TOTAL_FRAMES} frames")
    for k, v in E.items():
        print(f"{v:7.2f}  {k}")
