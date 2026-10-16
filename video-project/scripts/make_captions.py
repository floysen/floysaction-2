"""Render the Arabic captions as transparent PNG images.

Arabic is shaped with HarfBuzz (Pillow's raqm layout engine) so letters join
correctly, and words are laid out right-to-left.  Each caption gets one image
per spoken word, with the current word highlighted (karaoke style), timed from
data/timeline.json.

    python scripts/make_captions.py
        -> assets/captions/cap_XXX_YY.png, assets/captions/blank.png
        -> data/captions.json   (start, end, file)
        -> subtitles/captions_ar.srt  (plain subtitle file, for reference/upload)

The PNGs are committed with the project, so rendering does not need Pillow.
"""
import json
import os
import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))
TL = json.load(open(os.path.join(ROOT, "data", "timeline.json"), encoding="utf-8"))
C = CFG["captions"]
W, H = 1080, 1920
CAP_H = 440  # every caption image has the same size (ffmpeg overlay needs that)
OUT = os.path.join(ROOT, "assets", "captions")
MERGE_GAP = 0.45  # keep a caption on screen through short pauses

if not features.check("raqm"):
    raise SystemExit("Pillow was built without libraqm; Arabic shaping would be wrong. "
                     "Install a Pillow wheel with raqm support (pip install -U pillow).")

FONT = ImageFont.truetype(os.path.join(ROOT, CFG["font"]), C["font_size"],
                          layout_engine=ImageFont.Layout.RAQM)


def word_width(w):
    return FONT.getlength(w, direction="rtl", language="ar")


def layout(words):
    """Return lines -> list of (word_index, x_left) laid out right-to-left."""
    max_w = W * C["max_width_ratio"]
    space = word_width(" ") * 1.1
    lines, cur, cur_w = [], [], 0.0
    for i, w in enumerate(words):
        ww = word_width(w)
        if cur and cur_w + space + ww > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append((i, ww))
        cur_w += ww + (space if len(cur) > 1 else 0)
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        total = sum(ww for _, ww in ln) + space * (len(ln) - 1)
        x = (W + total) / 2  # right edge; RTL: first word on the right
        row = []
        for i, ww in ln:
            x -= ww
            row.append((i, x))
            x -= space
        out.append(row)
    return out


def render(words, active):
    lines = layout(words)
    asc, desc = FONT.getmetrics()
    line_h = int((asc + desc) * 1.08)
    pad_x, pad_y = 34, 18
    img_h = line_h * len(lines) + 2 * pad_y
    xs = [x for row in lines for _, x in row]
    xe = [x + word_width(words[i]) for row in lines for i, x in row]
    left, right = int(min(xs)) - pad_x, int(max(xe)) + pad_x
    im = Image.new("RGBA", (W, img_h + 30), (0, 0, 0, 0))
    # soft shadow + rounded box
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((left + 4, 10, right + 4, img_h + 10), 30, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((left, 4, right, img_h + 4), 30, fill=tuple(C["box_color"]))
    for li, row in enumerate(lines):
        y = 4 + pad_y + li * line_h
        for i, x in row:
            col = tuple(C["highlight_color"]) if i == active else tuple(C["text_color"])
            if i == active:
                ww = word_width(words[i])
                d.rounded_rectangle((x - 10, y + 6, x + ww + 10, y + line_h - 2), 16, fill=(255, 255, 255, 38))
            d.text((x, y), words[i], font=FONT, fill=col, direction="rtl", language="ar",
                   stroke_width=3, stroke_fill=(5, 20, 30, 255))
    return im


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    Image.new("RGBA", (W, CAP_H), (0, 0, 0, 0)).save(os.path.join(OUT, "blank.png"))
    caps = TL["captions"]
    words = TL["words"]
    entries = []
    srt = []
    for ci, cap in enumerate(caps):
        cw = [w for w in words if w["caption"] == ci]
        texts = [w["text"] for w in cw]
        nxt_start = caps[ci + 1]["start"] if ci + 1 < len(caps) else TL["duration"] + 0.6
        end = nxt_start if nxt_start - cap["end"] < MERGE_GAP else cap["end"] + 0.15
        for wi, w in enumerate(cw):
            st = cap["start"] if wi == 0 else w["start"]
            en = cw[wi + 1]["start"] if wi + 1 < len(cw) else end
            name = f"cap_{ci:03d}_{wi:02d}.png"
            im = render(texts, wi)
            canvas = Image.new("RGBA", (W, CAP_H), (0, 0, 0, 0))
            canvas.alpha_composite(im, (0, CAP_H - im.height))
            canvas.save(os.path.join(OUT, name), optimize=True)
            entries.append({"start": round(st, 3), "end": round(en, 3), "file": f"assets/captions/{name}"})
        srt.append(f"{ci + 1}\n{srt_time(cap['start'])} --> {srt_time(end)}\n‫{cap['text']}‬\n")
    json.dump({"width": W, "height": H, "caption_height": CAP_H, "bottom_margin_ratio": C["bottom_margin_ratio"], "entries": entries},
              open(os.path.join(ROOT, "data", "captions.json"), "w", encoding="utf-8"), indent=1)
    os.makedirs(os.path.join(ROOT, "subtitles"), exist_ok=True)
    open(os.path.join(ROOT, "subtitles", "captions_ar.srt"), "w", encoding="utf-8").write("\n".join(srt))
    print(f"[captions] {len(caps)} captions, {len(entries)} word-highlight images -> assets/captions")


if __name__ == "__main__":
    main()
