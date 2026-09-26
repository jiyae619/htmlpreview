// FocusDock v2 compositor: plates (Blender renders / real footage) + dot-matrix typography + transitions + grade.
// Deterministic: window.renderFrame(i) draws output frame i (30 fps) onto #c.
const QS = new URLSearchParams(location.search);
const VERT = QS.get('v') === '1';                 // 9:16 version for mobile
const W = VERT ? 1080 : 1920, H = VERT ? 1920 : 1080, FPS = 30;
const RENDERS = VERT ? 'renders_v' : 'renders';
const ROOT = '/v2/';
const FILM = await (await fetch(ROOT + 'film.json')).json();
const cv = document.getElementById('c'); cv.width = W; cv.height = H;
const ctx = cv.getContext('2d');
const mk = (w = W, h = H) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; };
const [fgC, fg] = mk(); const [txC, tx] = mk(); const [glC, gl] = mk(W / 2, H / 2);

// ------------------------------------------------------------------ palette (only the device's own colours)
const C = { ink: '#0f0f11', bone: '#ede5d0', cream: '#dcd0b2', lcd: '#2a5cff', lcdDot: '#e9f1ff', red: '#ff3b2e', green: '#2bff7a', greenInk: '#11a652' };
const NOTIF = ['#34c759', '#ff2d55', '#ff3b30', '#0a84ff', '#ff9500', '#af52de'];

// ------------------------------------------------------------------ helpers
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const seg = (t, a, b) => clamp01((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const inout = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const outc = (x) => 1 - Math.pow(1 - x, 3);
const outback = (x, s = 1.7) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
function hash(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }

const cache = new Map();
async function img(src) {
  if (cache.has(src)) return cache.get(src);
  const im = new Image(); im.src = src;
  try { await im.decode(); } catch (e) { cache.set(src, null); return null; }
  cache.set(src, im); if (cache.size > 60) cache.delete(cache.keys().next().value);
  return im;
}
const pad4 = (n) => String(n).padStart(4, '0');
const anchors = {};
for (const s of FILM.shots) if (s.kind === '3d') {
  try { anchors[s.shot] = (await (await fetch(`${ROOT}blender/${RENDERS}/${s.shot}/anchors.json`)).json()).frames; } catch (e) { }
}
const A = (shot, lf, key) => { const f = anchors[shot]?.[Math.min(anchors[shot].length, Math.max(1, lf)) - 1]; return f && f[key] ? { x: f[key][0] * W, y: f[key][1] * H } : null; };

// ------------------------------------------------------------------ HD44780 5x7 font
const FONT = {
  '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'], '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
  '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'], '3': ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
  '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'], '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
  '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'], '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
  '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'], '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
  ':': ['00000', '01100', '01100', '00000', '01100', '01100', '00000'], ' ': ['00000', '00000', '00000', '00000', '00000', '00000', '00000'],
  'A': ['01110', '10001', '10001', '10001', '11111', '10001', '10001'], 'B': ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
  'C': ['01110', '10001', '10000', '10000', '10000', '10001', '01110'], 'D': ['11100', '10010', '10001', '10001', '10001', '10010', '11100'],
  'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'], 'F': ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
  'G': ['01110', '10001', '10000', '10111', '10001', '10001', '01111'], 'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
  'I': ['01110', '00100', '00100', '00100', '00100', '00100', '01110'], 'J': ['00111', '00010', '00010', '00010', '00010', '10010', '01100'],
  'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'], 'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
  'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'], 'N': ['10001', '10001', '11001', '10101', '10011', '10001', '10001'],
  'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'], 'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
  'Q': ['01110', '10001', '10001', '10001', '10101', '10010', '01101'], 'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
  'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'], 'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
  'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'], 'V': ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
  'W': ['10001', '10001', '10001', '10101', '10101', '10101', '01010'], 'X': ['10001', '10001', '01010', '00100', '01010', '10001', '10001'],
  'Y': ['10001', '10001', '10001', '01010', '00100', '00100', '00100'], 'Z': ['11111', '00001', '00010', '00100', '01000', '10000', '11111'],
  '!': ['00100', '00100', '00100', '00100', '00100', '00000', '00100'], '.': ['00000', '00000', '00000', '00000', '00000', '01100', '01100'],
  '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'], '?': ['01110', '10001', '00001', '00010', '00100', '00000', '00100'],
  ',': ['00000', '00000', '00000', '00000', '01100', '00100', '01000'], "'": ['01100', '00100', '01000', '00000', '00000', '00000', '00000'],
  '/': ['00000', '00001', '00010', '00100', '01000', '10000', '00000'], '×': ['00000', '10001', '01010', '00100', '01010', '10001', '00000'],
  '█': ['11111', '11111', '11111', '11111', '11111', '11111', '11111'],
};
const GLYPH = {};
for (const [ch, rows] of Object.entries(FONT)) { const d = []; rows.forEach((r, y) => [...r].forEach((b, x) => b === '1' && d.push([x, y]))); GLYPH[ch] = d; }

