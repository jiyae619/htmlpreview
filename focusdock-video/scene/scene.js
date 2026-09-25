// FocusDock intro / outro scenes. Deterministic: window.renderFrame(t) renders time t (seconds).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
const W = +q.get('w') || 1920, H = +q.get('h') || 1080;
const SHOT = q.get('shot') || 'intro';
const U = H / 1080;
const CFG = JSON.parse(decodeURIComponent(q.get('cfg') || '%7B%7D'));
document.documentElement.style.setProperty('--u', U);
const stage = document.getElementById('stage');
stage.style.width = W + 'px'; stage.style.height = H + 'px';
const ui = document.getElementById('ui');
const lines = document.getElementById('lines');
lines.setAttribute('width', W); lines.setAttribute('height', H);
const fadeEl = document.getElementById('fade');

// ---------- helpers ----------
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const seg = (t, a, b) => clamp01((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const inOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const outCubic = (x) => 1 - Math.pow(1 - x, 3);
const inCubic = (x) => x * x * x;
const outBack = (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
const smooth = (x) => x * x * (3 - 2 * x);
function outBounce(x) {
  const n1 = 7.5625, d1 = 2.75;
  if (x < 1 / d1) return n1 * x * x;
  if (x < 2 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
  if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
  return n1 * (x -= 2.625 / d1) * x + 0.984375;
}
function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const v3 = (x, y, z) => new THREE.Vector3(x, y, z);
const lerpV = (a, b, k) => a.clone().lerp(b, k);
const col = (h) => new THREE.Color(h);
const mmss = (s) => { s = Math.max(0, Math.floor(s)); const m = Math.floor(s / 60) % 100; return String(m).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
stage.insertBefore(renderer.domElement, stage.firstChild);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(32, W / H, 0.05, 100);

const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.9, 0.6, 1.35);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// background gradient (screen space)
const bgCanvas = document.createElement('canvas'); bgCanvas.width = 16; bgCanvas.height = 256;
const bgCtx = bgCanvas.getContext('2d');
const bgTex = new THREE.CanvasTexture(bgCanvas); bgTex.colorSpace = THREE.SRGBColorSpace;
scene.background = bgTex;
let bgKey = '';
function setBackground(top, bottom) {
  const key = top.getHexString() + bottom.getHexString();
  if (key === bgKey) return; bgKey = key;
  const g = bgCtx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, '#' + top.getHexString()); g.addColorStop(1, '#' + bottom.getHexString());
  bgCtx.fillStyle = g; bgCtx.fillRect(0, 0, 16, 256); bgTex.needsUpdate = true;
}

// ---------- lights ----------
const key = new THREE.DirectionalLight(0xfff3e6, 2.4);
key.position.set(-3.5, 6, 4.5); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02;
Object.assign(key.shadow.camera, { left: -4, right: 4, top: 4, bottom: -4, near: 0.5, far: 20 });
scene.add(key);
const rim = new THREE.DirectionalLight(0x8fb8ff, 1.3); rim.position.set(3, 3, -5); scene.add(rim);
const fill = new THREE.HemisphereLight(0xdfe8ff, 0x20242c, 0.35); scene.add(fill);

// ---------- floor ----------
const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.42 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
function radialTex(inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)') {
  const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, inner); g.addColorStop(1, outer);
  x.fillStyle = g; x.fillRect(0, 0, 256, 256); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const poolMat = new THREE.MeshBasicMaterial({ map: radialTex(), transparent: true, opacity: 0.16, depthWrite: false, color: 0xffffff });
const pool = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), poolMat);
pool.rotation.x = -Math.PI / 2; pool.position.y = 0.001; scene.add(pool);
// coloured LED spill on the floor
const spillMat = new THREE.MeshBasicMaterial({ map: radialTex(), transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, color: 0x33ff88 });
const spill = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 2.2), spillMat);
spill.rotation.x = -Math.PI / 2; spill.position.set(-0.2, 0.002, 1.25); scene.add(spill);

// ---------- paper texture ----------
function paperTex(seed) {
  const c = document.createElement('canvas'); c.width = c.height = 512; const x = c.getContext('2d');
  const img = x.createImageData(512, 512); const r = rng(seed);
  for (let i = 0; i < img.data.length; i += 4) { const v = 150 + r() * 70; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  x.putImageData(img, 0, 0);
  // fine cross-hatch like book-cloth
  x.globalAlpha = 0.18; x.strokeStyle = '#000';
  for (let i = 0; i < 512; i += 3) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 512); x.stroke(); x.beginPath(); x.moveTo(0, i); x.lineTo(512, i); x.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(3, 3); return t;
}
const paper = paperTex(7);

