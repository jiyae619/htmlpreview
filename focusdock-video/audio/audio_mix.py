# Builds the new soundtrack: TTS voice + procedural music bed + light SFX, all placed from timeline.json.
# Usage: python3 audio_mix.py [--no-music]
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt, fftconvolve

SR = 48000
TL = json.load(open("timeline.json"))
I, O = TL["intro"], TL["outro"]
T_DEMO = round(I["dur"] * TL["fps"]) / TL["fps"]; T_OUTRO = T_DEMO + TL["demoLen"]; TOTAL = T_OUTRO + O["dur"]
N = int(round(TOTAL * SR))
rng = np.random.default_rng(7)
MUSIC = "--no-music" not in sys.argv

def at(t): return int(round(t * SR))
def add(buf, x, t, gain=1.0):
    i = at(t)
    if i >= len(buf): return
    x = x[: len(buf) - i]; buf[i:i + len(x)] += gain * x
def env_exp(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def fade(x, a=0.005, r=0.02):
    x = x.copy(); na, nr = int(a * SR), int(r * SR)
    if na: x[:na] *= np.linspace(0, 1, na)
    if nr: x[-nr:] *= np.linspace(1, 0, nr)
    return x
def lp(x, fc, order=2): return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)
def db(x): return 10 ** (x / 20)

# ---------------- voice ----------------
voice = np.zeros(N)
active = np.zeros(N)  # 1 while someone is talking (for ducking)
def place_voice(lid, t):
    x, sr = sf.read(f"tts/af_heart/{lid}.wav", dtype="float64")
    if x.ndim > 1: x = x.mean(1)
    x = resample_poly(x, SR, sr)
    x = hp(x, 70)
    add(voice, fade(x, 0.004, 0.03), t)
    active[at(t):at(t) + len(x)] = 1
for lid in "ABCD": place_voice(lid, I[lid][0])
for lid, rel in TL["demo"].items(): place_voice(lid, T_DEMO + rel)
# gentle compression-ish: soft clip the peaks after normalising
voice /= np.max(np.abs(voice)) + 1e-9
voice = np.tanh(voice * 1.6) / np.tanh(1.6)

# ---------------- sfx ----------------
sfx = np.zeros(N)
def tone(f, dur, tau, harm=((1, 1.0),)):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * h * t) for h, a in harm) * env_exp(n, tau)
def ping(f):
    x = tone(f, 0.5, 0.09, ((1, 1), (2, 0.25), (3, 0.08))) + 0.7 * np.concatenate([np.zeros(int(0.07 * SR)), tone(f * 1.335, 0.43, 0.1, ((1, 1), (2, 0.2)))])
    return fade(x, 0.002, 0.05)
def buzz(dur=0.28):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * 165 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 28 * t))
    return fade(lp(x, 900) * np.minimum(1, 8 * (1 - t / dur)), 0.01, 0.04)
def whoosh(dur, f0, f1, q=0.35):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); step = 1024
    for i in range(0, n, step):
        k = i / n; fc = f0 * (f1 / f0) ** k
        seg = x[max(0, i - 2048): i + step]
        y = bp(seg, fc * (1 - q), fc * (1 + q))[-min(step, n - i):]
        out[i:i + len(y)] = y
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out * e / (np.max(np.abs(out)) + 1e-9)
def thud(f=58, dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (f * t + 25 * (1 - np.exp(-t * 30)) / 30)) * env_exp(n, 0.12)
    click = lp(rng.standard_normal(n), 2500) * env_exp(n, 0.012)
    return fade(body + 0.35 * click, 0.001, 0.05)
def click():
    n = int(0.06 * SR); return fade(hp(rng.standard_normal(n), 2000) * env_exp(n, 0.006) + 0.6 * tone(2200, 0.06, 0.01), 0.0005, 0.01)
def flap():
    n = int(0.18 * SR); return fade(bp(rng.standard_normal(n), 400, 3000) * env_exp(n, 0.035), 0.002, 0.03)
def chime(freqs, spacing=0.07, tau=0.9, dur=2.6):
    out = np.zeros(int((dur + spacing * len(freqs)) * SR))
    for i, f in enumerate(freqs):
        x = tone(f, dur, tau, ((1, 1), (2, 0.18), (3, 0.05), (4.2, 0.03)))
        out[int(i * spacing * SR): int(i * spacing * SR) + len(x)] += x
    return fade(out, 0.002, 0.3)

pops = [I["A"][0] + 0.15 + i * ((I["A"][1] - I["A"][0] - 0.3) / 5) for i in range(6)]
for i, t in enumerate(pops):
    add(sfx, ping([1175, 1319, 1397, 1175, 1568, 1319][i]), t, 0.16)
    add(sfx, buzz(), t, 0.10)
add(sfx, whoosh(0.45, 300, 120), I["dockDrop"] - 0.05, 0.22)
for k, g in [(0.364, 0.9), (0.727, 0.3), (0.909, 0.12)]: add(sfx, thud(), I["dockDrop"] + k, 0.55 * g)
add(sfx, click(), I["press"] + 0.05, 0.35)
add(sfx, whoosh(I["land"] - I["lift"], 250, 900, 0.3), I["lift"], 0.14)
add(sfx, thud(95, 0.25), I["land"], 0.28)
add(sfx, chime([523.25, 659.25, 783.99, 1046.5]), I["land"] + 0.02, 0.12)
for k in ("photo1", "photo2", "photo3"): add(sfx, flap(), I[k] + 0.12, 0.3)
add(sfx, whoosh(0.7, 200, 700), I["expand"], 0.14)
# outro
add(sfx, whoosh(0.9, 700, 200), T_OUTRO, 0.13)
for k in (0.5, 0.8, 1.1, 1.4): add(sfx, flap(), T_OUTRO + k + 0.12, 0.28)
add(sfx, whoosh(0.8, 300, 1200), T_OUTRO + 4.3, 0.14)
add(sfx, chime([392.0, 523.25, 659.25, 783.99, 1046.5], 0.09, 1.3, 3.5), T_OUTRO + 5.1, 0.1)

