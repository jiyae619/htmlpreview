# FocusDock v2 soundtrack: "the notifications are the beat, until the phone goes down".
# 100 BPM, D major. Everything is placed from film.json; voice sits on top, music ducks under it.
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(f'{HERE}/film.json')); E = F['events']
SR = 48000; TOTAL = F['total']; N = int(TOTAL * SR)
BEAT = 60 / F['bpm']; BAR = 4 * BEAT
rng = np.random.default_rng(11)

def at(t): return int(round(t * SR))
def db(x): return 10 ** (x / 20)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a=0.005, tau=0.4, rel=0.02):
    t = np.arange(n) / SR; e = np.exp(-t / tau) * np.minimum(1, t / max(a, 1e-4))
    r = int(rel * SR)
    if r and r < n: e[-r:] *= np.linspace(1, 0, r)
    return e
def lp(x, fc, o=2): return sosfilt(butter(o, min(fc, SR / 2.2), 'low', fs=SR, output='sos'), x)
def hp(x, fc, o=2): return sosfilt(butter(o, fc, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, min(hi, SR / 2.2)], 'band', fs=SR, output='sos'), x)

class Bus:
    def __init__(self): self.L = np.zeros(N); self.R = np.zeros(N)
    def add(self, x, t, g=1.0, pan=0.0):
        i = at(t)
        if i >= N or i + len(x) <= 0: return
        if i < 0: x = x[-i:]; i = 0
        x = x[:N - i]; gl, gr = g * np.sqrt(0.5 * (1 - pan)), g * np.sqrt(0.5 * (1 + pan))
        self.L[i:i + len(x)] += gl * x; self.R[i:i + len(x)] += gr * x
    def arr(self): return np.stack([self.L, self.R], 1)

music, sfx = Bus(), Bus()

# ---------------------------------------------------------------- instruments
def ep(m, dur=1.6, vel=1.0):
    """FM electric piano: warm body + short tine."""
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m)
    idx = 1.6 * np.exp(-t / 0.35) + 0.25
    body = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    tine = 0.25 * np.sin(2 * np.pi * f * 4 * t + 2.0 * np.exp(-t / 0.03) * np.sin(2 * np.pi * f * 14 * t)) * np.exp(-t / 0.12)
    return (body + tine) * env(n, 0.004, 1.1, 0.08) * vel
def pad(notes, dur, bright=1600):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for m in notes:
        for det in (-0.07, 0.0, 0.06):
            f = mtof(m + det)
            x += sum(np.sin(2 * np.pi * f * h * t + h * 1.3) / h for h in range(1, 9))
    x = lp(x, bright)
    a = np.minimum(1, t / 0.8); r = np.minimum(1, (dur - t) / 0.9)
    return x * a * r / (len(notes) * 6)
def bell(f, dur=0.45, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t + 1.4 * bright * np.exp(-t / 0.06) * np.sin(2 * np.pi * f * 3.5 * t))
    x += 0.3 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / 0.05)
    return x * env(n, 0.001, 0.11, 0.03)
def kick(g=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(48 + 80 * np.exp(-t / 0.035)) / SR
    x = np.sin(ph) * np.exp(-t / 0.2) + 0.15 * lp(rng.standard_normal(n), 3000) * np.exp(-t / 0.004)
    return x * g
def tick(freq=2600, dur=0.03, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sign(np.sin(2 * np.pi * freq * t)) * 0.4 + hp(rng.standard_normal(n), 3000) * 0.6) * np.exp(-t / 0.006) * g
def hat(g=1.0):
    n = int(0.05 * SR); return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR / 0.012) * g
def click(g=1.0):  # tactile push-button
    n = int(0.07 * SR); t = np.arange(n) / SR
    return (hp(rng.standard_normal(n), 1500) * np.exp(-t / 0.004) + 0.5 * np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.008)) * g
def sub(m, dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m)
    return (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)) * env(n, 0.01, dur * 0.7, 0.05) * g
def buzz(dur=0.22, f=55):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * f * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * t))
    return lp(x, 700) * env(n, 0.005, dur, 0.04)
