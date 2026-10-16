# Toilet video, realistic 3D: «حفرة في حوش بيتك ← دورة مياه»

This is a realistic 3D cut-away explainer (1080×1920, 30 fps, H.264/AAC) in the style of the reference videos. It has:

* **Real 3D sets:** a Saudi villa yard with an outhouse over a pit, a house cut open with the bathroom, the toilet in
  cross-section, the drain under the slab, the street and sewer main, the vent stack through the roof, and the rooftop.
* **Realistic materials:** generated photo-like textures with colour, bump and roughness maps for eroded soil, grass,
  concrete, asphalt, plaster, tiles, wood, brick and sandstone. The porcelain is glossy and the water is clear.
* **Realistic lighting:** sun with soft shadows, sky-based ambient light, ambient occlusion (N8AO), distance haze
  and filmic tone mapping.
* **Cinematic camera:** continuous dolly, crane and tracking moves with real parallax, a subtle hand-held drift and
  clean cuts between sets.
* **Your voiceover**, with 50 synchronised sound effects and no music.
* **One-word Arabic captions**, drawn by the browser with correct Arabic shaping and timed to your actual speech.

## Render (Windows, Git Bash)

```bash
bash render.sh --preview   # optional: half resolution, quick check  -> output/toilet_preview.mp4
bash render.sh             # final video                             -> output/toilet_final.mp4
```

On the first run, `install.sh` sets up everything inside this folder only:
**Node.js** and the three.js packages, a private **Python** (audio mix and word timing), **FFmpeg**, and the speech
model used for word timing (about 480 MB). Rendering uses **Microsoft Edge** (built into Windows) or Chrome to draw
the 3D scene **on your graphics card**.

* **Render time:** depends on your GPU. Roughly 5–20 frames per second on a typical gaming or recent laptop GPU, so
  about 3–10 minutes for the 2,618 frames. Integrated graphics are slower. Progress and ETA are printed per chunk.
* **Stop and resume:** Ctrl+C is safe. Run the same command again and finished 3-second chunks are kept.
* **No GPU found?** If the log shows `GPU: ... SwiftShader`, the browser fell back to software rendering, which works
  but is very slow. Update your graphics driver, or close other GPU-heavy programs.

## How it works

```
render.sh
 ├─ install.sh                 Node + three.js, Python, FFmpeg, checks Edge/Chrome
 ├─ scripts/word_align.py      exact word times from the voiceover (Whisper, runs once)
 ├─ scripts/shotplan.py        story events keyed to spoken words -> data/events.json
 ├─ tools/render.mjs           opens web/index.html in Edge/Chrome (GPU), renders every frame,
 │                             pipes JPEG frames into FFmpeg in resumable chunks
 ├─ scripts/mix_audio.py       voiceover + timed sound effects
 └─ scripts/assemble.py        join chunks + audio, loudness -14 LUFS, checks
web/
 ├─ lib/engine.js              lighting, sky, materials, cut-away ground, trees, palms, camera paths, captions
 ├─ scenes/toilet.js           every set, object, animation and camera move of this video
 └─ textures/                  generated PBR textures (tools/make_textures.py)
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Microsoft Edge or Google Chrome is required` | Install Chrome, or set `BROWSER="C:\path\to\chrome.exe"` before `bash render.sh` |
| Very slow (`SwiftShader` in the log) | The GPU isn't being used. Update the graphics driver and close other 3D apps. |
| `download failed` | Check your internet connection and run again. Downloads are one-time only. |
| `\r: command not found` | Run `sed -i 's/\r$//' *.sh` once |
| Captions slightly off | Run `bash render.sh --realign`, or set `"align_model": "medium"` in `project-config.json` |
| Re-render everything | `bash render.sh --clean` |
