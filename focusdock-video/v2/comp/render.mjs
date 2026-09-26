// Usage: node render.mjs [--stills f1,f2,...] [--from a --to b] [--out file.mp4]
import { chromium } from '../../anim/node_modules/playwright/index.mjs';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { spawn } from 'node:child_process';
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? [...a, [v.slice(2), arr[i + 1]]] : a), []));
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(d); });
}).listen(0);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', (e) => console.error('[pageerror]', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.error('[console]', m.text()); });
await page.goto(`http://localhost:${server.address().port}/v2/comp/index.html${args.v ? '?v=1' : ''}`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
const film = JSON.parse(fs.readFileSync(path.join(ROOT, 'v2/film.json')));
const grab = async () => Buffer.from((await page.evaluate(() => document.getElementById('c').toDataURL('image/png'))).split(',')[1], 'base64');
if (args.stills) {
  const dir = args.dir || path.join(ROOT, args.v ? 'v2/comp/stills_v' : 'v2/comp/stills'); fs.mkdirSync(dir, { recursive: true });
  for (const s of args.stills.split(',')) { const f = Math.round(parseFloat(s) * 30); await page.evaluate((f) => window.renderFrame(f), f); fs.writeFileSync(path.join(dir, `f_${String(f).padStart(4, '0')}.png`), await grab()); }
} else {
  const a = +(args.from ?? 0), b = +(args.to ?? film.frames);
  const out = args.out || path.join(ROOT, 'v2/comp/video.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = a; f < b; f++) {
    await page.evaluate((f) => window.renderFrame(f), f);
    const buf = await grab(); if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 60 === 0) console.log(`frame ${f}/${b} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r)); console.log('wrote', out);
}
await browser.close(); server.close();