// ---------- dock ----------
const dock = new THREE.Group(); scene.add(dock);
const dockBody = new THREE.Group(); dock.add(dockBody);
const BW = 2.2, BD = 1.3, BH = 0.62, LW = 2.26, LD = 1.36, LY0 = 0.58, LY1 = 0.96;
const shellMats = [];
function shellMat(color, rough = 0.8) {
  const m = new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0.0, roughnessMap: paper, bumpMap: paper, bumpScale: 0.04 });
  shellMats.push(m); return m;
}
const blackMat = shellMat(0x121317, 0.9), topMat = shellMat(0x192030, 0.85), creamMat = shellMat(0xc9bc9c, 0.8);
function box(w, h, d, mat, x = 0, y = 0, z = 0, parent = dockBody) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z);
  m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
}
box(BW, BH - 0.035, BD, blackMat, 0, 0.035 + (BH - 0.035) / 2, 0);
box(BW + 0.014, 0.035, BD + 0.014, creamMat, 0, 0.0175, 0);
// lid: sides black, top navy
const lidMats = [blackMat, blackMat, topMat, blackMat, blackMat, blackMat];
const lid = new THREE.Mesh(new THREE.BoxGeometry(LW, LY1 - LY0 - 0.035, LD), lidMats);
lid.position.set(0, LY0 + 0.035 + (LY1 - LY0 - 0.035) / 2, 0); lid.castShadow = lid.receiveShadow = true; dockBody.add(lid);
box(LW + 0.014, 0.035, LD + 0.014, creamMat, 0, LY0 + 0.0175, 0);
// cream rim around top edge
const rimT = 0.022, rimW = 0.028;
box(LW + 0.014, rimT, rimW, creamMat, 0, LY1 - rimT / 2 + 0.001, LD / 2 - rimW / 2 + 0.007);
box(LW + 0.014, rimT, rimW, creamMat, 0, LY1 - rimT / 2 + 0.001, -LD / 2 + rimW / 2 - 0.007);
box(rimW, rimT, LD, creamMat, LW / 2 - rimW / 2 + 0.007, LY1 - rimT / 2 + 0.001, 0);
box(rimW, rimT, LD, creamMat, -LW / 2 + rimW / 2 - 0.007, LY1 - rimT / 2 + 0.001, 0);
// sensor opening on top
const holeMat = new THREE.MeshStandardMaterial({ color: 0x030304, roughness: 1 });
const hole = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.3), holeMat);
hole.rotation.x = -Math.PI / 2; hole.position.set(0, LY1 + 0.0015, 0); dockBody.add(hole);
shellMats.push(holeMat);

// LCD
const LCDC = { cols: 16, rows: 2, p: 9 };
const lcdCanvas = document.createElement('canvas');
lcdCanvas.width = (16 * 6 - 1 + 6) * LCDC.p; lcdCanvas.height = (2 * 9 - 1 + 6) * LCDC.p;
const lcdCtx = lcdCanvas.getContext('2d');
const lcdTex = new THREE.CanvasTexture(lcdCanvas); lcdTex.colorSpace = THREE.SRGBColorSpace; lcdTex.anisotropy = 8;
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
  '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'], '>': ['01000', '00100', '00010', '00001', '00010', '00100', '01000'],
};
let lcdKey = null;
function drawLCD(line1, line2, backlight = 1) {
  const k = line1 + '|' + line2 + '|' + backlight.toFixed(2);
  if (k === lcdKey) return; lcdKey = k;
  const { p } = LCDC, x = lcdCtx;
  const bl = backlight;
  x.fillStyle = `rgb(${Math.round(lerp(8, 30, bl))},${Math.round(lerp(14, 86, bl))},${Math.round(lerp(40, 232, bl))})`;
  x.fillRect(0, 0, lcdCanvas.width, lcdCanvas.height);
  const g = x.createLinearGradient(0, 0, 0, lcdCanvas.height);
  g.addColorStop(0, 'rgba(255,255,255,0.10)'); g.addColorStop(1, 'rgba(0,0,40,0.18)'); x.fillStyle = g; x.fillRect(0, 0, lcdCanvas.width, lcdCanvas.height);
  const rows = [line1.padEnd(16).slice(0, 16), line2.padEnd(16).slice(0, 16)];
  for (let r = 0; r < 2; r++) for (let c = 0; c < 16; c++) {
    const glyph = FONT[rows[r][c]] || FONT[' '];
    for (let gy = 0; gy < 8; gy++) for (let gx = 0; gx < 5; gx++) {
      const on = gy < 7 && glyph[gy][gx] === '1';
      const px = (3 + c * 6 + gx) * p, py = (3 + r * 9 + gy) * p;
      x.fillStyle = on ? `rgba(235,244,255,${0.35 + 0.65 * bl})` : 'rgba(255,255,255,0.075)';
      x.fillRect(px + 0.6, py + 0.6, p - 1.5, p - 1.5);
    }
  }
  lcdTex.needsUpdate = true;
}
const LCD_X = 0.3, LCD_Y = 0.33, FZ = BD / 2;
const pcbMat = new THREE.MeshStandardMaterial({ color: 0x1d6b3a, roughness: 0.5 });
const bezelMat = new THREE.MeshStandardMaterial({ color: 0x0b0c0e, roughness: 0.4, metalness: 0.2 });
shellMats.push(pcbMat, bezelMat);
box(0.98, 0.36, 0.012, pcbMat, LCD_X, LCD_Y, FZ + 0.006);
box(0.86, 0.26, 0.03, bezelMat, LCD_X, LCD_Y, FZ + 0.015);
const lcdMat = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xffffff, emissiveMap: lcdTex, emissiveIntensity: 1.05, roughness: 0.18, metalness: 0 });
const lcd = new THREE.Mesh(new THREE.PlaneGeometry(0.76, 0.175), lcdMat);
lcd.position.set(LCD_X, LCD_Y, FZ + 0.031); dockBody.add(lcd);

