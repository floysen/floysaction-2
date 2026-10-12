// Master timeline: the narration is the source of truth. Times are estimated
// from natural pacing (~2.4 words/s) because no voiceover file exists.
export const FPS = 30;
export const DURATION = 60;
export const TOTAL_FRAMES = FPS * DURATION;

export const SEGMENTS = [
  { id: 1, t0: 0, t1: 10, title: 'Premise: one ant becomes human-sized' },
  { id: 2, t0: 10, t1: 20, title: 'Nests burst out of the park' },
  { id: 3, t0: 20, t1: 30, title: 'Scale: they do not fit, they pile up' },
  { id: 4, t0: 30, t1: 40, title: 'Breathing: tracheae cannot supply oxygen' },
  { id: 5, t0: 40, t1: 50, title: 'Exoskeleton strain and collapse' },
  { id: 6, t0: 50, t1: 60, title: 'Ecosystem loss: the ant that is gone' },
];

export const NARRATION = [
  { t0: 0.2, t1: 4.6, seg: 1, text: 'Right now, roughly twenty quadrillion ants are living on Earth.' },
  { t0: 4.8, t1: 9.6, seg: 1, text: 'Imagine every one of them suddenly grew to the size of a human.' },
  { t0: 10.2, t1: 12.6, seg: 2, text: "Their underground nests can't hold them." },
  { t0: 12.8, t1: 19.4, seg: 2, text: 'Sidewalks crack, lawns heave, and giant bodies burst out of the soil in every city park.' },
  { t0: 20.1, t1: 21.6, seg: 3, text: 'Then the numbers hit.' },
  { t0: 21.8, t1: 26.4, seg: 3, text: "Spread across all of Earth's land, that's over a hundred human-sized ants on every square meter." },
  { t0: 26.7, t1: 29.6, seg: 3, text: "They don't fit. They pile up." },
  { t0: 30.1, t1: 31.9, seg: 4, text: 'But physics fights back.' },
  { t0: 32.1, t1: 36.4, seg: 4, text: 'Ants breathe through tiny tubes in their sides, which rely heavily on slow air diffusion.' },
  { t0: 36.6, t1: 39.7, seg: 4, text: "At this size, oxygen can't reach their muscles fast enough." },
  { t0: 40.1, t1: 44.3, seg: 5, text: 'Their exoskeletons, built for tiny loads, strain under their new weight.' },
  { t0: 44.6, t1: 49.2, seg: 5, text: 'Within minutes, many could collapse and stop moving.' },
  { t0: 50.1, t1: 51.9, seg: 6, text: 'The real disaster comes later.' },
  { t0: 52.1, t1: 56.9, seg: 6, text: 'Without ants turning soil, spreading seeds and hunting pests, ecosystems begin to unravel.' },
  { t0: 57.1, t1: 59.8, seg: 6, text: "The scariest giant ant is the one that's gone." },
];