# ---------------- music ----------------
music_l = np.zeros(N); music_r = np.zeros(N)
if MUSIC:
    BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT
    def midi(m): return 440 * 2 ** ((m - 69) / 12)
    def pad(notes, dur, bright=1800):
        n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
        for m in notes:
            for det in (-0.12, 0.0, 0.11):
                f = midi(m + det)
                x += sum(np.sin(2 * np.pi * f * h * t + h) / h for h in range(1, 7))
        x = lp(x, bright)
        a = np.minimum(1, t / 0.9); r = np.minimum(1, (dur - t) / 0.9)
        return x * a * r / (len(notes) * 3)
    def pluck(m, dur=1.4, tau=0.35):
        f = midi(m); n = int(dur * SR); t = np.arange(n) / SR
        x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * env_exp(n, tau)
        return fade(x, 0.003, 0.05)
    tense = [([57, 60, 64], [69, 72, 76, 72]), ([53, 57, 60], [65, 69, 72, 69]), ([50, 53, 57], [62, 65, 69, 65]), ([52, 56, 59], [64, 68, 71, 68])]   # Am F Dm E
    calm = [([48, 55, 64], [72, 76, 79, 76]), ([43, 50, 59], [67, 71, 74, 71]), ([45, 52, 60], [69, 72, 76, 72]), ([41, 48, 57], [65, 69, 72, 69])]    # C G Am F
    land = I["land"]
    t = 0.3; bar = 0
    while t < TOTAL - 0.2:
        prog = tense if t < land - 0.3 else calm
        chord, arp = prog[bar % 4]
        dur = min(BAR + 0.9, TOTAL - t)
        if prog is calm and t < land + BAR and t + BAR > land:  # resolve exactly on the landing
            pass
        p = pad([c for c in chord], dur, 1500 if prog is tense else 2200)
        pan = 0.5
        add(music_l, p, t, 0.55); add(music_r, p, t, 0.55)
        for i in range(8):
            tt = t + i * BEAT / 2
            if tt >= TOTAL - 0.5: break
            if prog is calm and i % 2: continue  # calmer: quarter notes only
            m = arp[i % 4] + (12 if (prog is tense and i >= 4) else 0)
            pl = pluck(m, 1.2, 0.22 if prog is tense else 0.45)
            side = 0.35 * np.sin(i * 1.3)
            add(music_l, pl, tt, 0.16 * (1 - side)); add(music_r, pl, tt, 0.16 * (1 + side))
        # bass on beat 1 and 3
        for b in (0, 2):
            tt = t + b * BEAT
            if tt < TOTAL - 0.5:
                bs = tone(midi(chord[0] - 12), BEAT * 1.8, 0.5, ((1, 1), (2, 0.3)))
                add(music_l, fade(bs, 0.01, 0.1), tt, 0.22); add(music_r, fade(bs, 0.01, 0.1), tt, 0.22)
        t += BAR; bar += 1
        if prog is tense and t >= land - 0.3:  # jump the grid so the calm chord starts on the landing
            t = land; bar = 0
    # reverb: short synthetic hall
    ir_n = int(2.2 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.55 * SR)); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    wet_l = fftconvolve(music_l, ir)[:N]; wet_r = fftconvolve(music_r, ir[::-1][::-1] * 1.0)[:N]
    music_l = 0.75 * music_l + 0.45 * wet_l; music_r = 0.75 * music_r + 0.45 * wet_r
    peak = max(np.max(np.abs(music_l)), np.max(np.abs(music_r))) + 1e-9
    music_l /= peak; music_r /= peak
    # level automation: duck under the voice, lift in the no-voice moments, fade in/out
    w = int(0.35 * SR); cs = np.concatenate([[0], np.cumsum(active)])
    idx = np.arange(N); lo = np.clip(idx - w // 2, 0, N); hi = np.clip(idx + w // 2, 0, N)
    sm = (cs[hi] - cs[lo]) / w
    sm = np.maximum(sm, np.concatenate([np.zeros(int(0.15 * SR)), sm[:-int(0.15 * SR)]]))
    g = db(-19) * (1 - sm) + db(-29) * sm
    tt = np.arange(N) / SR
    g *= np.clip(tt / 1.2, 0, 1) * np.clip((TOTAL - tt) / 1.4, 0, 1)
    music_l *= g; music_r *= g

# ---------------- mix ----------------
v = voice * db(-4)
L = v + sfx + music_l; R = v + sfx + music_r
mix = np.stack([L, R], 1)
mix /= max(1.0, np.max(np.abs(mix)) / db(-1.0))
sf.write("soundtrack_raw.wav", mix.astype(np.float32), SR)
sf.write("voice_only.wav", np.stack([v, v], 1).astype(np.float32), SR)
print("total", round(TOTAL, 3), "s")