// chars of a page: [{ch, line, col, t}] with per-character reveal times (word time + sweep)
function pageChars(page, sweep = 0.022) {
  const out = [];
  page.lines.forEach((toks, li) => {
    let col = 0;
    toks.forEach((tok, wi) => {
      if (wi > 0) col++;
      [...tok.w].forEach((ch, ci) => out.push({ ch, line: li, col: col + ci, t: tok.t + ci * sweep }));
      col += tok.w.length;
    });
  });
  const widths = page.lines.map((toks) => toks.reduce((a, t, i) => a + t.w.length + (i ? 1 : 0), 0));
  return { chars: out, widths };
}

// draw dot text in the current transform of g. Units: one dot pitch = p. Origin: (0,0) = anchor per align.
function dotText(g, page, t, o) {
  const { p, align = 'left', color = C.bone, lineGap = 2, tOut = page.t1, colorFn = null, rDot = 0.42, popDur = 0.07 } = o;
  const { chars, widths } = pageChars(page, o.sweep ?? 0.022);
  const lineH = 7 + lineGap;
  const totalH = page.lines.length * lineH - lineGap;
  const outK = o.noOut ? 0 : seg(t, tOut - 0.1, tOut);
  for (const c of chars) {
    const k = seg(t, c.t, c.t + popDur); if (k <= 0) continue;
    const sc = (k < 1 ? outback(k, 2.2) : 1) * (1 - outK); if (sc <= 0.01) continue;
    const lw = widths[c.line] * 6 - 1;
    const x0 = align === 'center' ? -lw / 2 : align === 'right' ? -lw : 0;
    const y0 = (o.valign === 'middle' ? -totalH / 2 : 0) + c.line * lineH;
    const gd = GLYPH[c.ch] || GLYPH[' '];
    for (const [dx, dy] of gd) {
      g.fillStyle = colorFn ? colorFn(c, dx, dy, t) : color;
      g.beginPath(); g.arc((x0 + c.col * 6 + dx + 0.5) * p, (y0 + dy + 0.5) * p, p * rDot * sc, 0, Math.PI * 2); g.fill();
    }
  }
}

// ------------------------------------------------------------------ plates
function shotAt(t) { return FILM.shots.find((s) => t >= s.start - 1e-6 && t < s.end - 1e-6) || FILM.shots[FILM.shots.length - 1]; }
async function drawPlate(g, s, lt, lf) {
  if (s.kind === '3d') {
    const im = await img(`${ROOT}blender/${RENDERS}/${s.shot}/rgb/${pad4(lf)}.png`);
    if (im) { g.imageSmoothingQuality = 'high'; g.filter = 'saturate(1.1) contrast(1.03)'; g.drawImage(im, 0, 0, W, H); g.filter = 'none'; }
    else { g.fillStyle = '#222'; g.fillRect(0, 0, W, H); g.fillStyle = '#f0f'; g.font = '40px monospace'; g.fillText(`${s.shot} ${lf}`, 60, 80); }
    return;
  }
  if (s.kind === 'real') {
    const n = Math.round((s.end - s.start) * FPS);
    let src;
    if (s.timelapse) src = Math.round(lerp(s.src[0], s.src[1], (lf - 1) / (n - 1)));
    else src = Math.min(s.src[1], s.src[0] + lf - 1);
    const im = await img(`${ROOT}real/${pad4(src)}.jpg`);
    if (VERT) { drawRealVertical(g, s, lt, im); return; }
    let zoom = 1.045, cx = W / 2, cy = H / 2;
    if (s.timelapse) { const k = inout(seg(lt, 0.1, s.end - s.start - 0.2)); zoom = lerp(1.06, 2.05, k); cx = lerp(W / 2, 1310, k); cy = lerp(H / 2, 648, k); }
    g.save(); g.filter = 'contrast(1.08) saturate(0.9) brightness(0.97)';
    g.translate(W / 2, H / 2); g.scale(zoom, zoom); g.translate(-cx, -cy);
    if (im) g.drawImage(im, 0, 0, W, H);
    g.restore(); g.filter = 'none';
    // warm bone tint in the highlights, like the 3D studio
    g.save(); g.globalCompositeOperation = 'soft-light'; g.globalAlpha = 0.12; g.fillStyle = C.bone; g.fillRect(0, 0, W, H); g.restore();
  }
}
// vertical: blurred cover fill + a sharp 1080x1080 window cut from the source around the action
const WIN = { x: 0, y: 480, s: 1080 };
function drawRealVertical(g, s, lt, im) {
  if (!im) return;
  const sc = H / 1080;
  g.save(); g.filter = 'blur(30px) brightness(0.42) saturate(0.85)'; g.drawImage(im, (W - 1920 * sc) / 2 - 120, 0, 1920 * sc, H); g.restore();
  let cx = 1100, cy = 540, zoom = 1.0;
  if (s.timelapse) { const k = inout(seg(lt, 0.1, s.end - s.start - 0.2)); zoom = lerp(1.0, 1.9, k); cx = lerp(1100, 1310, k); cy = lerp(540, 648, k); }
  const half = 540 / zoom;
  const sx = Math.max(0, Math.min(1920 - 2 * half, cx - half)), sy = Math.max(0, Math.min(1080 - 2 * half, cy - half));
  g.save(); g.filter = 'contrast(1.08) saturate(0.9) brightness(0.97)';
  g.shadowColor = 'rgba(0,0,0,0.5)'; g.shadowBlur = 40;
  g.drawImage(im, sx, sy, 2 * half, 2 * half, WIN.x, WIN.y, WIN.s, WIN.s); g.restore();
  g.save(); g.globalCompositeOperation = 'soft-light'; g.globalAlpha = 0.12; g.fillStyle = C.bone; g.fillRect(WIN.x, WIN.y, WIN.s, WIN.s); g.restore();
}
// vertical: live status line under the footage window, mirroring the LED
function drawRealStatus(g, t) {
  const E = FILM.events;
  let txt = 'FOCUS OFF', col = null;
  if (t >= E.focus_on_real) { txt = 'PHONE AWAY'; col = C.red; }
  if (t >= E.green_real) { txt = 'PHONE ON'; col = C.green; }
  if (t >= E.red_real) { txt = 'PHONE AWAY'; col = C.red; }
  const p = 9, y = WIN.y + WIN.s + 46;
  const pg = { t0: 0, t1: 99, lines: [[{ w: txt, t: 0 }]] };
  const tw = (txt.length * 6 - 1) * p, x0 = (W - tw) / 2 + (col ? 34 : 0);
  if (col) {
    const lx = x0 - 52, ly = y + 3.5 * p;
    const rg = g.createRadialGradient(lx, ly, 0, lx, ly, 46); rg.addColorStop(0, col); rg.addColorStop(1, 'rgba(0,0,0,0)');
    g.save(); g.globalAlpha = 0.55; g.fillStyle = rg; g.fillRect(lx - 50, ly - 50, 100, 100); g.restore();
    g.fillStyle = '#fff'; g.beginPath(); g.arc(lx, ly, 10, 0, 7); g.fill();
  }
  g.save(); g.translate(x0, y);
  dotText(g, pg, 10, { p, color: C.bone, rDot: 0.44, noOut: true, popDur: 0.001, sweep: 0 });
  g.restore();
}
async function drawForeground(g, s, lf) {
  // redraw the plate masked by the object matte so text sits behind the product
  const [pl, mt] = await Promise.all([img(`${ROOT}blender/${RENDERS}/${s.shot}/rgb/${pad4(lf)}.png`), img(`${ROOT}blender/${RENDERS}/${s.shot}/matte/${pad4(lf)}.png`)]);
  if (!pl || !mt) return;
  fg.globalCompositeOperation = 'source-over'; fg.clearRect(0, 0, W, H); fg.filter = 'saturate(1.1) contrast(1.03)'; fg.drawImage(pl, 0, 0, W, H); fg.filter = 'none';
  fg.globalCompositeOperation = 'destination-in'; fg.drawImage(mt, 0, 0, W, H); fg.globalCompositeOperation = 'source-over';
  g.drawImage(fgC, 0, 0);
}