def whoosh(dur, f0, f1, q=0.4):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); step = 1024
    for i in range(0, n, step):
        k = i / n; fc = f0 * (f1 / f0) ** k; s = x[max(0, i - 2048): i + step]
        y = bp(s, max(30, fc * (1 - q)), fc * (1 + q))[-min(step, n - i):]; out[i:i + len(y)] = y
    return out * np.sin(np.linspace(0, np.pi, n)) ** 1.4 / (np.abs(out).max() + 1e-9)
def impact(g=1.0):
    n = int(1.6 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(30 + 60 * np.exp(-t / 0.12)) / SR
    x = np.sin(ph) * np.exp(-t / 0.5) + 0.5 * lp(rng.standard_normal(n), 900) * np.exp(-t / 0.05)
    return x * g
def thock(g=1.0, low=90):
    n = int(0.5 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(low * 0.6 + low * np.exp(-t / 0.02)) / SR
    x = np.sin(ph) * np.exp(-t / 0.09) + 0.35 * bp(rng.standard_normal(n), 300, 2500) * np.exp(-t / 0.01) + 0.2 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    return x * g
def shimmer(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for m in (86, 90, 93, 97, 98):
        x += np.sin(2 * np.pi * mtof(m) * t + rng.random() * 6) * (0.5 + 0.5 * np.sin(2 * np.pi * (3 + rng.random() * 4) * t))
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2 / 5
def reverse_swell(dur=1.2, notes=(62, 66, 69, 73)):
    x = pad(notes, dur, 3000); x = x * np.linspace(0, 1, len(x)) ** 3
    return x

# ---------------------------------------------------------------- score
D_PENT_HI = [86, 89, 91, 93, 96, 98]          # D minor-ish pentatonic up high: restless
# cold open
sfx.add(bell(mtof(89), 0.5), 0.12, 0.28, 0.2)
sfx.add(thock(1.0, 95), E['hit_cold'], 0.9)
music.add(impact(0.55), E['hit_cold'], 0.6)
sfx.add(tick(3200, 0.02), E['hit_cold'] + 0.04, 0.35); sfx.add(tick(2400, 0.02), E['hit_cold'] + 0.09, 0.3)
music.add(pad([50, 57, 62, 66, 69, 76], 1.8, 2000), E['hit_cold'] + 0.05, 0.9)
sfx.add(tick(2600, 0.02), 1.62, 0.3)

# noise: every tile pop is a ping; phone buzz on the beat; typing clicks; riser into the slam
spawn = [2.4 + 0.25 + i * 0.23 for i in range(26)]
for i, s in enumerate(spawn):
    if s >= 9.4: break
    m = D_PENT_HI[int(rng.integers(len(D_PENT_HI)))] + (12 if rng.random() < 0.2 else 0)
    music.add(bell(mtof(m), 0.4, 1.2), s, 0.20, rng.uniform(-0.7, 0.7))
grid = np.arange(2.4, 9.35, BEAT / 4)
for j, g in enumerate(grid):
    dens = 0.15 + 0.7 * (g - 2.4) / 7.0
    if rng.random() < dens * 0.5:
        m = D_PENT_HI[int(rng.integers(len(D_PENT_HI)))]
        music.add(bell(mtof(m), 0.25, 0.8), g, 0.08, rng.uniform(-0.9, 0.9))
    if j % 2 == 0: music.add(hat(0.5 + 0.5 * dens), g, 0.10, rng.uniform(-0.3, 0.3))
for b in np.arange(2.4, 9.35, BEAT):
    music.add(buzz(0.2 if b < 6.0 else 0.14), b, 0.20)
    if b > 6.0: music.add(buzz(0.12), b + BEAT / 2, 0.14)
    music.add(sub(38, 0.5, 0.5), b, 0.35)
music.add(whoosh(2.2, 200, 4000, 0.3), 7.15, 0.16)
n = int(2.2 * SR); tt = np.arange(n) / SR
music.add(np.sin(2 * np.pi * np.cumsum(220 * 2 ** (tt / 2.2 * 1.6)) / SR) * (tt / 2.2) ** 2 * 0.5, 7.15, 0.10)

# the slam: hard stop, impact, glass scatter
sfx.add(impact(1.0), E['slam'], 0.95); sfx.add(thock(0.8, 70), E['slam'], 0.7)
for k in range(46):
    tt0 = E['slam'] + 0.03 + rng.exponential(0.22)
    sfx.add(bell(rng.uniform(2800, 7500), 0.12, 0.4), tt0, 0.05 * np.exp(-(tt0 - E['slam']) * 2), rng.uniform(-1, 1))
music.add(sub(38, 3.0, 0.8), E['slam'] + 0.05, 0.3)          # low drone under "I built FocusDock"
music.add(pad([38, 45, 50], 3.2, 700), E['slam'] + 0.1, 0.8)
# phone lift and landing -> the drop
sfx.add(whoosh(1.1, 300, 1800), 12.05, 0.22)
music.add(reverse_swell(1.2), E['land'] - 1.2, 0.9)
sfx.add(thock(0.8, 100), E['land'], 0.75); sfx.add(tick(3000, 0.02), E['land'] + 0.03, 0.35)

# the calm groove: D major, heartbeat kick, LCD-tick snare, button-click hats
PROG = [([50, 57, 61, 64, 66], 38), ([47, 54, 57, 61, 62], 35), ([43, 50, 54, 57, 62], 31), ([45, 52, 55, 59, 61], 33)]  # Dmaj9 Bm11 Gmaj9 A7sus-ish
GROOVE = [(E['land'], 43.8 + 0.0), (43.8, 48.9)]
def groove(t0, t1, energy=1.0, arp=False, hats16=None):
    b = 0; t = t0
    while t < t1 - 0.05:
        chord, root = PROG[b % 4]
        dur = min(BAR, t1 - t)
        music.add(pad(chord, dur + 0.6, 1900), t, 0.55 * energy)
        for i, m in enumerate(chord[1:]):
            music.add(ep(m, 1.8, 0.7), t + i * 0.012, 0.10 * energy, (i - 2) * 0.25)
        for k in range(4):
            tb = t + k * BEAT
            if tb >= t1 - 0.02: break
            if k in (0, 2): music.add(kick(1.0), tb, 0.42 * energy)
            if k in (1, 3): music.add(tick(2200, 0.03), tb, 0.13 * energy)
            music.add(sub(root, BEAT * (1.6 if k in (0, 2) else 0.8), 1.0), tb, 0.30 * energy if k in (0, 2) else 0.12 * energy)
            for h in (0, 1):
                th = tb + h * BEAT / 2
                if th < t1: music.add(click(0.5), th, 0.06 * energy, 0.3 if h else -0.3)
            if hats16 and hats16[0] <= tb < hats16[1]:
                for h in (1, 3): music.add(hat(1), tb + h * BEAT / 4, 0.06, 0.4)
            if arp:
                for q in range(4):
                    ta = tb + q * BEAT / 4
                    if ta < t1: music.add(bell(mtof(chord[(q + k) % len(chord)] + 24), 0.3, 0.3), ta, 0.035 * energy, np.sin(q + k))
        t += BAR; b += 1
groove(E['land'], 30.0, 0.9, arp=False)
groove(30.0, 43.8, 1.0, arp=True, hats16=(37.8, 40.2))
groove(43.8, 48.9, 1.05, arp=True)

# anatomy accents
sfx.add(tick(2800, 0.02), 20.4, 0.3); sfx.add(bell(mtof(81), 0.6, 0.5), 20.4, 0.10)     # LED red -> green
sfx.add(click(1.0), E['press3d'], 0.55)
sfx.add(shimmer(1.5), E['beam'] - 0.1, 0.35)
sfx.add(thock(0.4, 140), E['cover'] + 0.35, 0.3)
# real footage accents
for tc, col in ((30.0, 0), (43.8, 1)): sfx.add(whoosh(0.6, 400 if col == 0 else 1600, 1600 if col == 0 else 300), tc - 0.3, 0.18)
sfx.add(click(1.0), E['press_real'], 0.5)
sfx.add(bell(mtof(74), 0.5, 0.4), E['focus_on_real'], 0.12); sfx.add(bell(mtof(77), 0.5, 0.4), E['focus_on_real'] + 0.08, 0.1)
for i, m in enumerate((74, 78, 81, 86)): sfx.add(bell(mtof(m), 0.9, 0.5), E['green_real'] + i * 0.06, 0.11)
for k in np.arange(37.8, 40.2, BEAT / 2): sfx.add(tick(3100, 0.015), k, 0.12)                       # time-lapse clock
sfx.add(bell(mtof(70), 0.9, 1.6), E['red_real'], 0.14); sfx.add(bell(mtof(71), 0.9, 1.6), E['red_real'] + 0.02, 0.1)
# outro build, then the end card
music.add(whoosh(1.3, 300, 5000, 0.3), 47.6, 0.14)
music.add(reverse_swell(1.0, (62, 66, 69, 76)), 47.9, 0.6)
music.add(pad([50, 57, 62, 66, 69, 76], 4.4, 1400), 48.9, 0.75)
music.add(sub(38, 1.2, 1.0), 48.9, 0.25)
music.add(pad([38, 50, 57, 61, 64, 66, 71], 4.2, 2200), 50.4, 1.0)
music.add(kick(1.0), 50.4, 0.45); music.add(sub(38, 2.4, 1.0), 50.4, 0.35)
for i, m in enumerate((62, 66, 69, 73, 76, 78)): music.add(ep(m, 3.0, 0.8), 50.4 + i * 0.05, 0.10, (i - 3) * 0.2)
for k, ch in enumerate('FOCUSDOCK'): sfx.add(tick(2600 + 90 * k, 0.012), 50.45 + k * 0.03, 0.12)
for k in range(16): sfx.add(tick(2400, 0.01), 50.75 + k * 0.03, 0.08); sfx.add(tick(2500, 0.01), 51.65 + k * 0.03, 0.08)
sfx.add(whoosh(0.8, 1400, 300), 52.6, 0.12)
sfx.add(bell(mtof(86), 0.8, 0.3), 53.0, 0.1)
sfx.add(thock(0.5, 70), 54.25, 0.35)

# ---------------------------------------------------------------- voice
voice = np.zeros(N); active = np.zeros(N)
for v in F['vo']:
    x, sr = sf.read(f'{HERE}/vo/{v["id"]}.wav', dtype='float64')
    x = resample_poly(x, SR, sr); x = hp(x, 75)
    x = x + 0.25 * hp(x, 3500)                 # a little presence
    i = at(v['start']); x = x[:N - i]; voice[i:i + len(x)] += x; active[i:i + len(x)] = 1
voice /= np.abs(voice).max() + 1e-9
voice = np.tanh(voice * 1.8) / np.tanh(1.8)

# ---------------------------------------------------------------- mix
ir_n = int(1.9 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.5 * SR)); ir = lp(ir, 6000); ir /= np.sqrt((ir ** 2).sum())
mus = music.arr(); fx = sfx.arr()
mus = 0.8 * mus + 0.35 * np.stack([fftconvolve(mus[:, 0], ir)[:N], fftconvolve(mus[:, 1], ir[::-1].copy())[:N]], 1)
fx = fx + 0.22 * np.stack([fftconvolve(fx[:, 0], ir)[:N], fftconvolve(fx[:, 1], ir)[:N]], 1)
# duck the music under the voice (smooth, look-ahead)
w = int(0.25 * SR); cs = np.concatenate([[0], np.cumsum(active)]); idx = np.arange(N)
duck = (cs[np.clip(idx + w, 0, N)] - cs[np.clip(idx - w // 2, 0, N)]) / (1.5 * w)
duck = np.clip(duck, 0, 1)
mg = db(-13.5) * (1 - duck) + db(-23.5) * duck
mus *= (mg / (np.abs(mus).max() + 1e-9))[:, None]
fx *= db(-9) / (np.abs(fx).max() + 1e-9)
fx *= (1 - 0.45 * duck)[:, None]
vo = np.stack([voice, voice], 1) * db(-3.5)
mix = vo + mus + fx
tt = np.arange(N) / SR; mix *= np.clip((TOTAL - tt) / 0.35, 0, 1)[:, None]
mix /= max(1.0, np.abs(mix).max() / db(-1))
sf.write(f'{HERE}/soundtrack_raw.wav', mix.astype(np.float32), SR)
sf.write(f'{HERE}/stems_music.wav', (mus + fx).astype(np.float32), SR)
print('ok', round(TOTAL, 2), 's')
