# What If Every Ant on Earth Became Human-Sized? — Three.js animation

A deterministic, procedurally built 3D animation (1080×1920, 30 fps, 60 s), rendered headlessly to `final-animation.mp4`.
No textures, stock footage or AI video are used. Every model is built from code.

## Commands
```bash
npm install                 # three@0.169.0 + playwright (uses the system Chromium)
npm run preview             # http://localhost:5173/index.html  (?t=34.5 holds a frame)
npm run render              # captures frames/f_00000.jpg … f_01799.jpg (3 parallel workers; resumable)
npm run encode              # H.264, yuv420p → final-animation.mp4 (muxes voiceover.wav/mp3/m4a if present)
npm run verify              # ffprobe report, full decode test, black-frame scan, contact-sheet.jpg
```
To render only selected frames: `node scripts/render.mjs --list 0,450,900 --out /tmp/check`.

## Determinism
`renderFrame(frameIndex)` derives `t = frameIndex / 30` and sets every object, light, camera and overlay from `t` only.
Randomness uses seeded PRNGs. Nothing accumulates frame to frame, so frames can be rendered in any order or in parallel.

## Source layout
| File | Responsibility |
|---|---|
| `src/timeline.js` | Master timeline: segments and timed narration lines |
| `src/models.js` | Procedural models: ant (6 legs, elbowed antennae, spiracles), crowd LOD, human, dog, oak, tram, buildings, props |
| `src/world.js` | The park: layout, sky, sun/shadow rig, segment-6 time-lapse (dry patches, seeds, aphids, wilting flowers) |
| `src/actors.js` | Hero ants, emergence craters, instanced crowd and piles, people, tram |
| `src/cutaway.js` | Segment-2 soil cross-section with nest tunnels |
| `src/globe.js` | Segment-3 globe; continents tint as the "all of Earth's land" line plays |
| `src/xray.js` | Segment-4 X-ray: spiracles → tracheae, slow O₂ particles, muscles dimming |
| `src/camera.js` | Shot list with eased and log-distance camera moves |
| `src/overlay.js` | On-screen text and the 1 m² inset |
| `scripts/*` | Static server, Playwright frame capture, ffmpeg encode, verification |

No narration audio was supplied, so the video is silent. See `NARRATION_GUIDE.md` for line timings.