// glow: draw the text layer blurred underneath, then crisp
function composeText(g, glow = 0.55, blur = 10) {
  gl.clearRect(0, 0, W / 2, H / 2); gl.drawImage(txC, 0, 0, W / 2, H / 2);
  g.save(); g.globalAlpha = glow; g.filter = `blur(${blur / 2}px)`; g.globalCompositeOperation = 'screen';
  g.drawImage(glC, 0, 0, W, H); g.restore();
  g.drawImage(txC, 0, 0);
}

// ------------------------------------------------------------------ caption modes
const capGroups = FILM.captions;
function reflow(page, maxCols) {
  const lines = [];
  for (const line of page.lines) {
    let cur = [], len = 0;
    for (const tok of line) {
      if (tok.w.length > maxCols) {            // one long word: split it with a hyphen
        if (cur.length) { lines.push(cur); cur = []; len = 0; }
        const cut = Math.ceil(tok.w.length / 2);
        lines.push([{ w: tok.w.slice(0, cut) + '-', t: tok.t }]); cur = [{ w: tok.w.slice(cut), t: tok.t + 0.22 }]; len = cur[0].w.length; continue;
      }
      const add = (cur.length ? 1 : 0) + tok.w.length;
      if (len + add > maxCols && cur.length) { lines.push(cur); cur = [tok]; len = tok.w.length; } else { cur.push(tok); len += add; }
    }
    if (cur.length) lines.push(cur);
  }
  return { ...page, lines };
}
function splitHyphens(page) {   // PHONE-DOWN -> PHONE- / DOWN (stacked giant type)
  const lines = [];
  for (const line of page.lines) for (const tok of line) {
    const parts = tok.w.split('-');
    parts.forEach((pt, i) => lines.push([{ w: pt + (i < parts.length - 1 ? '-' : ''), t: tok.t + i * 0.22 }]));
  }
  return { ...page, lines };
}
function activePages(t) {
  const out = [];
  for (const grp of capGroups) grp.pages.forEach((pg, i) => { if (t >= pg.t0 - 0.02 && t < pg.t1 + 0.02) out.push({ grp, pg, i }); });
  return out;
}
const PAGE_MODE = { 'smart:0': 'lcd', 'acct:0': 'lcd', 'acct:2': 'lcd' };
const modeOf = (grp, i) => PAGE_MODE[`${grp.vo}:${i}`] || grp.mode;

