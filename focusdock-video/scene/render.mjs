// Usage: node render.mjs --shot intro --dur 12 --fps 30 --w 1920 --h 1080 [--stills 1,4,8] [--out file.mp4] [--cfg '{"tagline":"..."}']
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? [...a, [v.slice(2), arr[i + 1]]] : a), []));
const shot = args.shot || 'intro', fps = +(args.fps || 30), w = +(args.w || 1920), h = +(args.h || 1080);
const cfg = JSON.parse(args.cfg || '{}'); cfg.dur = +(args.dur || cfg.dur || 12);
const root = path.dirname(new URL(import.meta.url).pathname);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(d); });
}).listen(0);
const port = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
page.on('pageerror', (e) => console.error('[pageerror]', e.message));
await page.goto(`http://localhost:${port}/index.html?shot=${shot}&w=${w}&h=${h}&cfg=${encodeURIComponent(JSON.stringify(cfg))}`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
const clip = { x: 0, y: 0, width: w, height: h };

if (args.stills) {
  const outDir = args.outdir || path.join(root, 'stills'); fs.mkdirSync(outDir, { recursive: true });
  for (const t of args.stills.split(',').map(Number)) {
    await page.evaluate((t) => window.renderFrame(t), t);
    await page.screenshot({ path: path.join(outDir, `${shot}_${t.toFixed(2)}.jpg`), type: 'jpeg', quality: 88, clip });
  }
} else {
  const out = args.out || path.join(root, `${shot}.mp4`);
  const n = Math.round(cfg.dur * fps);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => window.renderFrame(t), i / fps);
    const buf = await page.screenshot({ type: 'png', clip });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 30 === 0) console.log(`${shot} frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise((r) => ff.on('close', r));
  console.log('wrote', out);
}
await browser.close(); server.close();