// LEDs
function makeLED(color, x, y) {
  const g = new THREE.Group();
  const mat = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(color).multiplyScalar(0.35), roughness: 0.15, transmission: 0, clearcoat: 1, emissive: color, emissiveIntensity: 0 });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(0.032, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2), mat);
  dome.rotation.x = Math.PI / 2; dome.position.z = 0.03;
  const cyl = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.036, 0.03, 24), mat); cyl.rotation.x = Math.PI / 2; cyl.position.z = 0.015;
  g.add(dome, cyl); g.position.set(x, y, FZ); dockBody.add(g);
  const light = new THREE.PointLight(color, 0, 4, 2); light.position.set(x, y - 0.12, FZ + 0.6); dockBody.add(light);
  return { g, mat, light, set(v) { mat.emissiveIntensity = v * 7; light.intensity = v * 1.1; } };
}
const ledRed = makeLED(0xff2a1a, -0.38, 0.41);
const ledGreen = makeLED(0x22ff6a, -0.38, 0.29);

// side button on mini breadboard (right side)
const bbMat = new THREE.MeshStandardMaterial({ color: 0xf1f0ea, roughness: 0.55 }); shellMats.push(bbMat);
box(0.1, 0.42, 0.56, bbMat, BW / 2 + 0.05, 0.3, 0.22);
const btnCap = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.05, 28), new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.5 }));
btnCap.rotation.z = Math.PI / 2; btnCap.position.set(BW / 2 + 0.125, 0.33, 0.22); btnCap.castShadow = true; dockBody.add(btnCap);
shellMats.push(btnCap.material);
const btnBase = box(0.03, 0.13, 0.13, new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.6 }), BW / 2 + 0.11, 0.33, 0.22);
shellMats.push(btnBase.material);
// USB cable
const cableCurve = new THREE.CatmullRomCurve3([v3(BW / 2 + 0.1, 0.12, -0.35), v3(BW / 2 + 0.45, 0.05, -0.5), v3(BW / 2 + 0.8, 0.03, -1.3), v3(BW / 2 + 0.6, 0.03, -3.5)]);
const cable = new THREE.Mesh(new THREE.TubeGeometry(cableCurve, 64, 0.025, 10), new THREE.MeshPhysicalMaterial({ color: 0x5aa9e6, roughness: 0.3, transmission: 0.0, clearcoat: 0.6 }));
cable.castShadow = true; dockBody.add(cable);

// ---------- phone ----------
const phone = new THREE.Group(); scene.add(phone);
const PL = 1.55, PT = 0.075, PWd = 0.74;
const phoneBody = new THREE.Mesh(new RoundedBoxGeometry(PWd, PT, PL, 6, 0.07), new THREE.MeshPhysicalMaterial({ color: 0x2c2f35, metalness: 0.55, roughness: 0.32, clearcoat: 0.6 }));
phoneBody.castShadow = true; phoneBody.receiveShadow = true; phone.add(phoneBody);
const scrCanvas = document.createElement('canvas'); scrCanvas.width = 488; scrCanvas.height = 1024;
const scrCtx = scrCanvas.getContext('2d');
const scrTex = new THREE.CanvasTexture(scrCanvas); scrTex.colorSpace = THREE.SRGBColorSpace; scrTex.anisotropy = 8;
const scrMat = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xffffff, emissiveMap: scrTex, emissiveIntensity: 1, roughness: 0.12, metalness: 0 });
const screen = new THREE.Mesh(new THREE.PlaneGeometry(PWd - 0.07, PL - 0.08), scrMat);
screen.rotation.x = -Math.PI / 2; screen.position.y = PT / 2 + 0.001; phone.add(screen);
// camera bump on the back
const bump = new THREE.Mesh(new RoundedBoxGeometry(0.3, 0.02, 0.3, 4, 0.05), new THREE.MeshPhysicalMaterial({ color: 0x3a3d44, metalness: 0.5, roughness: 0.25 }));
bump.position.set(-PWd / 2 + 0.22, -PT / 2 - 0.008, -PL / 2 + 0.24); phone.add(bump);
for (const [dx, dz] of [[-0.065, -0.065], [0.065, -0.065], [-0.065, 0.065]]) {
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.02, 24), new THREE.MeshPhysicalMaterial({ color: 0x0a0a0c, metalness: 0.2, roughness: 0.05, clearcoat: 1 }));
  lens.position.set(bump.position.x + dx, -PT / 2 - 0.02, bump.position.z + dz); phone.add(lens);
}
let scrKey = null;
function drawScreen(on, flash) {
  const k = on.toFixed(2) + '|' + flash.toFixed(2);
  if (k === scrKey) return; scrKey = k;
  const x = scrCtx, w = scrCanvas.width, h = scrCanvas.height;
  x.fillStyle = '#000'; x.fillRect(0, 0, w, h);
  if (on <= 0.001) { scrTex.needsUpdate = true; return; }
  x.save(); x.globalAlpha = on;
  const pw = w, ph = h;
  const g = x.createLinearGradient(0, 0, pw, ph); g.addColorStop(0, '#5b3df5'); g.addColorStop(0.55, '#c13dd8'); g.addColorStop(1, '#ff7a59');
  x.fillStyle = g; x.fillRect(0, 0, pw, ph);
  x.fillStyle = 'rgba(255,255,255,0.95)'; x.textAlign = 'center';
  x.font = '600 34px Inter'; x.fillText('Tuesday, March 10', pw / 2, 150);
  x.font = '700 150px SG'; x.fillText('9:41', pw / 2, 290);
  for (let i = 0; i < 4; i++) { x.fillStyle = 'rgba(255,255,255,0.78)'; const y = 390 + i * 120; x.beginPath(); x.roundRect(28, y, pw - 56, 100, 26); x.fill();
    x.fillStyle = ['#34c759', '#ff2d55', '#ff3b30', '#0a84ff'][i]; x.beginPath(); x.roundRect(48, y + 22, 56, 56, 14); x.fill();
    x.fillStyle = 'rgba(0,0,0,0.55)'; x.fillRect(122, y + 30, 200, 16); x.fillStyle = 'rgba(0,0,0,0.3)'; x.fillRect(122, y + 58, 260, 14); }
  x.restore();
  if (flash > 0) { x.fillStyle = `rgba(255,255,255,${0.35 * flash})`; x.fillRect(0, 0, w, h); }
  scrTex.needsUpdate = true;
}
const phoneGlow = new THREE.PointLight(0xb070ff, 0, 3, 2); phone.add(phoneGlow); phoneGlow.position.y = 0.4;

