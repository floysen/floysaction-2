"""Align the supplied Arabic script to the supplied voiceover.

No cloud service or speech model is needed: the voiceover's energy envelope is
analysed to find the real pauses, and the script's caption chunks are snapped
to those pauses with a dynamic-programming search that also respects the
expected speaking length of every chunk (Arabic letter count).

Output: data/timeline.json
  {
    "duration": <seconds of voiceover>,
    "paragraphs": [{"index", "start", "end"}],
    "captions":   [{"text", "start", "end", "paragraph"}],
    "words":      [{"text", "start", "end", "paragraph", "caption"}]
  }

The generated timeline.json is committed with the project, so this script only
needs to be re-run if the voiceover or script changes:
    python scripts/align_captions.py
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "project-config.json"), encoding="utf-8"))
VOICE = os.path.join(ROOT, CFG["voiceover"])
SCRIPT = os.path.join(ROOT, CFG["script"])
OUT = os.path.join(ROOT, "data", "timeline.json")

SR = 16000
HOP = 0.01  # 10 ms analysis frames
MAX_WORDS_PER_CAPTION = 5
ARABIC_LETTER = re.compile(r"[ء-ي]")


def ffmpeg_bin():
    return os.environ.get("FFMPEG", "ffmpeg")


def load_audio(path):
    cmd = [ffmpeg_bin(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def envelope_db(sig):
    hop = int(SR * HOP)
    n = len(sig) // hop
    frames = sig[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    # light smoothing (50 ms) so plosive gaps inside a word are not pauses
    k = np.ones(5) / 5
    return np.convolve(db, k, mode="same")


def find_pauses(db):
    """Return list of (centre_time, duration) of low-energy runs."""
    ref = np.percentile(db, 95)
    thr = ref - 24.0
    low = db < thr
    pauses = []
    i = 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            dur = (j - i) * HOP
            if dur >= 0.10:
                pauses.append(((i + j) / 2 * HOP, dur, i * HOP, j * HOP))
            i = j
        else:
            i += 1
    return pauses, low


def speech_bounds(low):
    idx = np.where(~low)[0]
    return idx[0] * HOP, (idx[-1] + 1) * HOP


def tokenize(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    captions = []  # list of (words, paragraph_index, strength_of_end)
    for pi, para in enumerate(paragraphs):
        # split into phrases on punctuation, keeping the punctuation
        phrases = re.findall(r"[^،,.!؟?…]+(?:\.\.\.|[،,.!؟?…])*", para)
        for ph in phrases:
            words = ph.split()
            if not words:
                continue
            end_mark = ph.strip()[-1]
            strength = 2 if end_mark in ".!؟?…" else 1
            # break long phrases into balanced chunks
            n = max(1, -(-len(words) // MAX_WORDS_PER_CAPTION))
            size = -(-len(words) // n)
            for c in range(n):
                chunk = words[c * size:(c + 1) * size]
                if chunk:
                    captions.append((chunk, pi, strength if c == n - 1 else 0))
    return paragraphs, captions


def word_weight(w):
    return len(ARABIC_LETTER.findall(w)) + 1.5


def main():
    sig = load_audio(VOICE)
    duration = len(sig) / SR
    db = envelope_db(sig)
    pauses, low = find_pauses(db)
    s0, s1 = speech_bounds(low)
    paragraphs, caps = tokenize(open(SCRIPT, encoding="utf-8").read())

    # expected boundary times, in "speech time" (pauses removed) mapped back to real time
    weights = [sum(word_weight(w) for w in c[0]) for c in caps]
    total_w = sum(weights)

    # DP over captions: every caption group starts right after a real pause and ends right
    # before a real pause; a group may hold 1-3 captions (inner boundaries are then split by
    # letter weight).  Cost = mismatch between real and expected duration + structure terms.
    cand = [p for p in pauses if s0 + 0.2 < p[0] < s1 - 0.2]
    # node 0 = speech start, nodes 1..m = pauses, node m+1 = speech end
    node_start = [s0] + [p[3] for p in cand] + [None]
    node_end = [None] + [p[2] for p in cand] + [s1]
    node_dur = [0.0] + [p[1] for p in cand] + [0.0]
    m = len(cand) + 1
    n = len(caps)
    rate = (s1 - s0 - sum(p[1] for p in cand) * 0.6) / total_w
    INF = 1e18
    dp = np.full((n + 1, m + 1), INF)
    back = {}
    dp[0, 0] = 0.0
    for i in range(n):
        for c0 in range(m):
            if dp[i, c0] >= INF:
                continue
            st = node_start[c0]
            for k in (1, 2, 3):
                if i + k > n:
                    break
                exp = sum(weights[i:i + k]) * rate
                inner_strong = sum(1 for q in range(i, i + k - 1) if caps[q][2] == 2)
                for c1 in range(c0 + 1, m + 1):
                    en = node_end[c1]
                    dur = en - st
                    if dur <= 0.15:
                        continue
                    if dur > exp * 3 + 2:
                        break
                    if (i + k == n) != (c1 == m):
                        continue
                    cost = 4.0 * abs(np.log(dur / exp)) + 1.2 * (k - 1) + 3.0 * inner_strong
                    # pauses skipped inside the group are wasted pauses
                    cost += 0.8 * sum(node_dur[c0 + 1:c1]) / 0.25
                    if c1 < m:
                        strength = caps[i + k - 1][2]
                        cost -= node_dur[c1] * (3.0 if strength == 2 else 1.5 if strength == 1 else 0.2)
                    v = dp[i, c0] + cost
                    if v < dp[i + k, c1]:
                        dp[i + k, c1] = v
                        back[(i + k, c1)] = (i, c0)
    starts, ends = [0.0] * n, [0.0] * n
    i, c = n, m
    snapped = 0
    while i > 0:
        pi_, pc = back[(i, c)]
        st, en = node_start[pc], node_end[c]
        ws = weights[pi_:i]
        t = st
        for q, w in zip(range(pi_, i), ws):
            d = (en - st) * w / sum(ws)
            starts[q], ends[q] = t, t + d
            t += d
        snapped += 1
        i, c = pi_, pc
    nb = n - 1
    snapped -= 1

    captions, words = [], []
    for i, (cw, pi, _) in enumerate(caps):
        st, en = round(starts[i], 3), round(ends[i], 3)
        captions.append({"text": " ".join(cw), "start": st, "end": en, "paragraph": pi})
        ww = [word_weight(w) for w in cw]
        t = st
        for w, wt in zip(cw, ww):
            d = (en - st) * wt / sum(ww)
            words.append({"text": w, "start": round(t, 3), "end": round(t + d, 3),
                          "paragraph": pi, "caption": i})
            t += d
    paras = []
    for pi in range(len(paragraphs)):
        cs = [c for c in captions if c["paragraph"] == pi]
        paras.append({"index": pi, "start": cs[0]["start"], "end": cs[-1]["end"],
                      "text": paragraphs[pi]})
    json.dump({"duration": round(duration, 3), "speech_start": round(s0, 3),
               "speech_end": round(s1, 3), "paragraphs": paras,
               "captions": captions, "words": words},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[align] {len(captions)} captions, {snapped}/{nb} boundaries snapped to real pauses, "
          f"voice {duration:.2f}s -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