// floor-embedded text in the top-down storm: printed on the floor around the phone, aligned to it
function floorXform(shot, lf, origin, ang) {
  const O = A(shot, lf, 'O'), X = A(shot, lf, 'X'), Y = A(shot, lf, 'Y');
  if (!O) return null;
  const mx = { x: (X.x - O.x) / 0.1, y: (X.y - O.y) / 0.1 }, my = { x: (Y.x - O.x) / 0.1, y: (Y.y - O.y) / 0.1 };
  const S = (px, py) => ({ x: O.x + mx.x * px + my.x * py, y: O.y + mx.y * px + my.y * py });
  const u = { x: Math.cos(ang), y: Math.sin(ang) }, v = { x: -Math.sin(ang), y: Math.cos(ang) };
  const o = S(origin.x, origin.y);
  return [mx.x * u.x + my.x * u.y, mx.y * u.x + my.y * u.y, -(mx.x * v.x + my.x * v.y), -(mx.y * v.x + my.y * v.y), o.x, o.y];
}
const PHONE0 = { x: -0.075, y: -0.005 }, PROT0 = 14 * Math.PI / 180;

// text printed on the floor: pick the floor point under a screen position at the page start,
// orient it screen-horizontal then, and let it turn with the floor as the camera keeps moving
function floorText(page, t, lf, sh, sx, sy, pPx, opts = {}) {
  const f0 = Math.max(1, Math.round((page.t0 - sh.start) * FPS) + 1);
  const O = A(sh.shot, f0, 'O'), X = A(sh.shot, f0, 'X'), Y = A(sh.shot, f0, 'Y');
  if (!O) return;
  const mx = { x: (X.x - O.x) / 0.1, y: (X.y - O.y) / 0.1 }, my = { x: (Y.x - O.x) / 0.1, y: (Y.y - O.y) / 0.1 };
  const det = mx.x * my.y - my.x * mx.y; const tx0 = sx - O.x, ty0 = sy - O.y;
  const fx = (tx0 * my.y - my.x * ty0) / det, fy = (mx.x * ty0 - tx0 * mx.y) / det;
  const ang = Math.atan2(X.y - O.y, X.x - O.x);
  const pxPerM = Math.hypot(mx.x, mx.y);
  const m = floorXform(sh.shot, lf, { x: fx, y: fy }, ang); if (!m) return;
  tx.setTransform(...m);
  dotText(tx, page, t, { p: pPx / pxPerM, align: 'center', valign: 'middle', tOut: page.t1, color: C.bone, ...opts });
  tx.setTransform(1, 0, 0, 1, 0, 0);
}
function drawFloorCaption(page, i, t, lf, sh) {
  const noise = page.accent === 'noise';
  if (VERT) {
    const pg = reflow(page, noise ? 9 : 13);
    const cols = Math.max(...pg.lines.map((l) => l.reduce((a, tk, j) => a + tk.w.length + (j ? 1 : 0), 0)));
    const pPx = Math.min(noise ? 19 : 15, (0.82 * W) / (cols * 6));
    floorText(pg, t, lf, sh, 0.5 * W, 0.66 * H, pPx, { lineGap: 3,
      colorFn: noise ? (c, dx, dy, tt) => (hash(c.col * 31 + c.line * 97 + dx * 7 + dy * 13 + Math.floor(tt * 14)) > 0.45 ? NOTIF[Math.floor(hash(c.col + c.line * 17 + dx * 5 + dy * 3 + Math.floor(tt * 9)) * 6)] : C.bone) : null });
    return;
  }
  floorText(page, t, lf, sh, 0.5 * W, (page.lines.length > 1 ? 0.755 : 0.77) * H, noise ? 19.5 : 15, {
    lineGap: 3,
    colorFn: noise ? (c, dx, dy, tt) => (hash(c.col * 31 + dx * 7 + dy * 13 + Math.floor(tt * 14)) > 0.45 ? NOTIF[Math.floor(hash(c.col + dx * 5 + dy * 3 + Math.floor(tt * 9)) * 6)] : C.bone) : null,
  });
}
function drawBuiltCaption(page, i, t, lf, sh) {
  const title = i === 1;
  if (VERT) {
    floorText(reflow(page, 13), t, lf, sh, 0.5 * W, 0.165 * H, title ? 17 : 13, { sweep: title ? 0.035 : 0.022, lineGap: 3,
      colorFn: title ? (c) => (c.col >= 5 ? C.green : C.bone) : null });
    return;
  }
  floorText(page, t, lf, sh, 0.33 * W, (title ? 0.8 : 0.82) * H, title ? 21 : 14, {
    sweep: title ? 0.035 : 0.022, lineGap: 3,
    colorFn: title ? (c) => (c.col >= 5 ? C.green : C.bone) : null,
  });
}