// ---------- ambient particles ----------
const NP = 160; const pr = rng(42);
const pGeo = new THREE.BufferGeometry(); const pPos = new Float32Array(NP * 3); const pSeed = [];
for (let i = 0; i < NP; i++) pSeed.push([(pr() - 0.5) * 9, pr() * 4, (pr() - 0.5) * 6 - 1, pr(), 0.3 + pr() * 0.7]);
pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
const dotTex = radialTex('rgba(255,255,255,1)', 'rgba(255,255,255,0)');
const pMat = new THREE.PointsMaterial({ map: dotTex, size: 0.05, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: 0x9cffc9, opacity: 0 });
const particles = new THREE.Points(pGeo, pMat); scene.add(particles);
function updateParticles(t, opacity, color) {
  for (let i = 0; i < NP; i++) { const [x, y, z, ph, sp] = pSeed[i]; pPos[i * 3] = x + Math.sin(t * 0.3 + ph * 6) * 0.2; pPos[i * 3 + 1] = (y + t * 0.12 * sp) % 4; pPos[i * 3 + 2] = z; }
  pGeo.attributes.position.needsUpdate = true; pMat.opacity = opacity; if (color) pMat.color.set(color);
}

// landing ring
const ringMat = new THREE.MeshBasicMaterial({ color: 0xc9b8ff, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
const ring = new THREE.Mesh(new THREE.RingGeometry(0.985, 1.0, 128), ringMat); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.004; scene.add(ring);
const ring2Mat = new THREE.MeshBasicMaterial({ color: 0x6ef2a4, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
const ring2 = new THREE.Mesh(new THREE.RingGeometry(0.985, 1.0, 128), ring2Mat); ring2.rotation.x = -Math.PI / 2; scene.add(ring2);

// ---------- DOM overlay ----------
const ICONS = {
  chat: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 3C6.5 3 2 6.6 2 11c0 2.4 1.3 4.6 3.4 6.1L4.5 21l4.2-2.2c1 .3 2.1.4 3.3.4 5.5 0 10-3.6 10-8S17.5 3 12 3z"/></svg>',
  heart: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 21s-7.5-4.6-10-9.3C.4 8.4 2.3 4.5 6 4.1c2.2-.2 4 1 6 3.2 2-2.2 3.8-3.4 6-3.2 3.7.4 5.6 4.3 4 7.6C19.5 16.4 12 21 12 21z"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M7 4.5v15l13-7.5z"/></svg>',
  bag: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M6 7h12l1 14H5L6 7zm3 0a3 3 0 0 1 6 0h-1.6a1.4 1.4 0 0 0-2.8 0H9z"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M3 5h18v14H3V5zm2 2v.5l7 4.5 7-4.5V7H5z"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 22a2.5 2.5 0 0 0 2.4-2h-4.8a2.5 2.5 0 0 0 2.4 2zm7-6V11a7 7 0 0 0-5-6.7V3a2 2 0 0 0-4 0v1.3A7 7 0 0 0 5 11v5l-2 2v1h18v-1z"/></svg>',
};
// x, y = resting centre as a fraction of the frame
const NOTIFS = [
  { app: 'Messages', msg: 'Are you free tonight?', c: '#34c759', i: 'chat', x: 0.21, y: 0.24 },
  { app: 'Social', msg: '12 people liked your post', c: '#ff2d55', i: 'heart', x: 0.79, y: 0.19 },
  { app: 'Video', msg: 'New video: 10 study hacks', c: '#ff3b30', i: 'play', x: 0.18, y: 0.47 },
  { app: 'Group chat', msg: '47 new messages', c: '#0a84ff', i: 'mail', x: 0.82, y: 0.42 },
  { app: 'Shop', msg: 'Flash deal ends in 10 min', c: '#ff9500', i: 'bag', x: 0.5, y: 0.09 },
  { app: 'Reminder', msg: 'Just one more scroll…', c: '#af52de', i: 'bell', x: 0.8, y: 0.66 },
];
const notifEls = NOTIFS.map((n) => {
  const el = document.createElement('div'); el.className = 'notif';
  el.innerHTML = `<div class="ic" style="background:${n.c}">${ICONS[n.i]}</div><div class="tx"><div class="app">${n.app}</div><div class="msg">${n.msg}</div></div><div class="when">now</div>`;
  el.style.opacity = 0; ui.appendChild(el); return el;
});
const badge = document.createElement('div'); badge.className = 'badge'; badge.style.opacity = 0; ui.appendChild(badge);

const title = document.createElement('div'); title.id = 'title';
title.innerHTML = `<div class="name">${'FocusDock'.split('').map((ch, i) => `<span class="${i >= 5 ? 'dock' : ''}">${ch}</span>`).join('')}</div><div class="tag">A smart box that tracks your ‘phone-down’ time</div>`;
ui.appendChild(title);
const titleLetters = [...title.querySelectorAll('.name span')];
const titleTag = title.querySelector('.tag');

// callout for the side button
const callout = document.createElement('div'); callout.className = 'callout'; callout.innerHTML = '<span class="dot"></span>Focus button'; ui.appendChild(callout);
const pulse = document.createElement('div'); pulse.className = 'pulse'; ui.appendChild(pulse);

// real-photo cards
function makeCard(src, cap, cls = '') {
  const el = document.createElement('div'); el.className = 'card ' + cls;
  el.innerHTML = `<img src="${src}">${cap ? `<div class="cap">${cap}</div>` : ''}`;
  el.style.opacity = 0; ui.appendChild(el); return el;
}
const chip = document.createElement('div'); chip.className = 'chip-top'; chip.innerHTML = '<span class="rec"></span>The real prototype'; chip.style.opacity = 0; ui.appendChild(chip);

const endCard = document.createElement('div'); endCard.id = 'endcard';
endCard.innerHTML = `
  <div class="ty">Thank you <svg class="smile" viewBox="0 0 64 64"><circle cx="32" cy="32" r="29" fill="#ffd34d"/><circle cx="22" cy="26" r="4" fill="#3a2a00"/><circle cx="42" cy="26" r="4" fill="#3a2a00"/><path d="M19 38c3.5 6 8 9 13 9s9.5-3 13-9" stroke="#3a2a00" stroke-width="4" fill="none" stroke-linecap="round"/></svg></div>
  <div class="who">Jiyae Choi</div>
  <div class="rule"></div>
  <div class="brand"><b>Focus<span>Dock</span></b> · Park your phone. Prove your focus.</div>
  <div class="course">HCDE 539 · Winter 2026</div>`;
ui.appendChild(endCard);
const endParts = [...endCard.children];

function toScreen(p) { const v = p.clone().project(camera); return { x: (v.x * 0.5 + 0.5) * W, y: (-v.y * 0.5 + 0.5) * H, z: v.z }; }

// ---------- shared state setters ----------
function setLEDs(red, green) {
  ledRed.set(red); ledGreen.set(green);
  spillMat.color.setRGB(0.2 + 0.8 * red, 0.2 + 0.8 * green, 0.35 * green + 0.1 * red);
  spillMat.opacity = Math.max(red, green) * 0.2;
}
function setCanvasFilter(blur, bright) {
  renderer.domElement.style.filter = blur > 0.05 || bright < 0.999 ? `blur(${blur * U}px) brightness(${bright})` : 'none';
}
function hideAllUI() {
  notifEls.forEach((e) => (e.style.opacity = 0)); badge.style.opacity = 0; title.style.opacity = 0;
  callout.style.opacity = 0; pulse.style.opacity = 0; chip.style.opacity = 0; endCard.style.opacity = 0;
}
// place a card by centre (fractions), width in px, rotation, scale
function placeCard(el, cx, cy, w, rot, sc, op) {
  el.style.opacity = op; el.style.width = w + 'px';
  el.style.transform = `translate(${cx * W}px, ${cy * H}px) translate(-50%, -50%) rotate(${rot}deg) scale(${sc})`;
}
const pending = [];
function setImg(img, src) { if (img.getAttribute('src') !== src) { img.setAttribute('src', src); pending.push(img.decode().catch(() => {})); } }

const DOCK_TOP = LY1 + PT / 2 + 0.002;
const PHONE_DOCKED = () => { phone.position.set(0, DOCK_TOP, 0.02); phone.rotation.order = 'YXZ'; phone.rotation.set(0, Math.PI / 2, Math.PI); };

// ---------- INTRO ----------
const I = CFG.intro || {};
const introCards = SHOT === 'intro' ? [
  makeCard('assets/IMG_1294.jpg', 'Focus on, phone away → <b style="color:#ff5a4a">red</b>'),
  makeCard('assets/IMG_1295.jpg', 'Phone docked → <b style="color:#1fbf62">green</b> + timer'),
  makeCard('assets/demo_first.jpg', '', 'full'),
] : [];

function intro(t) {
  const D = I.dur;
  hideAllUI();
  const land = I.land, hit = I.dockHit;
  // background: restless violet -> calm deep green once the phone is docked
  const calm = smooth(seg(t, land - 0.2, land + 1.2));
  setBackground(col(0x1b1238).lerp(col(0x06161a), calm), col(0x3b1a52).lerp(col(0x0c3b31), calm));
  poolMat.opacity = lerp(0.1, 0.16, calm);

  // dock drops in and bounces
  const dropK = seg(t, I.dockDrop, I.dockDrop + 1.0);
  dock.position.set(0, t < I.dockDrop ? 8 : (1 - outBounce(dropK)) * 3.4, 0);
  const sq = Math.sin(seg(t, hit - 0.02, hit + 0.35) * Math.PI) * 0.07;
  dock.scale.set(1 + sq, 1 - sq, 1 + sq);
  const rk = seg(t, hit, hit + 1.0); ring.scale.setScalar(1.3 + rk * 1.8); ringMat.opacity = rk > 0 && rk < 1 ? 0.45 * (1 - rk) : 0;

  // focus logic on the LCD / LEDs
  const press = Math.sin(seg(t, I.press, I.press + 0.25) * Math.PI);
  btnCap.position.x = BW / 2 + 0.125 - 0.03 * press;
  let l1 = 'FOCUS OFF', l2 = 'PRESS TO START', red = 0, green = 0;
  if (t >= I.press + 0.12) { l1 = 'FOCUS ON'; l2 = 'PHONE AWAY 00:00'; red = 1; }
  if (t >= land) { l2 = 'PHONE ON   ' + mmss(t - land); red = 0; green = 1; }
  red *= 1 - seg(t, land - 0.05, land + 0.08); green *= seg(t, land, land + 0.12);
  drawLCD(l1, l2, 1); setLEDs(red, green);
  const r2 = seg(t, land, land + 1.4); ring2.scale.setScalar(1.2 + r2 * 2.6); ring2Mat.opacity = r2 > 0 && r2 < 1 ? 0.7 * (1 - r2) : 0;

  // phone: rests on the desk and buzzes; then arcs up, flips face-down and lands on the dock
  const P0 = v3(-0.15, PT / 2, 1.95), P1 = v3(0, DOCK_TOP, 0.02);
  const lift = seg(t, I.lift, land), le = inOut(lift);
  const pos = lerpV(P0, P1, le); pos.y += Math.sin(lift * Math.PI) * 1.1;
  if (t > land) pos.y -= Math.sin(seg(t, land, land + 0.18) * Math.PI) * 0.015;
  phone.position.copy(pos);
  const pops = NOTIFS.map((_, i) => I.A[0] + 0.15 + i * ((I.A[1] - I.A[0] - 0.3) / (NOTIFS.length - 1)));
  let buzz = 0; pops.forEach((bt) => { const k = seg(t, bt, bt + 0.3); if (k > 0 && k < 1) buzz += Math.sin(k * Math.PI * 10) * (1 - k); });
  phone.rotation.order = 'YXZ';
  phone.rotation.set(0, buzz * 0.05 - 0.12 * (1 - le) + (Math.PI / 2) * inOut(seg(t, I.lift + 0.1, land - 0.1)), Math.PI * inOut(seg(t, I.lift + 0.2, land - 0.05)));
  const flash = pops.reduce((a, bt) => (t >= bt ? Math.max(a, 1 - seg(t, bt, bt + 0.35)) : a), 0);
  drawScreen(1 - seg(t, I.lift + 0.25, I.lift + 0.8), t < I.lift ? flash : 0);
  phoneGlow.intensity = (1 - seg(t, I.lift, I.lift + 0.7)) * (0.7 + flash * 1.4);

  // camera
  const K = [
    { t: 0, p: v3(0.45, 2.45, 4.35), l: v3(-0.1, 0.0, 1.85) },
    { t: I.B[0] - 0.35, p: v3(0.32, 2.2, 4.0), l: v3(-0.1, 0.02, 1.9) },
    { t: hit + 0.4, p: v3(1.6, 2.7, 6.6), l: v3(0, 0.55, 0.7) },      // wide: dock + phone
    { t: I.titleIn + 0.4, p: v3(1.3, 2.6, 6.9), l: v3(0, 0.95, 0.7) }, // tilt down: room for the title
    { t: I.D[0] - 0.1, p: v3(0.9, 2.6, 6.9), l: v3(0, 0.95, 0.7) },
    { t: I.press - 0.15, p: v3(2.9, 2.1, 5.4), l: v3(0.25, 0.5, 0.6) }, // see the side button
    { t: I.lift + 0.2, p: v3(2.9, 2.5, 6.3), l: v3(0.1, 0.8, 0.6) },
    { t: land + 0.5, p: v3(0.9, 1.75, 4.7), l: v3(0, 0.62, 0.1) },
    { t: D, p: v3(0.25, 1.45, 4.3), l: v3(0, 0.62, 0.1) },
  ];
  let k = 0; while (k < K.length - 2 && t > K[k + 1].t) k++;
  const a = K[k], b = K[k + 1], kk = inOut(seg(t, a.t, b.t));
  camera.position.copy(lerpV(a.p, b.p, kk)); camera.lookAt(lerpV(a.l, b.l, kk));
  camera.fov = 32; camera.updateProjectionMatrix(); camera.updateMatrixWorld();
  scene.updateMatrixWorld(true);

  // notifications
  const scr = toScreen(phone.localToWorld(v3(0, PT / 2, 0)));
  const blast = outCubic(seg(t, hit, hit + 0.6));
  const suckK = (i) => inCubic(seg(t, I.lift - 0.2 + i * 0.06, land - 0.35 + i * 0.03));
  NOTIFS.forEach((n, i) => {
    const el = notifEls[i], bt = pops[i];
    if (t < bt) { el.style.opacity = 0; return; }
    const k = outBack(seg(t, bt, bt + 0.45), 1.5);
    const bob = Math.sin((t - bt) * 2.1 + i * 1.7) * 7 * U;
    let x = lerp(scr.x, n.x * W, k), y = lerp(scr.y, n.y * H, k) + bob;
    // pushed to the edges by the dock's landing
    const ex = (n.x - 0.5) * W * 0.28 * blast, ey = (n.y - 0.5) * H * 0.35 * blast;
    const shake = t > hit && t < hit + 0.4 ? Math.sin((t - hit) * 70 + i) * 10 * U * (1 - seg(t, hit, hit + 0.4)) : 0;
    x += ex + shake; y += ey;
    let sc = (0.35 + 0.65 * k) * (1 - 0.18 * blast), op = seg(t, bt, bt + 0.15) * (1 - 0.55 * blast);
    const sk = suckK(i);
    x = lerp(x, scr.x, sk); y = lerp(y, scr.y, sk); sc *= 1 - 0.9 * sk; op *= 1 - sk;
    el.style.opacity = op; el.style.filter = blast > 0.01 ? `blur(${1.6 * blast * (1 - sk) * U}px)` : 'none';
    el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%) scale(${sc}) rotate(${(n.x > 0.5 ? 1 : -1) * (2 * (1 - k) + 3 * blast)}deg)`;
  });
  const nb = pops.filter((bt) => t >= bt).length;
  if (nb > 0 && t < land) {
    badge.textContent = ['3', '15', '28', '49', '72', '99+'][nb - 1];
    const bc = toScreen(phone.localToWorld(v3(PWd / 2 - 0.03, PT / 2, -PL / 2 + 0.03)));
    const bk = outBack(seg(t, pops[0], pops[0] + 0.3), 2) * (1 - seg(t, I.lift, I.lift + 0.3));
    badge.style.opacity = bk > 0.01 ? 1 : 0;
    badge.style.transform = `translate(${bc.x}px, ${bc.y}px) translate(-50%, -50%) scale(${bk * (1 + 0.18 * flash)})`;
  }

  // title while the narration says "a smart box that tracks your phone-down time"
  if (t > I.titleIn - 0.1 && t < I.titleOut + 0.8) {
    title.style.opacity = 1 - seg(t, I.titleOut, I.titleOut + 0.5);
    title.style.top = 0.075 * H + 'px';
    title.style.transform = `translateY(${-seg(t, I.titleOut, I.titleOut + 0.5) * 30 * U}px)`;
    titleLetters.forEach((s, i) => { const t0 = I.titleIn + i * 0.045; const kk = outBack(seg(t, t0, t0 + 0.55), 1.4); s.style.transform = `translateY(${(1 - kk) * 60 * U}px)`; s.style.opacity = seg(t, t0, t0 + 0.3); });
    const kt = outCubic(seg(t, I.titleIn + 0.55, I.titleIn + 1.1)); titleTag.style.opacity = kt; titleTag.style.transform = `translateY(${(1 - kt) * 20 * U}px)`;
  }
  // button callout
  const co = seg(t, I.press - 0.55, I.press - 0.3) * (1 - seg(t, I.press + 1.2, I.press + 1.5));
  if (co > 0) {
    const bp = toScreen(btnCap.localToWorld(v3(0, 0.03, 0)));
    callout.style.opacity = co; callout.style.transform = `translate(${bp.x + 40 * U}px, ${bp.y - 110 * U}px)`;
    const pk = ((t - (I.press - 0.5)) % 0.8) / 0.8;
    pulse.style.opacity = co * (1 - pk); pulse.style.transform = `translate(${bp.x}px, ${bp.y}px) translate(-50%, -50%) scale(${0.4 + pk * 1.3})`;
  }

  updateParticles(t, 0.85 * calm, 0x9cffc9);

  // real photos drop in, then the last one (the demo's first frame) grows to full frame
  const blurK = smooth(seg(t, I.photo1 - 0.1, I.photo1 + 0.6));
  setCanvasFilter(9 * blurK, 1 - 0.35 * blurK);
  chip.style.opacity = seg(t, I.photo1, I.photo1 + 0.3) * (1 - seg(t, I.expand, I.expand + 0.25));
  const cardSpec = [
    { at: I.photo1, x: 0.3, y: 0.5, w: 0.36 * W, r: -5 },
    { at: I.photo2, x: 0.71, y: 0.49, w: 0.24 * W, r: 4 },
    { at: I.photo3, x: 0.5, y: 0.53, w: 0.4 * W, r: -1.5 },
  ];
  introCards.forEach((el, i) => {
    const c = cardSpec[i]; if (t < c.at) { el.style.opacity = 0; return; }
    const k = outBack(seg(t, c.at, c.at + 0.55), 1.3), kIn = seg(t, c.at, c.at + 0.2);
    const drift = (t - c.at) * 0.004;
    let x = c.x + drift * (i === 1 ? -1 : 1), y = lerp(c.y + 0.5, c.y, k), rot = lerp(c.r * 3, c.r, k), w = c.w, sc = lerp(1.25, 1, k);
    if (i === 2) {
      const e = inOut(seg(t, I.expand, D - 1 / 30));
      el.style.padding = `${lerp(12, 0, e) * U}px`; el.style.borderRadius = `${lerp(6, 0, e) * U}px`;
      el.style.boxShadow = e >= 1 ? 'none' : '';
      x = lerp(x, 0.5, e); y = lerp(y, 0.5, e); rot = lerp(rot, 0, e); w = lerp(w + 24 * U, W, e); sc = lerp(sc, 1, e);
      if (e >= 1) { el.style.transform = 'none'; el.style.width = W + 'px'; el.style.opacity = 1; el.style.left = '0px'; el.style.top = '0px'; return; }
    }
    placeCard(el, x, y, w, rot, sc, kIn);
  });
  fadeEl.style.opacity = 1 - seg(t, 0, 0.6);
}

// ---------- OUTRO ----------
const O = CFG.outro || {};
const outroCards = SHOT === 'outro' ? [
  { el: makeCard('assets/demo_last.jpg', 'Live demo', 'full'), x: 0.25, y: 0.3, w: 0.33, r: -4, at: 0 },
  { el: makeCard('assets/IMG_1292.jpg', 'Inside: Arduino + photoresistor'), x: 0.52, y: 0.37, w: 0.2, r: 2.5, at: 0.5 },
  { el: makeCard('assets/clip_button/001.jpg', 'Button → Focus ON'), x: 0.78, y: 0.29, w: 0.28, r: 3.5, at: 0.8, clip: 'clip_button', n: 105 },
  { el: makeCard('assets/clip_timer/001.jpg', 'Phone docked → timer counts'), x: 0.26, y: 0.74, w: 0.3, r: 2, at: 1.1, clip: 'clip_timer', n: 180 },
  { el: makeCard('assets/IMG_1295.jpg', 'Park your phone.'), x: 0.75, y: 0.7, w: 0.17, r: -3, at: 1.4 },
] : [];

function outro(t) {
  const D = O.dur || 9;
  hideAllUI();
  setBackground(col(0x06141a), col(0x0d3a31)); poolMat.opacity = 0.16;
  dock.position.set(0, 0, 0); dock.scale.set(1, 1, 1); ringMat.opacity = 0; ring2Mat.opacity = 0;
  PHONE_DOCKED(); drawScreen(0, 0); phoneGlow.intensity = 0;
  // time-lapse timer: the focus session keeps adding up
  const tl = 12 + Math.pow(seg(t, 0, D), 1.7) * 3500;
  drawLCD('FOCUS ON', 'PHONE ON   ' + mmss(tl), 1); setLEDs(0, 1);

  // camera: slow orbit behind the gallery, then settle with the dock on the right
  const c0 = { p: v3(-2.2, 2.3, 5.2), l: v3(0, 0.5, 0) }, c1 = { p: v3(1.0, 2.0, 5.6), l: v3(-1.25, 0.55, 0) }, c2 = { p: v3(0.2, 1.7, 5.2), l: v3(-1.3, 0.62, 0) };
  let cp, cl;
  if (t < 5.2) { const k = inOut(seg(t, 0, 5.2)); cp = lerpV(c0.p, c1.p, k); cl = lerpV(c0.l, c1.l, k); }
  else { const k = inOut(seg(t, 5.2, D)); cp = lerpV(c1.p, c2.p, k); cl = lerpV(c1.l, c2.l, k); }
  camera.position.copy(cp); camera.lookAt(cl); camera.fov = 32; camera.updateProjectionMatrix(); camera.updateMatrixWorld();
  scene.updateMatrixWorld(true);

  const out0 = 4.3;
  const blurK = 1 - smooth(seg(t, out0, out0 + 1.0));
  setCanvasFilter(9 * blurK, 1 - 0.4 * blurK);
  chip.style.opacity = seg(t, 0.6, 0.9) * (1 - seg(t, out0 - 0.2, out0 + 0.1));
  outroCards.forEach((c, i) => {
    const el = c.el;
    if (c.clip) setImg(el.querySelector('img'), `assets/${c.clip}/${String(1 + (Math.floor(Math.max(0, t - c.at) * 30) % c.n)).padStart(3, '0')}.jpg`);
    const fly = inCubic(seg(t, out0 + i * 0.07, out0 + 0.6 + i * 0.07));
    const dir = c.x < 0.5 ? -1 : 1;
    if (i === 0) {
      // the last demo frame shrinks from full screen into the collage
      const e = inOut(seg(t, 0, 1.0));
      el.style.padding = `${lerp(0, 12, e) * U}px`; el.style.borderRadius = `${lerp(0, 6, e) * U}px`;
      if (e <= 0) { el.style.transform = 'none'; el.style.width = W + 'px'; el.style.opacity = 1; el.style.boxShadow = 'none'; return; }
      el.style.boxShadow = '';
      const x = lerp(0.5, c.x, e) + dir * fly * 0.8, y = lerp(0.5, c.y, e) - fly * 0.2;
      placeCard(el, x, y, lerp(W, c.w * W, e), lerp(0, c.r, e) + dir * fly * 25, 1, 1 - fly);
      el.querySelector('.cap').style.opacity = seg(t, 0.8, 1.1);
      return;
    }
    if (t < c.at) { el.style.opacity = 0; return; }
    const k = outBack(seg(t, c.at, c.at + 0.55), 1.3);
    const drift = Math.sin(t * 0.6 + i) * 0.004;
    placeCard(el, c.x + drift + dir * fly * 0.8, lerp(c.y + 0.55, c.y, k) - fly * 0.25, c.w * W, lerp(c.r * 3, c.r, k) + dir * fly * 25, lerp(1.2, 1, k), seg(t, c.at, c.at + 0.2) * (1 - fly));
  });

  // end card
  if (t > 5.0) {
    endCard.style.opacity = 1;
    endParts.forEach((p, i) => { const t0 = 5.1 + i * 0.22; const k = outCubic(seg(t, t0, t0 + 0.7)); p.style.opacity = k; p.style.transform = `translateY(${(1 - k) * 26 * U}px)`; });
  }
  updateParticles(t, 0.7, 0x9cffc9);
  fadeEl.style.opacity = seg(t, D - 0.9, D);
}

window.renderFrame = async (t) => {
  pending.length = 0;
  if (SHOT === 'intro') intro(t); else outro(t);
  composer.render();
  await Promise.all(pending);
  return true;
};
await Promise.all([...document.images].map((im) => im.decode().catch(() => {})));
await document.fonts.load('700 100px SG'); await document.fonts.load('500 20px Inter'); await document.fonts.load('600 20px Inter'); await document.fonts.ready;
window.READY = true;
