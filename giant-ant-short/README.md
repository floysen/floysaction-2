# Giant Ant Short — "A Human-Sized Ant Is Outside Your Door"

This is a 3D YouTube Short built entirely in Three.js. It renders to **1080×1920 at 30 fps, 31.0 s (930 frames)**, encoded as H.264 / yuv420p. The output is `final-animation.mp4`.

The source of truth is **Script 2 (Immediate danger)**. The MP4 is **silent**. Record the voiceover with `narration-guide.srt` as a timing guide, then mux it in (see below).

## Commands

```bash
npm install                 # three@0.170.0 + playwright@1.56.1
npm run preview             # open http://localhost:5173/?preview   (single frame: /?frame=450)
npm run validate            # rig part counts, timeline coverage, camera-inside-geometry checks
npm run render              # validate -> render all 930 frames -> encode final-animation.mp4 -> QA
npm run stills -- 0,300,600 # render chosen frames to out/stills for inspection
npm run inspect             # ffprobe + blackdetect + contact sheet (out/contact-sheet.jpg)
```

Rendering uses headless Chromium with SwiftShader (software WebGL), so it needs no GPU and gives the same result on any machine. If Playwright can't find its browser, set `CHROMIUM_PATH=/path/to/chromium`.

### Adding the voiceover later
The animation timing is fixed. Mux the audio without re-encoding the video:
```bash
ffmpeg -i final-animation.mp4 -i voiceover.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest final-with-vo.mp4
```

## Project layout
| File | Purpose |
|---|---|
| `src/timeline.js` | Master clock (FPS, duration), narration timestamps, easing helpers, seeded PRNG |
| `src/shots.js` | Shot list (camera per shot), every character and prop state as a pure function of time, on-screen text |
| `src/characters/ant.js` | Ant rig: 6 legs with analytic two-bone IK, elbowed antennae, cracks, x-ray breathing tubes with air particles |
| `src/characters/human.js` | "You": 1 head, 2 arms, 2 hands, 2 legs, 2 feet, all hung from joint groups |
| `src/env/street.js` | Night street, apartment interior, car with hinged door, lamps, instanced rain and windows |
| `src/env/lab.js` | Abstract scale-comparison stage: multi-scale grid, coin, weight and strength bars |
| `src/overlay.js` | HTML captions, 3D-anchored labels and the height-comparison guide (captured with each frame) |
| `src/validate.js` | Scene-graph and timeline validation |
| `scripts/render.mjs` | Deterministic frame capture (Playwright) followed by FFmpeg encoding |

## Determinism
Every animated value is a pure function of `t = frame / 30`. There is no real-time clock, no physics engine and no unseeded randomness. Random layouts (rain, buildings, cracks, debris) come from fixed-seed PRNGs at build time. `window.renderFrame(n)` always produces the same image for frame `n`.

## Shot list (synced to the estimated narration)
| Time | Narration | Shot |
|---|---|---|
| 0.0–1.6 | You hear it before you see it. | Dark apartment; push toward "you" at the rainy window |
| 1.6–3.2 | Clicking. | Over the shoulder through the glass: a giant ant passes behind the parked car |
| 3.2–5.3 | Hundreds of legs on concrete. | Ground-level tracking: feet strike wet concrete with splash rings; more ants in the distance |
| 5.3–6.8 | Outside your window, | Over the shoulder: the ant stops and turns its head to the window; "you" flinch |
| 6.8–8.0 | an ant as tall as you | Street view at head height: dashed guide links both head tops. **AS TALL AS YOU** |
| 8.0–9.4 | grabs a car door | Over the car: the ant steps in and hooks the door handle with a front leg |
| 9.4–10.8 | and pulls… | The door swings open with tug-jerks; the ant leans back |
| 10.8–12.4 | and its leg snaps. | Close-up: the tibia breaks at mid-joint, chitin chips fly, controlled shake, body sags |
| 12.4–14.6 | Grow an ant 500× taller, | Lab: a 3 mm ant beside a coin grows to human size; counter ×1 → ×500 |
| 14.6–16.6 | …125 million times heavier. | The WEIGHT bar shoots up out of frame; counter to ×125,000,000 |
| 16.6–18.6 | (continued) | A weight arrow presses down; the legs splay and tremble under the load |
| 18.6–20.2 | Its muscles? Only a quarter-million times stronger. | Macro: the tiny green STRENGTH bar at the foot of the weight bar; ×250,000 |
| 20.2–21.8 | (continued) | Pull back: both bars and the ant. "= 500× WEAKER FOR ITS WEIGHT" |
| 21.8–23.9 | Its shell starts to crack. | Back on the street: cracks race across the abdomen and thorax, flakes fall |
| 23.9–26.6 | Its body can't pull in enough air. | X-ray: the shell fades; air enters the breathing tubes but stalls before the red core. **NO LUNGS** |
| 26.6–28.6 | The invasion collapses | The ant staggers and collapses with its head on your doorstep |
| 28.6–31.0 | right on your doorstep. | Crane up: the whole street of collapsed giant ants. **TOO BIG TO SURVIVE** |

## Accuracy notes
- 500× taller means 500³ = 125,000,000× the weight but only 500² = 250,000× the muscle cross-section. Strength-to-weight therefore drops 500×. This is simplified square-cube scaling.
- Leg snapping and shell cracking are dramatised visual projections of that scaling, not observed events.
- Ants have no lungs. Air reaches their tissues through tracheae, largely by diffusion (some insects also pump air actively). The x-ray shot is a simplified visual metaphor.