// "ACCOUNTABLE": the focus light writes the word onto the lid face and it rides the box as the camera pushes in
// vertical: the push-in carries the lid past the frame edges, so the word leaves before it would clip
let projOut = null;
function projectedOut(page, sh) {
  if (projOut !== null) return projOut;
  projOut = 48.55;
  if (!VERT) return projOut;
  for (let lf = Math.floor((page.t0 - sh.start) * FPS) + 1; lf <= anchors[sh.shot].length; lf++) {
    const c = A(sh.shot, lf, 'lid_face'), cx = A(sh.shot, lf, 'lid_face_x');
    const half = 0.1075 * Math.hypot(cx.x - c.x, cx.y - c.y) / 0.1;   // half of the 21.5 cm word
    if (c.x - half < 0.04 * W || c.x + half > 0.96 * W) { projOut = Math.min(projOut, sh.start + (lf - 1) / FPS); break; }
  }
  return projOut;
}
function drawProjected(g, page, t, sh, lf) {
  const c = A(sh.shot, lf, 'lid_face'), cx = A(sh.shot, lf, 'lid_face_x');
  if (!c || !cx) return;
  const pxPerM = Math.hypot(cx.x - c.x, cx.y - c.y) / 0.1, ang = Math.atan2(cx.y - c.y, cx.x - c.x);
  const p = (0.215 / 65) * pxPerM;        // the word spans 21.5 cm of the 26 cm lid
  tx.setTransform(Math.cos(ang), Math.sin(ang), -Math.sin(ang), Math.cos(ang), c.x, c.y);
  dotText(tx, page, t, { p, align: 'center', valign: 'middle', sweep: 0.03, tOut: projectedOut(page, sh), color: '#34ff85', rDot: 0.44 });
  tx.setTransform(1, 0, 0, 1, 0, 0);
  g.save(); g.globalCompositeOperation = 'screen'; g.globalAlpha = 0.5; g.filter = `blur(${Math.max(4, p * 0.6)}px)`; g.drawImage(txC, 0, 0); g.restore();
  g.save(); g.globalCompositeOperation = 'screen'; g.drawImage(txC, 0, 0); g.restore();
  tx.clearRect(0, 0, W, H);
}
function drawGiant(page, grp, i, t, sh) {
  // huge type on the studio backdrop, behind the product
  const acc = grp.vo === 'acct';
  if (VERT) page = splitHyphens(page);
  const cols = Math.max(...page.lines.map((l) => l.reduce((a, tk, j) => a + tk.w.length + (j ? 1 : 0), 0)));
  const p = VERT ? Math.min(28, (0.86 * W) / (cols * 6)) : (acc ? 25 : 21);
  tx.setTransform(1, 0, 0, 1, W / 2, VERT ? 0.13 * H : (acc ? 0.2 * H : 0.05 * H));
  dotText(tx, page, t, {
    p, align: 'center', valign: 'top', lineGap: 3, sweep: 0.03, tOut: acc ? 48.5 : page.t1, noOut: false,
    color: page.accent === 'green' ? C.greenInk : '#1b1c20', rDot: 0.44,
  });
  tx.setTransform(1, 0, 0, 1, 0, 0);
}

