"""Synthesise every sound effect procedurally (no downloaded samples, no licences).

    python scripts/make_sfx.py      -> assets/sound-effects/*.wav  (48 kHz mono)

The WAV files are committed with the project; re-run only to tweak sounds.
"""
import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sound-effects")
SR = 48000
rng = np.random.default_rng(1234)


def t_axis(d):
    return np.arange(int(SR * d)) / SR


def env(d, a=0.005, r=0.2, shape=3.0):
    t = t_axis(d)
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-shape * t / max(r, 1e-4))
    return e


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def bandpass(x, lo, hi):
    return lowpass(highpass(x, lo), hi)


def noise(d):
    return rng.standard_normal(int(SR * d))


def fade(x, fi=0.005, fo=0.05):
    n = len(x)
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def write(name, x):
    x = fade(norm(x.astype(np.float64)))
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("  ", name, f"{len(x) / SR:.2f}s")


def bubbles(d, rate, f_lo=400, f_hi=1400, decay=40):
    out = np.zeros(int(SR * d))
    n = int(rate * d)
    for _ in range(n):
        st = rng.integers(0, len(out) - SR // 10)
        f0 = rng.uniform(f_lo, f_hi)
        dur = rng.uniform(0.02, 0.07)
        t = t_axis(dur)
        f = f0 * (1 + 2.5 * t / dur)  # rising chirp = bubble
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-decay * t)
        out[st:st + len(b)] += b * rng.uniform(0.3, 1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    print("[sfx] synthesising:")
    # shovel into soil: crunchy filtered noise + low thud
    d = 0.35
    x = bandpass(noise(d), 200, 3000) * env(d, 0.003, 0.08, 4) + 0.6 * np.sin(2 * np.pi * 70 * t_axis(d)) * env(d, 0.002, 0.05, 5)
    write("dig.wav", x)
    # water pouring: band noise with bubbling, sustained
    d = 1.6
    x = bandpass(noise(d), 300, 2500) * 0.5 + bubbles(d, 120, 300, 900) * 0.5
    write("water_pour.wav", x * np.minimum(1, t_axis(d) / 0.15))
    # splash: bright burst + bubbles
    d = 0.9
    x = highpass(noise(d), 400) * env(d, 0.002, 0.18, 3) + bubbles(d, 60, 500, 1600) * np.exp(-3 * t_axis(d)) * 0.6
    write("splash.wav", x)
    # sparkle / chime
    d = 1.2
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-k * t) * a for f, k, a in
            ((1568, 4, 1), (2093, 5, 0.8), (2637, 6, 0.6), (3136, 7, 0.4)))
    for i, off in enumerate((0, 0.08, 0.16)):
        s = int(off * SR)
        x[s:] += 0.5 * np.sin(2 * np.pi * (2349 + i * 300) * t[: len(x) - s]) * np.exp(-6 * t[: len(x) - s])
    write("sparkle.wav", x)
    # whoosh transition
    d = 0.7
    t = t_axis(d)
    n = noise(d)
    x = bandpass(n, 300, 2500) * np.sin(np.pi * t / d) ** 2
    write("whoosh.wav", x)
    # dripping / seeping
    d = 2.2
    x = bubbles(d, 9, 900, 1800, 60)
    write("drips.wav", x)
    # wall collapse: rumble + falling debris
    d = 1.8
    t = t_axis(d)
    x = lowpass(noise(d), 180) * 3 * np.exp(-1.2 * t) + bandpass(noise(d), 500, 4000) * 0.3 * np.exp(-2 * t)
    for _ in range(25):
        s = rng.integers(0, int(SR * 1.5))
        k = bandpass(noise(0.05), 300, 3000) * env(0.05, 0.001, 0.02, 4)
        x[s:s + len(k)] += k * rng.uniform(0.3, 0.8)
    write("crumble.wav", x)
    # rebar clank: inharmonic metal partials
    d = 0.8
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-k * t) for f, k in ((523, 6), (1390, 8), (2780, 10), (4120, 14)))
    x += highpass(noise(d), 2000) * env(d, 0.001, 0.01, 5) * 2
    write("metal_clank.wav", x)
    # shotcrete spray: hiss + pump pulsing
    d = 2.6
    t = t_axis(d)
    x = highpass(noise(d), 1500) * (0.7 + 0.3 * np.sin(2 * np.pi * 6 * t)) + 0.3 * lowpass(noise(d), 150)
    write("spray.wav", x * np.minimum(1, t / 0.1))
    # draining gurgle
    d = 1.6
    t = t_axis(d)
    x = bubbles(d, 60, 150, 500, 25) + lowpass(noise(d), 300) * 0.4
    write("drain_gurgle.wav", x)
    # groundwater rumble
    d = 2.0
    t = t_axis(d)
    x = lowpass(noise(d), 90) * 4 * np.sin(np.pi * t / d) + 0.4 * np.sin(2 * np.pi * 45 * t) * np.sin(np.pi * t / d)
    write("underground_rumble.wav", x)
    # pool lifting: creaking stress + grinding
    d = 2.0
    t = t_axis(d)
    f = 90 + 30 * np.sin(2 * np.pi * 1.3 * t)
    saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
    x = lowpass(saw, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)) + bandpass(noise(d), 100, 800) * 0.5
    write("lift_creak.wav", x * np.sin(np.pi * t / d) ** 0.5)
    # valve click
    d = 0.18
    t = t_axis(d)
    x = highpass(noise(d), 1500) * env(d, 0.0005, 0.008, 5) + np.sin(2 * np.pi * 1800 * t) * env(d, 0.0005, 0.03, 4) * 0.6
    write("valve_click.wav", x)
    # bubbles
    d = 1.8
    write("bubbles.wav", bubbles(d, 70, 300, 1100))
    # pump start: motor spin-up hum
    d = 2.2
    t = t_axis(d)
    f = 30 + 70 * (1 - np.exp(-2.5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph) + 0.15 * bandpass(noise(d), 400, 1500)
    write("pump_start.wav", x)
    # water rushing through pipes
    d = 2.2
    t = t_axis(d)
    x = bandpass(noise(d), 150, 900) * (0.8 + 0.2 * np.sin(2 * np.pi * 2 * t)) + bubbles(d, 25, 200, 600) * 0.3
    write("pipe_flow.wav", x * np.minimum(1, t / 0.3))
    # clean water shimmer (gentle glassy tones)
    d = 1.6
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-2 * t) for f in (1047, 1319, 1568)) * 0.4 + bandpass(noise(d), 2000, 6000) * 0.15 * np.exp(-2 * t)
    write("water_shimmer.wav", x)
    # leaves rustling
    d = 1.3
    t = t_axis(d)
    x = highpass(noise(d), 2500) * (np.abs(np.sin(2 * np.pi * 3 * t)) ** 3 * 0.8 + 0.2) * np.sin(np.pi * t / d)
    write("leaves.wav", x)
    # pebble plop
    d = 0.4
    t = t_axis(d)
    f = 700 * np.exp(-6 * t) + 250
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.001, 0.12, 3) + highpass(noise(d), 1000) * env(d, 0.001, 0.02, 4) * 0.5
    write("plop.wav", x)
    # return jets
    d = 2.0
    t = t_axis(d)
    x = bandpass(noise(d), 600, 3500) * 0.6 + bubbles(d, 40, 600, 1500) * 0.4
    write("jets.wav", x * np.minimum(1, t / 0.2))
    # swirl
    d = 2.2
    t = t_axis(d)
    cutoff_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.9 * t)
    x = bandpass(noise(d), 200, 1200) * cutoff_mod + bandpass(noise(d), 1200, 3000) * (1 - cutoff_mod) * 0.4
    write("swirl.wav", x * np.sin(np.pi * t / d))
    # chlorine fizz
    d = 1.8
    t = t_axis(d)
    x = highpass(noise(d), 3000) * (0.6 + 0.4 * rng.random(len(t)) ** 8) + bubbles(d, 160, 1500, 4000, 90) * 0.4
    write("fizz.wav", x * np.minimum(1, t / 0.05))
    # bacteria zap
    d = 0.5
    t = t_axis(d)
    f = 1800 * np.exp(-5 * t) + 200
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(d, 0.001, 0.2, 3) * 0.4
    write("zap.wav", lowpass(x, 5000))
    # sniff (two short inhales)
    d = 0.9
    x = np.zeros(int(SR * d))
    for off in (0.0, 0.32):
        s = int(off * SR)
        k = bandpass(noise(0.26), 900, 5000) * np.sin(np.pi * t_axis(0.26) / 0.26) ** 2
        x[s:s + len(k)] += k
    write("sniff.wav", x)
    # molecular reaction pop
    d = 0.7
    t = t_axis(d)
    f = 300 + 900 * (1 - np.exp(-12 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.002, 0.25, 3) + bubbles(d, 30, 800, 2000) * 0.3
    write("reaction_pop.wav", x)
    # tile clack (ceramic)
    d = 0.25
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-k * t) for f, k in ((1900, 40), (3300, 55), (5200, 70))) + highpass(noise(d), 3000) * env(d, 0.0005, 0.006, 4)
    write("tile_clack.wav", x)
    # diving board boing
    d = 1.4
    t = t_axis(d)
    f = 110 + 25 * np.sin(2 * np.pi * 5 * t) * np.exp(-2 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.2 * t) + 0.4 * highpass(noise(d), 1500) * env(d, 0.001, 0.02, 4)
    write("board_boing.wav", x)
    # flies buzzing (several detuned buzzers with wandering pitch)
    d = 2.6
    t = t_axis(d)
    x = np.zeros_like(t)
    for k in range(4):
        f = 190 + 40 * k + 25 * np.sin(2 * np.pi * (0.7 + 0.3 * k) * t + k)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x += np.sign(np.sin(ph)) * (0.5 + 0.5 * np.sin(2 * np.pi * (1.1 + 0.4 * k) * t + k)) * 0.25
    write("flies.wav", lowpass(x, 2500) * np.sin(np.pi * t / d) ** 0.4)
    # sewer gas hiss (breathy, rising)
    d = 1.8
    t = t_axis(d)
    x = bandpass(noise(d), 500, 3000) * np.sin(np.pi * t / d) + 0.3 * lowpass(noise(d), 120) * np.sin(np.pi * t / d)
    write("gas_hiss.wav", x)
    # toilet flush: roaring rush that swirls, then gurgles out
    d = 2.6
    t = t_axis(d)
    x = bandpass(noise(d), 120, 1800) * np.minimum(1, t / 0.15) * np.exp(-0.6 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 3 * t))
    x += bubbles(d, 80, 150, 600, 25) * np.clip((t - 1.2) / 0.8, 0, 1) * 0.8
    write("flush.wav", x)
    # breathing air (soft in/out)
    d = 1.6
    x = np.zeros(int(SR * d))
    for off, ln in ((0.0, 0.7), (0.8, 0.7)):
        s = int(off * SR)
        k = bandpass(noise(ln), 400, 3500) * np.sin(np.pi * t_axis(ln) / ln) ** 2
        x[s:s + len(k)] += k
    write("breath.wav", x)
    print(f"[sfx] done -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
