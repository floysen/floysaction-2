"""Render the Arabic captions in the style of the reference videos:
ONE word at a time, big bold white text with a thick dark outline and a soft
shadow, centred in the upper part of the frame and popping in on each word.

Arabic is shaped with HarfBuzz (Pillow's raqm layout engine) so letters join
correctly and text runs right-to-left.  Images are pre-rendered and committed,
so the render machine does not need Pillow or raqm.

    python scripts/make_captions.py
        -> assets/captions/w_XXX.png
        -> data/captions.json        (start, end, file per word)
        -> subtitles/captions_ar.srt (plain phrase subtitles, for upload)
"""
import json
import os
import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))
TL = json.load(open(os.path.join(ROOT, "data", "timeline.json"), encoding="utf-8"))
C = CFG["captions"]
OUT = os.path.join(ROOT, "assets", "captions")
HOLD_GAP = 0.5  # keep a word on screen through pauses shorter than this

if not features.check("raqm"):
    raise SystemExit("Pillow was built without libraqm; Arabic shaping would be wrong.")

FONT = ImageFont.truetype(os.path.join(ROOT, CFG["font"]), C["font_size"], layout_engine=ImageFont.Layout.RAQM)


def render_word(text):
    stroke = C["stroke_width"]
    kw = dict(font=FONT, direction="rtl", language="ar", stroke_width=stroke)
    l, t_, r, b = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, **kw)
    pad = stroke + 30
    w, h = r - l + 2 * pad, b - t_ + 2 * pad
    org = (pad - l, pad - t_)
    # soft drop shadow
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((org[0] + 4, org[1] + 8), text, fill=(0, 0, 0, 150),
                            stroke_fill=(0, 0, 0, 150), **kw)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(sh)
    ImageDraw.Draw(im).text(org, text, fill=tuple(C["text_color"]) + (255,),
                            stroke_fill=tuple(C["stroke_color"]) + (255,), **kw)
    return im


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    words = TL["words"]
    entries = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else TL["duration"] + 0.6
        end = nxt if nxt - w["end"] < HOLD_GAP else w["end"] + 0.25
        name = f"w_{i:03d}.png"
        render_word(w["text"]).save(os.path.join(OUT, name), optimize=True)
        entries.append({"start": round(w["start"], 3), "end": round(end, 3), "text": w["text"],
                        "file": f"assets/captions/{name}"})
    json.dump({"center_y_ratio": C["center_y_ratio"], "entries": entries},
              open(os.path.join(ROOT, "data", "captions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    srt = []
    for ci, cap in enumerate(TL["captions"]):
        srt.append(f"{ci + 1}\n{srt_time(cap['start'])} --> {srt_time(cap['end'] + 0.2)}\n‫{cap['text']}‬\n")
    os.makedirs(os.path.join(ROOT, "subtitles"), exist_ok=True)
    open(os.path.join(ROOT, "subtitles", "captions_ar.srt"), "w", encoding="utf-8").write("\n".join(srt))
    print(f"[captions] {len(entries)} word captions -> assets/captions")


if __name__ == "__main__":
    main()
