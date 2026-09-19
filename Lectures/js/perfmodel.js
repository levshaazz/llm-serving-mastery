/* Reusable quantitative widgets for inference-performance lectures. */
(function () {
  'use strict';
  if (window.__lec_perfmodel) return;
  window.__lec_perfmodel = 1;

  const fmt = (n, digits = 1) => Number(n).toLocaleString('en-US', { maximumFractionDigits: digits });
  const val = (root, name) => Number(root.querySelector(`[data-pm-input="${name}"]`)?.value || 0);
  const out = (root, name, value) => {
    const el = root.querySelector(`[data-pm-output="${name}"]`);
    if (el) el.textContent = value;
  };
  const reflect = (root) => root.querySelectorAll('[data-pm-input]').forEach((el) => {
    const o = root.querySelector(`[data-pm-value="${el.dataset.pmInput}"]`);
    if (o) o.textContent = el.value;
  });

  function shape(root) {
    const phase = root.dataset.phase || 'prefill';
    const batch = Math.max(1, val(root, 'batch'));
    const prompt = Math.max(1, val(root, 'prompt'));
    const history = Math.max(1, val(root, 'history'));
    const q = phase === 'prefill' ? prompt : 1;
    const k = phase === 'prefill' ? prompt : history;
    out(root, 'phase', phase);
    out(root, 'queries', `${batch} × ${q}`);
    out(root, 'attention', `${batch} × H × ${q} × ${k}`);
    out(root, 'gemm', phase === 'prefill' ? `M = ${batch * prompt}` : `M = ${batch}`);
    root.querySelectorAll('[data-pm-phase]').forEach((b) => b.classList.toggle('is-active', b.dataset.pmPhase === phase));
    const bars = root.querySelectorAll('.pm-tensor-bar');
    if (bars[0]) bars[0].style.width = `${Math.min(100, 34 + Math.log2(batch * q + 1) * 8)}%`;
    if (bars[1]) bars[1].style.width = `${Math.min(100, 30 + Math.log2(q * k + 1) * 5)}%`;
    if (bars[2]) bars[2].style.width = `${Math.min(100, 32 + Math.log2(batch + 1) * 10)}%`;
  }

  function roofline(root) {
    const intensity = Math.max(.1, val(root, 'intensity'));
    const compute = Number(root.dataset.compute || 60);
    const bandwidth = Number(root.dataset.bandwidth || 600);
    const memoryRoof = bandwidth * intensity / 1000;
    const attainable = Math.min(compute, memoryRoof);
    const ridge = compute * 1000 / bandwidth;
    const regime = intensity < ridge ? 'bandwidth-bound ceiling' : 'compute-bound ceiling';
    out(root, 'intensity', `${fmt(intensity)} FLOP/B`);
    out(root, 'attainable', `${fmt(attainable)} TFLOP/s`);
    out(root, 'ridge', `${fmt(ridge)} FLOP/B`);
    out(root, 'regime', regime);
    const x = 90 + (Math.log10(intensity) + 1) / 4 * 720;
    const yValue = Math.max(.1, attainable);
    const y = 330 - (Math.log10(yValue) + 1) / 3 * 250;
    const p = root.querySelector('.pm-point');
    if (p) { p.setAttribute('cx', String(Math.max(90, Math.min(810, x)))); p.setAttribute('cy', String(Math.max(65, Math.min(330, y)))); }
  }

  function kv(root) {
    const seq = Math.max(1, val(root, 'sequences'));
    const context = Math.max(1, val(root, 'context'));
    const kvHeads = Math.max(1, val(root, 'kvheads'));
    const bytes = Math.max(1, val(root, 'bytes'));
    const layers = Number(root.dataset.layers || 36);
    const headDim = Number(root.dataset.headDim || 128);
    const capacity = Number(root.dataset.capacityGib || 8);
    const perToken = 2 * layers * kvHeads * headDim * bytes;
    const total = perToken * seq * context;
    const gib = total / (2 ** 30);
    const ratio = gib / capacity;
    out(root, 'per-token', `${fmt(perToken / 1024, 0)} KiB/token`);
    out(root, 'tokens', fmt(seq * context, 0));
    out(root, 'total', `${fmt(gib, 2)} GiB`);
    out(root, 'fit', ratio <= 1 ? `${fmt(capacity - gib, 2)} GiB headroom` : `${fmt(gib - capacity, 2)} GiB over budget`);
    const fill = root.querySelector('.pm-capacity-fill');
    if (fill) {
      fill.style.width = `${Math.min(100, ratio * 100)}%`;
      fill.classList.toggle('is-warn', ratio > .75 && ratio <= 1);
      fill.classList.toggle('is-over', ratio > 1);
    }
  }

  function update(root) {
    reflect(root);
    const kind = root.dataset.kind;
    if (kind === 'shape') shape(root);
    else if (kind === 'roofline') roofline(root);
    else if (kind === 'kv') kv(root);
    root.dataset.pmReady = '1';
    window.Lecture?.refit(root.closest('.slide'));
  }

  function init(root) {
    if (root.dataset.pmBound) return;
    root.dataset.pmBound = '1'; root.dataset.pmReady = '0';
    root.querySelectorAll('[data-pm-input]').forEach((el) => el.addEventListener('input', () => update(root)));
    root.querySelectorAll('[data-pm-phase]').forEach((b) => b.addEventListener('click', () => { root.dataset.phase = b.dataset.pmPhase; update(root); }));
    update(root);
  }
  const initAll = () => document.querySelectorAll('.pm-widget[data-kind]').forEach(init);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll); else initAll();
  document.addEventListener('deck:ready', initAll);
})();
