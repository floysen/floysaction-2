# MASTER PROMPT — ADDENDUM B: REALISTIC STYLE (overrides §5.1, §5.3, §5.5 and §12 where they conflict)

From now on, videos use the **realistic kit** (`kit/`) instead of the low-poly look.

## B.1 World
- **Sky and light:** a real HDR sky (`<Sky name=…>`) as the visible background **and** as the source of image-based lighting and reflections. Add one directional sun that matches the HDR, with 4096 soft shadows.
- **Surfaces:** PBR materials only (colour + normal + roughness). Use `Ground` and `Building` from `kit/Surfaces.tsx`. Windows are reflective glass, lit at night.
- **Vegetation:** `Tree` (ez-tree presets) with wind. Use 2–3 presets per scene and seed variety.
- **Water:** `Water` (animated normals plus sky reflection) for fountains, pools, the sea and rivers.
- **Life:** `Birds` flocks; dust and particles as before.
- **Post:** AgX tone mapping, N8AO contact shadows, gentle bloom, small grade, SMAA (`RealPost`).

## B.2 People (replaces the faceless rule, §5.3)
- Characters are **realistic rigged humans** (Mixamo characters), or the X Bot mannequin for background crowds.
- **Faces may exist, but every face is always pixel-mosaicked** by `FaceTracker` + the FaceBlur pass: about 5 blocks across the face height, so no facial feature is readable. Every human character registers its head (`blurFace` defaults to true). Never turn it off.
- Close-ups are allowed, because the mosaic stays on. Emotion is still carried by body language.
- Animation comes from **motion capture** (Mixamo clips), blended by weight, and is a pure function of time (`Character clips=[{clip, time, weight}]`).

## B.3 Unchanged
Everything else in the MASTER PROMPT still applies: the conversation protocol, the 61–80 s length, the text system, the HUD, the sound rules, no voice-over, determinism and the QA checklist.
Remove "photoreal humans" and "facial features" from §12: they're allowed now, but faces are always mosaicked.
