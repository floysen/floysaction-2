"""Mix the original voiceover with the timed sound effects -> build/mix.wav

Uses only numpy + the standard library, so it runs in Blender's bundled Python:
    blender -b --factory-startup --python scripts/mix_audio.py
or any Python with numpy:
    python scripts/mix_audio.py

The voiceover samples are not edited: the narration plays from t=0 at its
original level and the effects are added underneath it.
"""
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import shotplan as SP  # noqa: E402

SR = 48000


def ffmpeg():
    return os.environ.get("FFMPEG", "ffmpeg")


def read_voice():
    path = os.path.join(ROOT, SP.CFG["voiceover"])
    raw = subprocess.run([ffmpeg(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR, path
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return data


def db(g):
    return 10 ** (g / 20.0)


def main():
    voice = read_voice() * db(SP.CFG["audio"]["voice_gain_db"])
    n = int(SP.DURATION * SR)
    bed = np.zeros(n, dtype=np.float32)
    cache = {}
    for t, name, gain in SP.sfx_cues():
        if name not in cache:
            cache[name] = read_wav(os.path.join(ROOT, "assets", "sound-effects", name))
        s = cache[name] * db(gain)
        i = int(max(t, 0) * SR)
        j = min(n, i + len(s))
        bed[i:j] += s[: j - i]
    # gentle ducking of effects while the narrator is speaking (voice stays untouched)
    win = int(0.05 * SR)
    v = np.zeros(n, dtype=np.float32)
    v[: min(n, len(voice))] = voice[:n]
    envl = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, mode="same"))
    duck = 1.0 - 0.45 * np.clip(envl / 0.05, 0, 1)
    bed *= duck * db(SP.CFG["audio"]["sfx_gain_db"])
    mix = v + bed
    peak = float(np.max(np.abs(mix)))
    if peak > 0.98:
        # soft limiting only on the rare overs, never re-levels the whole voice
        over = np.abs(mix) > 0.9
        mix[over] = np.sign(mix[over]) * (0.9 + 0.08 * np.tanh((np.abs(mix[over]) - 0.9) / 0.08))
    stereo = np.repeat(mix[:, None], 2, axis=1)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    out = os.path.join(ROOT, "build", "mix.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(stereo, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"[audio] {len(SP.sfx_cues())} sound cues mixed under the voiceover -> build/mix.wav ({n / SR:.2f}s)")


if __name__ == "__main__":
    main()