// floating 16x2 LCD caption strip (the device's own display, blown up)
const LCDP = 7, LCD_PAD = 3;
// strip corner per shot, chosen to stay clear of the parts each shot is about
const STRIP_AT = { N: 'bl', N3: 'tl', M1: 'bl', M2: 'br', M3: 'bl', M5: 'bl', M6: 'bl', O1: 'bl' };
function lcdPanelRect(sh) {
  const w = (16 * 6 - 1 + 2 * LCD_PAD) * LCDP + 28, h = (2 * 9 - 1 + 2 * LCD_PAD) * LCDP + 28;
  if (VERT) return { x: (W - w) / 2, y: 262, w, h };   // one fixed spot, clear of the app's bottom UI
  const at = sh.kind === 'real' ? 'tl_chip' : (STRIP_AT[sh.id] || 'bl');
  if (at === 'tl_chip') return { x: 64, y: 64 + 54, w, h };
  const x = at.endsWith('r') ? W - 64 - w : 64;
  const y = at.startsWith('t') ? (LABELS[sh.id] ? 64 + 58 : 64) : H - 64 - h;
  return { x, y, w, h };
}
function drawLcdStrip(g, t, sh, pages) {
  // visibility envelope across consecutive lcd pages
  const lcdPages = [];
  for (const grp of capGroups) grp.pages.forEach((pg, i) => { if (modeOf(grp, i) === 'lcd') lcdPages.push({ grp, pg, i }); });
  // consecutive pages (gap < 0.6 s) share one continuous panel
  lcdPages.sort((a, b) => a.pg.t0 - b.pg.t0);
  const runs = [];
  for (const lp of lcdPages) {
    const last = runs[runs.length - 1];
    if (last && lp.pg.t0 - last.t1 < 0.6) last.t1 = Math.max(last.t1, lp.pg.t1); else runs.push({ t0: lp.pg.t0, t1: lp.pg.t1 });
  }
  const run = runs.find((r) => t >= r.t0 - 0.12 && t < r.t1 + 0.16);
  if (!run) return;
  const r = lcdPanelRect(sh);
  const vis = outc(seg(t, run.t0 - 0.12, run.t0 + 0.02)) * (1 - seg(t, run.t1 + 0.02, run.t1 + 0.16));
  const inRun = lcdPages.filter(({ pg }) => pg.t0 >= run.t0 - 1e-6 && pg.t0 - 0.02 <= t);
  const cur = inRun[inRun.length - 1];
  const lastOfRun = cur && Math.abs(cur.pg.t1 - run.t1) < 1e-6;
  const acc = cur?.pg.accent;
  const bl = acc === 'green' && t >= cur.pg.lines[1]?.[1]?.t - 0.05 ? '#169a4f' : acc === 'red' && t >= cur.pg.lines[1]?.[0]?.t - 0.05 ? '#c6302a' : '#1f55f0';
  g.save();
  g.globalAlpha = vis; g.translate(r.x, r.y + (1 - vis) * 20);
  // bezel + shadow
  g.shadowColor = 'rgba(0,0,0,0.45)'; g.shadowBlur = 30; g.shadowOffsetY = 10;
  g.fillStyle = '#0b0c0e'; g.beginPath(); g.roundRect(0, 0, r.w, r.h, 12); g.fill();
  g.shadowColor = 'transparent';
  const ix = 14, iy = 14, iw = r.w - 28, ih = r.h - 28;
  const grd = g.createLinearGradient(0, iy, 0, iy + ih); grd.addColorStop(0, bl); grd.addColorStop(1, shade(bl, -0.18));
  g.fillStyle = grd; g.beginPath(); g.roundRect(ix, iy, iw, ih, 4); g.fill();
  // unlit cells
  g.fillStyle = 'rgba(255,255,255,0.07)';
  for (let row = 0; row < 2; row++) for (let col = 0; col < 16; col++) {
    g.fillRect(ix + (LCD_PAD + col * 6) * LCDP, iy + (LCD_PAD + row * 9) * LCDP, 5 * LCDP - 1, 8 * LCDP - 1);
  }
  // text
  if (cur) {
    g.translate(ix + LCD_PAD * LCDP, iy + LCD_PAD * LCDP);
    g.shadowColor = 'rgba(220,235,255,0.8)'; g.shadowBlur = 6;
    dotText(g, cur.pg, t, { p: LCDP, color: C.lcdDot, lineGap: 2, rDot: 0.46, popDur: 0.03, sweep: 0.018, tOut: cur.pg.t1 + 0.02, noOut: lastOfRun });
  }
  g.restore();
}
function shade(hex, k) { const n = parseInt(hex.slice(1), 16); const f = (c) => Math.max(0, Math.min(255, Math.round(c * (1 + k)))); return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`; }

// technical labels, Teenage-Engineering-manual style
const LABELS = { M1: '01 — 16×2 LCD', M2: '02 — LEDS · RED / GREEN', M3: '03 — FOCUS BUTTON', M5: '04 — SENSOR OPENING', M6: '05 — PHOTORESISTOR' };
function drawLabel(g, sh, lt) {
  const txt = LABELS[sh.id];
  const real = sh.kind === 'real';
  if (!txt && !real) return;
  const k = outc(seg(lt, 0.05, 0.35));
  g.save(); g.globalAlpha = k; g.font = '500 23px Mono'; g.letterSpacing = '3px';
  const label = real ? 'REAL PROTOTYPE' : txt;
  const w = g.measureText(label).width + (real ? 70 : 48);
  const ly = VERT ? 190 : 60;
  g.fillStyle = 'rgba(8,8,10,0.58)'; g.beginPath(); g.roundRect(64, ly, w, 44, 22); g.fill();
  if (real) { g.fillStyle = C.red; g.beginPath(); g.arc(90, ly + 22, 7, 0, 7); g.fill(); }
  g.fillStyle = C.bone; g.fillText(label, real ? 108 : 88, ly + 30);
  g.restore();
}

// ------------------------------------------------------------------ special graphics
function drawButtonPulse(g, sh, lf, lt) {
  const P = A(sh.shot, lf, 'button'); if (!P) return;
  const k = seg(lt, 0.45, 1.05); if (k <= 0 || k >= 1) return;
  g.save(); g.strokeStyle = `rgba(255,255,255,${0.9 * (1 - k)})`; g.lineWidth = 3;
  g.beginPath(); g.arc(P.x, P.y, 30 + 120 * outc(k), 0, 7); g.stroke(); g.restore();
}
function drawLdrMeter(g, sh, lt) {
  // mini LCD readout of the analog value the Arduino sees
  const E = FILM.events; const t = sh.start + lt;
  const bright = seg(t, E.beam - 0.05, E.beam + 0.35) * (1 - seg(t, E.cover + 0.2, E.cover + 0.5));
  const val = Math.round(lerp(212, 874, bright) + (hash(Math.floor(t * 12)) - 0.5) * 8);
  const show = outc(seg(lt, 1.1, 1.4)); if (show <= 0) return;
  const bars = Math.round(bright * 9);
  const state = bright > 0.5 ? 'BRIGHT' : 'DARK';
  const pg = { t0: 0, t1: 99, lines: [[{ w: 'LDR', t: 0 }, { w: String(val).padStart(4, ' '), t: 0 }], [{ w: ('█'.repeat(Math.max(0, bars)) + ' '.repeat(9 - bars) + ' ' + state.padStart(6, ' ')), t: 0 }]] };
  const p = 5, w = (16 * 6 - 1 + 6) * p + 24, h = (17 + 6) * p + 24;
  g.save(); g.globalAlpha = show; g.translate(VERT ? (W - w) / 2 : W - 64 - w, VERT ? 478 : 64);
  g.fillStyle = '#0b0c0e'; g.beginPath(); g.roundRect(0, 0, w, h, 10); g.fill();
  g.fillStyle = bright > 0.5 ? '#1f55f0' : '#14307f'; g.beginPath(); g.roundRect(12, 12, w - 24, h - 24, 4); g.fill();
  g.translate(12 + 3 * p, 12 + 3 * p);
  dotText(g, pg, 10, { p, color: C.lcdDot, rDot: 0.46, noOut: true, popDur: 0.001, sweep: 0 });
  g.restore();
}
function dotWipe(g, t, tc, color) {
  // the frame dissolves through a grid of LCD pixels
  const d = t - tc; if (Math.abs(d) > 0.34) return;
  const pitch = 54; g.fillStyle = color;
  for (let y = 0; y < H + pitch; y += pitch) for (let x = 0; x < W + pitch; x += pitch) {
    const delay = ((x / W) * 0.6 + (y / H) * 0.4) * 0.16;
    const k = d < 0 ? seg(d, -0.34 + delay, -0.1 + delay) : 1 - seg(d, delay * 0.8, 0.2 + delay * 0.8);
    if (k <= 0) continue;
    g.beginPath(); g.arc(x + pitch / 2, y + pitch / 2, pitch * 0.75 * inout(k), 0, 7); g.fill();
  }
}

// ------------------------------------------------------------------ end card: the device's LCD becomes the screen
const END = { lcd: null };
function endLcd(g, t, sh) {
  const lt = t - sh.start;
  // rect of the 3D LCD in the last O1 frame, grows to a clean centred panel, then shrinks away
  const R0 = (VERT ? FILM.endLcdRectV : FILM.endLcdRect) || { x: 0.035 * W, y: 0.27 * H, w: 0.93 * W, h: 0.42 * H };
  const R1 = VERT ? { x: 0.05 * W, y: 0.4 * H, w: 0.9 * W, h: 0.9 * W * 0.26 } : { x: 0.06 * W, y: 0.26 * H, w: 0.88 * W, h: 0.4 * H };
  const shrink = inout(seg(t, 52.6, 53.4));
  const R2 = VERT ? { x: 0.16 * W, y: 0.42 * H, w: 0.68 * W, h: 0.68 * W * 0.26 } : { x: 0.25 * W, y: 0.34 * H, w: 0.5 * W, h: 0.228 * H };
  let R = lerpR(R0, R1, inout(seg(lt, 0.0, 0.5)));
  R = lerpR(R, R2, shrink);
  const power = 1 - seg(t, 54.25, 54.55);
  g.fillStyle = '#060607'; g.fillRect(0, 0, W, H);
  // bezel
  g.save(); g.fillStyle = '#0c0d10'; g.beginPath(); g.roundRect(R.x - 0.02 * R.w, R.y - 0.06 * R.h, R.w * 1.04, R.h * 1.12, 14); g.fill();
  const blue = `rgba(${Math.round(lerp(8, 31, power))},${Math.round(lerp(10, 85, power))},${Math.round(lerp(20, 240, power))},1)`;
  g.fillStyle = blue; g.fillRect(R.x, R.y, R.w, R.h);
  const p = R.w / (16 * 6 - 1 + 8);
  const oy = R.y + (R.h - (2 * 9 - 1) * p) / 2, ox = R.x + 4 * p;
  g.fillStyle = `rgba(255,255,255,${0.07 * power})`;
  for (let row = 0; row < 2; row++) for (let col = 0; col < 16; col++) g.fillRect(ox + col * 6 * p, oy + row * 9 * p, 5 * p - 1, 8 * p - 1);
  // content timeline
  const go = capGroups.find((c) => c.vo === 'go').pages[0];
  let page;
  if (t < go.t0) page = { t0: -1, t1: 99, lines: [[{ w: 'FOCUS', t: -1 }, { w: 'ON', t: -1 }], [{ w: 'PHONE', t: -1 }, { w: 'ON   59:59', t: -1 }]] };
  else if (t < 50.4) page = { ...go, t1: 50.4 };
  else if (t < 51.6) page = { t0: 50.45, t1: 51.6, lines: [[{ w: '   FOCUSDOCK', t: 50.45 }], [{ w: 'PARK YOUR PHONE.', t: 50.75 }]] };
  else page = { t0: 51.62, t1: 99, lines: [[{ w: '   FOCUSDOCK', t: -1 }], [{ w: 'PROVE YOUR FOCUS', t: 51.65 }]] };
  g.shadowColor = `rgba(220,235,255,${0.8 * power})`; g.shadowBlur = p * 0.8;
  g.translate(ox, oy);
  dotText(g, page, t, { p, color: `rgba(233,241,255,${power})`, lineGap: 2, rDot: 0.46, popDur: 0.04, sweep: 0.03, tOut: page.t1, noOut: page.t1 > 90,
    colorFn: t >= 50.4 ? (c) => (c.line === 0 && c.col >= 8 ? `rgba(120,255,170,${power})` : `rgba(233,241,255,${power})`) : null });
  g.restore();
  // LED + credits
  const cr = outc(seg(t, 52.9, 53.5)) * (1 - seg(t, 54.6, 55.0));
  g.save(); g.globalAlpha = cr; g.fillStyle = C.bone; g.font = '500 26px Mono'; g.letterSpacing = '4px'; g.textAlign = 'center';
  if (VERT) { g.font = '500 24px Mono'; g.fillText('JIYAE CHOI', W / 2, R.y + R.h + 110); g.fillText('HCDE 539 · WINTER 2026', W / 2, R.y + R.h + 152); }
  else g.fillText('JIYAE CHOI — HCDE 539 · WINTER 2026', W / 2, R.y + R.h + 110);
  g.restore();
  const led = seg(t, 52.9, 53.2) * (1 - seg(t, 54.9, 55.15));
  if (led > 0) {
    const lx = R.x - 0.06 * R.w, ly = R.y + R.h * 0.5;
    const rg = g.createRadialGradient(lx, ly, 0, lx, ly, 70); rg.addColorStop(0, `rgba(80,255,150,${0.9 * led})`); rg.addColorStop(1, 'rgba(80,255,150,0)');
    g.fillStyle = rg; g.fillRect(lx - 80, ly - 80, 160, 160);
    g.fillStyle = `rgba(220,255,230,${led})`; g.beginPath(); g.arc(lx, ly, 9, 0, 7); g.fill();
  }
}
const lerpR = (a, b, k) => ({ x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), w: lerp(a.w, b.w, k), h: lerp(a.h, b.h, k) });

// ------------------------------------------------------------------ grain + vignette
const grains = [];
for (let i = 0; i < 6; i++) {
  const [c, g] = mk(512, 512); const id = g.createImageData(512, 512);
  for (let j = 0; j < id.data.length; j += 4) { const v = 128 + (Math.random() - 0.5) * 90; id.data[j] = id.data[j + 1] = id.data[j + 2] = v; id.data[j + 3] = 255; }
  g.putImageData(id, 0, 0); grains.push(c);
}
function grade(g, fi) {
  g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = 0.06;
  const gc = grains[fi % grains.length]; const pat = g.createPattern(gc, 'repeat'); g.fillStyle = pat;
  g.translate((fi * 137) % 512, (fi * 71) % 512); g.fillRect(-512, -512, W + 1024, H + 1024); g.restore();
  const vg = VERT ? g.createRadialGradient(W / 2, H / 2, W * 0.45, W / 2, H / 2, Math.hypot(W, H) * 0.55) : g.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 1.05);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.32)');
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
}

// ------------------------------------------------------------------ frame
window.renderFrame = async (fi) => {
  const t = fi / FPS;
  const sh = shotAt(t); const lt = t - sh.start; const lf = Math.floor(lt * FPS + 1e-4) + 1;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.filter = 'none';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  if (sh.kind === '2d') {
    endLcd(ctx, t, sh);
    if (lt < 0.2) {   // dissolve out of the last rendered LCD frame
      const o1 = FILM.shots.find((x) => x.id === 'O1'); const last = Math.round((o1.end - o1.start) * FPS);
      const im = await img(`${ROOT}blender/${RENDERS}/O1/rgb/${pad4(last)}.png`);
      if (im) { ctx.save(); ctx.globalAlpha = 1 - inout(seg(lt, 0, 0.2)); ctx.filter = 'saturate(1.1) contrast(1.03)'; ctx.drawImage(im, 0, 0, W, H); ctx.restore(); }
    }
    grade(ctx, fi); return true;
  }
  await drawPlate(ctx, sh, lt, lf);

  // text layers
  tx.setTransform(1, 0, 0, 1, 0, 0); tx.clearRect(0, 0, W, H);
  const pages = activePages(t);
  let behind = false;
  for (const { grp, pg, i } of pages) {
    const m = modeOf(grp, i);
    if (m === 'floor' && sh.shot === 'N') { drawFloorCaption(pg, i, t, lf, sh); behind = true; }
    if (m === 'giant_dark' && sh.shot === 'N') { drawBuiltCaption(pg, i, t, lf, sh); behind = true; }
    if (m === 'giant' && sh.shot === 'N3') { drawGiant(pg, grp, i, t, sh); behind = true; }
  }
  const acc = capGroups.find((c) => c.vo === 'acct');
  const accPg = acc.pages[1];
  const onDark = sh.shot === 'N' && t < FILM.events.land + 0.3;
  composeText(ctx, onDark ? 0.7 : 0.18, onDark ? 12 : 6);
  if (behind && (sh.shot === 'N' || sh.shot === 'N3')) await drawForeground(ctx, sh, lf);
  if (sh.shot === 'O1' && t >= accPg.t0 - 0.02 && t < 48.6) drawProjected(ctx, accPg, t, sh, lf);

  // graphics
  if (sh.id === 'M3') drawButtonPulse(ctx, sh, lf, lt);
  if (sh.id === 'M6') drawLdrMeter(ctx, sh, lt);
  drawLabel(ctx, sh, lt);
  if (VERT && sh.kind === 'real') drawRealStatus(ctx, t);
  drawLcdStrip(ctx, t, sh, pages);

  // transitions
  if (sh.id === 'H1') { ctx.fillStyle = `rgba(0,0,0,${seg(lt, 2.22, 2.4)})`; ctx.fillRect(0, 0, W, H); }
  if (sh.id === 'N' && lt < 0.25) { ctx.fillStyle = `rgba(0,0,0,${1 - seg(lt, 0, 0.25)})`; ctx.fillRect(0, 0, W, H); }
  dotWipe(ctx, t, 30.0, C.bone);
  dotWipe(ctx, t, 43.8, '#0d0d0f');
  grade(ctx, fi);
  return true;
};
await document.fonts.load('500 20px Mono');
window.READY = true;
