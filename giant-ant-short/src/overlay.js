import * as THREE from 'three';

// On-screen text lives in HTML over the canvas (crisp at 1080x1920) and is captured with the frame.
// All text sits in the upper-centre safe zone, away from the Shorts UI (bottom + right edge).
export function createOverlay(root) {
  root.innerHTML = `
    <div id="vignette"></div>
    <div id="caption"><div id="main"></div><div id="sub"></div></div>
    <div id="labels"></div>
    <div id="guide"><div class="tick"></div><div class="dash"></div><div class="tick"></div></div>`;
  const cap = root.querySelector('#caption');
  const main = root.querySelector('#main');
  const sub = root.querySelector('#sub');
  const labelsEl = root.querySelector('#labels');
  const guide = root.querySelector('#guide');
  const pool = [];
  const v = new THREE.Vector3();

  return {
    setText(spec) {
      if (!spec) { cap.style.opacity = 0; return; }
      cap.style.opacity = spec.o ?? 1;
      main.textContent = spec.main;
      main.style.color = spec.color ?? '#ffffff';
      sub.textContent = spec.sub ?? '';
      sub.style.display = spec.sub ? 'block' : 'none';
      sub.style.color = spec.subColor ?? '#ffffff';
      // Subtle scale-in as it appears.
      cap.style.transform = `translateX(-50%) scale(${0.92 + 0.08 * (spec.o ?? 1)})`;
    },
    // Dashed horizontal guide between two world points (used for the height comparison).
    setGuide(a, b, o, camera) {
      if (!a) { guide.style.display = 'none'; return; }
      const pa = a.clone().project(camera), pb = b.clone().project(camera);
      const xa = (pa.x * 0.5 + 0.5) * 1080, xb = (pb.x * 0.5 + 0.5) * 1080;
      const y = ((-pa.y * 0.5 + 0.5) * 1920 + (-pb.y * 0.5 + 0.5) * 1920) / 2;
      const x0 = Math.min(xa, xb) - 40, x1 = Math.max(xa, xb) + 40;
      guide.style.display = 'flex';
      guide.style.left = x0 + 'px';
      guide.style.top = y - 6 + 'px';
      guide.style.width = (x1 - x0) * Math.min(1, o * 1.2) + 'px';
      guide.style.opacity = Math.min(1, o * 2);
    },
    setLabels(list, camera) {
      while (pool.length < list.length) {
        const el = document.createElement('div');
        el.className = 'label';
        labelsEl.appendChild(el);
        pool.push(el);
      }
      pool.forEach((el, i) => {
        const l = list[i];
        if (!l) { el.style.display = 'none'; return; }
        v.copy(l.pos).project(camera);
        const x = (v.x * 0.5 + 0.5) * 1080, y = (-v.y * 0.5 + 0.5) * 1920;
        el.style.display = v.z < 1 ? 'block' : 'none';
        el.style.left = `${Math.min(860, Math.max(220, x))}px`;
        el.style.top = `${Math.min(1450, Math.max(380, y))}px`;
        el.style.opacity = l.o ?? 1;
        el.style.borderColor = l.color;
        el.style.color = l.color;
        el.textContent = l.text;
      });
    },
  };
}
