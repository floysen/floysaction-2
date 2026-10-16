# Toilet video: «حفرة في حوش بيتك ← دورة مياه»

A vertical educational short (1080×1920, 30 fps, H.264 + AAC) in the style of the
"How a … Becomes a …" reference videos. It uses the same fixed cut-away "diorama" view: the yard and house at the top,
the ground sliced open below, and simple shaded objects that look slightly 3D but keep a clean 2D style.
The captions copy the references too: **one bold white word at a time with a dark outline**, popping in on each spoken word.

Every frame is drawn by Python code with the **Cairo** 2D graphics library. There is no Blender, no 3D software,
no cloud service and no manual editing. The narration is your original voiceover.

## Render it (Windows, Git Bash)

1. Copy this `video-project` folder to your PC (about 1 GB free is plenty).
2. Right-click inside the folder and choose **Open Git Bash here**.
3. Run:

```bash
bash render.sh
```

The finished video is at **`output/toilet_final.mp4`**. On a normal PC it takes about **5–15 minutes**.

On the first run, `install.sh` sets up everything inside the folder, one time only:

* **uv** (a small Python installer) → a private **Python 3.12** in `tools/` + `.venv/` with `numpy` and `pycairo`.
  It doesn't touch any Python you already have.
* **FFmpeg** in `tools/`, unless `ffmpeg` is already on your PATH.

## Options

| Command | What it does |
|---|---|
| `bash render.sh` | Full quality 1080×1920 → `output/toilet_final.mp4` |
| `bash render.sh --preview` | Half resolution, about 4× faster → `output/toilet_preview.mp4` |
| `bash render.sh --workers 2` | Use fewer CPU cores (default: all but one) |
| `bash render.sh --realign` | Re-run the speech-recognition word timing |
| `bash render.sh --no-align` | Skip the word timing step |
| `bash render.sh --clean` | Delete the rendered pieces and render again from scratch |

**Stopping and resuming:** press **Ctrl+C** at any time. Run the same command again and it continues;
finished 4-second pieces (`build/chunks_*`) are kept. If you change any code or timing, `render.sh`
notices and re-renders on its own.

Settings live in `project-config.json`: caption size, outline, colour and height (`captions`), audio levels (`audio`)
and output quality (`crf`: lower means better and bigger).

## How it works

```
render.sh ─► install.sh (Python + pycairo + numpy + FFmpeg)
          └► engine/render.py
               ├─ frames: engine/frame.py → world.py (the story) + draw.py (drawing toolkit)
               │          rendered in parallel, piped to FFmpeg in 4-second chunks
               ├─ audio:  scripts/mix_audio.py → original voiceover + 52 timed sound effects
               └─ final:  join chunks + audio → loudness −14 LUFS → automatic checks
```

The final checks are: H.264, 1080×1920, 30 fps, yuv420p, AAC 48 kHz, duration at least the voiceover length, and a full decode with no errors.

* **Timing:** `data/timeline.json` aligns your script to your voiceover by finding the real pauses in the audio.
  Every story event (outhouse, smell, flies, toilet, drain, sewer, bucket, sewer gas, S-trap, siphon, gurgle,
  tank/flapper/float, dry trap, vent stack, roof, seat and lid) is keyed to the actual spoken word in `scripts/shotplan.py`.
* **Sets:** the yard with the outhouse; the house cut-away (bathroom, toilet in section, drain, street and sewer main,
  vent stack); and the rooftop. Depth comes from lit 3D boxes, soft contact shadows, corner shading, background haze,
  glossy porcelain and a light vignette.
* **Exact word timing:** on the first run, `render.sh` installs `faster-whisper` and runs a Whisper speech model
  (`small`, about 480 MB, downloaded once) on your voiceover with `scripts/word_align.py`. It finds the real moment each
  word is spoken and matches the words to your script, so the captions and the on-screen events line up with the voice.
  It takes about 1–3 minutes, only once. `bash render.sh --realign` re-runs it. For even better accuracy, set
  `"align_model": "medium"` in `project-config.json`. If it can't run (no internet), the earlier pause-based timing is used.
* **Captions are turned off** (`"captions": {"enabled": false}` in `project-config.json`), so you can add your own.
  `subtitles/captions_ar.srt` has the phrase timing if it helps. Set `enabled` to `true` to bring the built-in captions back.
* **Built-in captions (when enabled):** `assets/captions/w_*.png` holds one image per spoken word. They're shaped with HarfBuzz, so the Arabic letters
  join correctly and read right-to-left. They're pre-made, so your PC needs no special Arabic text support.
  `subtitles/captions_ar.srt` has plain phrase subtitles if you need them for upload.
* **Sound:** 31 sound effects synthesised by code (`assets/sound-effects/`) are mixed under your voice.
  There is no music and no ambient bed.

## Project layout

```
video-project/
├── render.sh / install.sh      ← the one command, and its installer
├── project-config.json         ← caption style, audio levels, quality
├── requirements.txt            ← numpy, pycairo
├── engine/
│   ├── draw.py                 ← camera, shading, gradients, textures (soil, lawn, clouds)
│   ├── world.py                ← every scene element and its animation
│   ├── frame.py                ← camera zooms, scene transitions, captions
│   └── render.py               ← parallel chunked renderer + encode + verification
├── scripts/
│   ├── shotplan.py             ← story events + sound cues from the narration timing
│   ├── align_captions.py       ← script ↔ voiceover alignment
│   ├── make_captions.py        ← word caption images (needs Pillow + raqm; only to regenerate)
│   ├── make_sfx.py             ← sound effect synthesiser
│   └── mix_audio.py            ← audio mix
├── assets/  audio/voiceover.mp3 · fonts/Cairo-ExtraBold.ttf (OFL) · captions/ · sound-effects/
├── data/    script_ar.txt · timeline.json · captions.json
└── output/  ← final MP4
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `download failed` | Check your internet connection and re-run. Or install `uv` (https://docs.astral.sh/uv/) and/or FFmpeg yourself. |
| FFmpeg is installed somewhere unusual | `FFMPEG="/d/ffmpeg/bin/ffmpeg.exe" bash render.sh` (ffprobe must be next to it) |
| `\r: command not found` | The `.sh` files got Windows line endings. Run `sed -i 's/\r$//' *.sh` once. |
| The PC is too busy while rendering | `bash render.sh --workers 2` |
| Antivirus blocks `uv.exe` or `ffmpeg.exe` in `tools/` | Allow them, or install Python 3.10+ with `pip install numpy pycairo` and FFmpeg yourself. |
| Something looks wrong in one shot | Render a single frame to check it: `.venv/Scripts/python -c "import sys; sys.path.insert(0,'engine'); import frame; frame.render(12.5).write_to_png('test.png')"` |

## Regenerating assets (optional)

Only needed if you change the script, voiceover or caption style. It needs `pip install pillow numpy`, with a Pillow that includes libraqm:

```bash
python scripts/align_captions.py   # new voiceover or script
python scripts/make_captions.py    # caption text/style
python scripts/make_sfx.py         # sound effects
bash render.sh
```
