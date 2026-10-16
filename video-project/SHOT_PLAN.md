# Shot plan: حفرة في حوش بيتك ← مسبح

Vertical 9:16 at 1080×1920 and 30 fps. Running time is 80.0 s: 78.8 s of voiceover plus a 1.2 s tail.
The times below come from the voiceover itself (`data/timeline.json`). Every event is keyed to a
spoken word in `scripts/shotplan.py`, so if the alignment is regenerated, the visuals follow it.

| # | Time (s) | Narration | Camera | What happens on screen | Sound |
|---|----------|-----------|--------|------------------------|-------|
| 1 | 0.00–5.08 | لو حفرت حفرة… صار عندك مسبح! | `cam_yard`: high wide shot of a Saudi villa courtyard that pushes down toward the hole | A shovel digs 4 strokes, the dirt plug sinks, clumps fly onto a growing dirt pile next to a wheelbarrow. A hose pours water into the pit as the level rises. Confetti bursts on «مبروك», then a rubber ring drops in with a splash | dig ×4, water pour, sparkle, splash |
| 2 | 5.08–8.78 | بس ثاني يوم… تنهار | `cam_section_seep`: the ground is sliced open into a cross-section with visible soil layers | Glowing drops seep from the pit floor and walls down into the soil while the water level falls. Mud chunks break off the rim and tumble in, slumps grow at the base, and the water turns muddy | whoosh, drips, crumble |
| 3 | 8.78–10.61 | عشان كذا، تركّب شبكة حديد | `cam_rebar`: high orbit over the clean pit | Four rebar groups drop in one after another with a small bounce (floor X/Y, wall verticals, wall rings) | metal clank ×5 |
| 4 | 10.61–13.54 | وترشّ عليها طبقة سميكة من الخرسانة | `cam_spray`: tracking dolly that follows the nozzle | A shotcrete gun on its hose sweeps the length of the pool spraying concrete particles. The shell appears behind the spray front with a ragged edge | spray hiss |
| 5 | 13.54–15.67 | كذا صار المسبح يمسك الموية | `cam_full_pool`: low corner angle | The finished shell fills with clear blue water | water pour |
| 6 | 15.67–22.65 | لكن إذا فضّيته… كأنه قارب! | `cam_section_lift`: cross-section again | The pool drains. Groundwater (translucent blue) rises under the slab, and glowing arrows pulse upward. The whole shell lifts out of the ground and rocks on the water like a boat | gurgle, rumble, creak, splash |
| 7 | 22.65–33.46 | الحل؟… صمام الضغط الهيدروستاتيكي | `cam_valve`: section close-up that pulls back, then orbits the valve | The shell drops back down. A valve (body, gravel screen, brass flap) drops into the floor. Pressure arrows converge on it, the flap swings open, and a column of bubbles enters the pool. The pool nudges up but stays put. A gold ring pulses as the valve is named | whoosh, click, click, bubbles |
| 8 | 33.46–37.06 | لكن بعد أسبوع تحت الشمس… خضرا | `cam_sun_week`: wide high shot | The sun sweeps the sky (moving shadows, pulsing light), algae spreads over the walls and the water turns green, with algae puffs in the water | whoosh |
| 9 | 37.06–39.63 | وهنا تحتاج مضخة. تسحب الموية | `cam_equipment`: the equipment pad beside the pool | The pump and sand filter pop in, PVC pipes draw themselves along their bends, and dirty-green beads flow pool → pump → filter | pump spin-up, pipe flow |
| 10 | 39.63–44.78 | وتدفعها داخل خزان… فلتر الرمل | `cam_filter_cut`: close orbit on the tank | The tank wall turns transparent: gravel, sand bed, laterals and standpipe. Dirt specks pile up on the sand, and blue clean beads return to the pool. Pool and tank water turn blue again | water shimmer |
| 11 | 44.78–52.59 | بس الأوراق تطفو… اسمها السكيمر | `cam_debris`: low angle that pans to the skimmer | Leaves flutter down and float. Pebbles splash in and sink with bubbles. The skimmer pops into the wall at the waterline, flow particles pull toward it, the leaves drift in and vanish, and a gold ring pulses as it is named | leaves, plop ×3, pipe flow |
| 12 | 52.59–55.88 | وفتحة ثانية في أعمق نقطة… | `cam_drain`: looking down at the floor | The main drain grate pops in with a glow ring. The pebbles slide across the floor into it | drain gurgle |
| 13 | 55.88–62.12 | وبعدين توجّه الموية النظيفة… | `cam_topdown`: overhead | Four eyeball return jets pop onto the walls and shoot angled streams. A rotating ring of arrows shows the circulation, and the floating leaves orbit, then spiral into the skimmer | jets, swirl |
| 14 | 62.12–66.73 | لكن البكتيريا أصغر… يقضي عليها | `cam_macro`: microscopic set inside the sand filter | Dirt particles get stuck on large sand grains while green bacteria wriggle through the gaps. Glowing chlorine drops rain down, and each bacterium flashes, swells and disappears | whoosh, fizz, zap |
| 15 | 66.73–68.62 | والريحة القوية اللي تشمّها | `cam_smell`: at the water surface | Pale yellow-green vapour puffs and organic specks rise off the water | sniff |
| 16 | 68.62–73.33 | مو بالضرورة من الكلور… العضوية | `cam_molecule`: molecular set | A Cl₂ molecule appears and a red ✕ pops beside it (it isn't the chlorine itself). A urea (sweat) molecule drifts in, they collide with a flash, and chloramine (NH₂Cl) forms and floats up, giving off vapour | reaction pop |
| 17 | 73.33–76.33 | باقي تركّب البلاط، والدرج، ولوح القفز | `cam_finish`: high 3/4 view | Blue mosaic tiles sweep along the shell and coping stones drop in around the rim. A chrome ladder drops in, then a diving board lands and wobbles | tile clacks, clank, boing |
| 18 | 76.33–80.01 | ومبروك عليك! بنيت مسبحك بنفسك | `cam_final`: sweeping orbit | Loungers and an umbrella pop in, confetti bursts, the rubber ring splashes back in, and the light warms to golden hour | sparkle, splash |

Captions are Arabic in the Saudi dialect, taken word for word from the supplied script. They are shaped with HarfBuzz and laid out right-to-left.
They sit at 57–80 % of the frame height, which keeps them in the mobile safe area above the TikTok/Reels UI. The current spoken word is highlighted.
