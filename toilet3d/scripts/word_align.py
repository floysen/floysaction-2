"""Exact word timing from the voiceover with a speech-recognition model.

Runs Whisper (faster-whisper, local, free) on the voiceover with word timestamps,
then matches the recognised words to the words of the script (fuzzy Arabic
matching, so dialect spelling differences are fine).  Every script word gets the
real time it is spoken; the few words the model misses are placed between their
matched neighbours.  The script text itself is never changed.

    python scripts/word_align.py [--model small|medium|large-v3]

Updates data/timeline.json (words, captions, paragraphs) and data/captions.json.
The first run downloads the model once (small ~ 480 MB, medium ~ 1.5 GB).
"""
import argparse
import difflib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TLP = os.path.join(ROOT, "data", "timeline.json")
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))

_KEEP = re.compile(r"[ء-ي]")
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})


def norm(w):
    return "".join(_KEEP.findall(w)).translate(_FOLD)


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def align(script_words, rec):
    """Needleman-Wunsch alignment.  rec = [(text, start, end)].  Returns list of
    (start, end) or None per script word."""
    S = [norm(w) for w in script_words]
    R = [norm(r[0]) for r in rec]
    n, m = len(S), len(R)
    GAP = -0.35
    NEG = -1e9
    dp = [[NEG] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            best, arg = NEG, None
            if i > 0 and j > 0:
                s = sim(S[i - 1], R[j - 1])
                v = dp[i - 1][j - 1] + (s * 2 - 0.6)
                if v > best:
                    best, arg = v, ("m", 1)
                # one script word recognised as two words (e.g. a split prefix)
                if j > 1:
                    s2 = sim(S[i - 1], R[j - 2] + R[j - 1])
                    v = dp[i - 1][j - 2] + (s2 * 2 - 0.6) + GAP * 0.3
                    if v > best:
                        best, arg = v, ("m", 2)
            if i > 0 and dp[i - 1][j] + GAP > best:
                best, arg = dp[i - 1][j] + GAP, ("s", 0)
            if j > 0 and dp[i][j - 1] + GAP > best:
                best, arg = dp[i][j - 1] + GAP, ("r", 0)
            dp[i][j], bt[i][j] = best, arg
    out = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        kind, k = bt[i][j]
        if kind == "m":
            pair = rec[j - k:j]
            score = sim(S[i - 1], "".join(R[j - k:j]))
            if score >= 0.45:
                out[i - 1] = (pair[0][1], pair[-1][2])
            i, j = i - 1, j - k
        elif kind == "s":
            i -= 1
        else:
            j -= 1
    return out


def fill_gaps(words, times, duration):
    """Place unmatched words between matched neighbours, weighted by letter count."""
    n = len(words)
    res = list(times)
    i = 0
    while i < n:
        if res[i] is not None:
            i += 1
            continue
        j = i
        while j < n and res[j] is None:
            j += 1
        t0 = res[i - 1][1] if i > 0 else 0.05
        t1 = res[j][0] if j < n else max(t0 + 0.3 * (j - i), duration - 0.1)
        if t1 - t0 < 0.15 * (j - i):
            t1 = t0 + 0.15 * (j - i)
        wts = [len(norm(w)) + 1.5 for w in words[i:j]]
        tot = sum(wts)
        t = t0
        for k in range(i, j):
            d = (t1 - t0) * wts[k - i] / tot
            res[k] = (t, t + d)
            t += d
        i = j
    # monotonic + minimum length
    for k in range(1, n):
        if res[k][0] < res[k - 1][0] + 0.06:
            res[k] = (res[k - 1][0] + 0.06, max(res[k][1], res[k - 1][0] + 0.18))
    return res


def write_caption_timing(tl):
    """data/captions.json timing from the word list (images w_###.png already exist)."""
    sys.path.insert(0, HERE)
    words = tl["words"]
    hold = 0.5
    entries = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else tl["duration"] + 0.6
        end = nxt if nxt - w["end"] < hold else w["end"] + 0.25
        entries.append({"start": round(w["start"], 3), "end": round(end, 3), "text": w["text"],
                        "file": f"assets/captions/w_{i:03d}.png"})
    json.dump({"center_y_ratio": CFG["captions"]["center_y_ratio"], "entries": entries},
              open(os.path.join(ROOT, "data", "captions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=CFG.get("align_model", "small"))
    a = ap.parse_args()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("[align] faster-whisper is not installed")
    tl = json.load(open(TLP, encoding="utf-8"))
    backup = os.path.join(ROOT, "data", "timeline_pauses.json")
    if not os.path.exists(backup):
        shutil.copy(TLP, backup)
    words = [w["text"] for w in tl["words"]]
    script_text = open(os.path.join(ROOT, CFG["script"]), encoding="utf-8").read()
    print(f"[align] loading Whisper '{a.model}' (downloads once) ...", flush=True)
    try:
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
    except Exception as e:  # no internet / blocked download
        sys.exit(f"[align] could not load the speech model ({type(e).__name__}: {str(e)[:120]})")
    segs, _ = model.transcribe(os.path.join(ROOT, CFG["voiceover"]), language="ar", word_timestamps=True,
                               beam_size=5, initial_prompt=script_text[:220], condition_on_previous_text=False)
    rec = []
    for s in segs:
        for w in s.words or []:
            if norm(w.word):
                rec.append((w.word.strip(), float(w.start), float(w.end)))
    print(f"[align] recognised {len(rec)} words, script has {len(words)}", flush=True)
    times = align(words, rec)
    matched = sum(1 for x in times if x)
    if matched < len(words) * 0.5:
        sys.exit(f"[align] only {matched}/{len(words)} words matched - keeping the previous timing")
    times = fill_gaps(words, times, tl["duration"])
    for w, (st, en) in zip(tl["words"], times):
        w["start"], w["end"] = round(st, 3), round(en, 3)
    for ci, c in enumerate(tl["captions"]):
        ws = [w for w in tl["words"] if w["caption"] == ci]
        c["start"], c["end"] = ws[0]["start"], ws[-1]["end"]
    for p in tl["paragraphs"]:
        ws = [w for w in tl["words"] if w["paragraph"] == p["index"]]
        p["start"], p["end"] = ws[0]["start"], ws[-1]["end"]
    tl["alignment"] = f"whisper-{a.model}: {matched}/{len(words)} words matched exactly"
    json.dump(tl, open(TLP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if CFG["captions"].get("enabled", True):
        write_caption_timing(tl)
    print(f"[align] {matched}/{len(words)} words timed from the audio, the rest placed between them -> data/timeline.json", flush=True)


if __name__ == "__main__":
    main()
