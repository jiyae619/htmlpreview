# Master timeline for FocusDock v2: shots, voice placement, caption pages with per-word timing.
# Writes film.json (read by the compositor and the audio mixer).
import json, re, os
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, BPM = 30, 100
BEAT = 60 / BPM
words = json.load(open(f'{HERE}/vo_words.json'))

# ---- picture: every cut sits on the 100 BPM grid (0.6 s)
SHOTS = [
    # id, start, end, source
    ('H1', 0.0, 2.4, {'kind': '3d', 'shot': 'H1'}),
    ('N', 2.4, 14.4, {'kind': '3d', 'shot': 'N'}),
    ('N3', 14.4, 16.8, {'kind': '3d', 'shot': 'N3'}),
    ('M1', 16.8, 19.2, {'kind': '3d', 'shot': 'M1'}),
    ('M2', 19.2, 21.6, {'kind': '3d', 'shot': 'M2'}),
    ('M3', 21.6, 24.0, {'kind': '3d', 'shot': 'M3'}),
    ('M5', 24.0, 26.4, {'kind': '3d', 'shot': 'M5'}),
    ('M6', 26.4, 30.0, {'kind': '3d', 'shot': 'M6'}),
    # real footage: source frame ranges in the original 30 fps video
    ('R1a', 30.0, 31.2, {'kind': 'real', 'src': [1091, 1127]}),            # hand on the button (press @ src 37.3)
    ('R1b', 31.2, 33.6, {'kind': 'real', 'src': [1265, 1337]}),            # FOCUS OFF -> cut -> FOCUS ON, red
    ('R2', 33.6, 37.8, {'kind': 'real', 'src': [1357, 1483]}),             # phone placed -> green @ src 1423
    ('R3', 37.8, 40.2, {'kind': 'real', 'src': [1483, 1764], 'timelapse': True}),
    ('R4', 40.2, 43.8, {'kind': 'real', 'src': [1764, 1869], 'hold': True}),  # phone lifted -> red @ src 1832
    ('O1', 43.8, 48.9, {'kind': '3d', 'shot': 'O1'}),
    ('END', 48.9, 55.2, {'kind': '2d'}),
]
TOTAL = 55.2

# ---- voice: start times chosen so key words land on picture events
VO = {'q': 2.7, 'built': 9.75, 'smart': 13.9, 'parts': 16.75, 'hole': 24.2, 'ldr': 26.7,
      'button': 30.2, 'place': 33.7, 'warn': 40.4, 'acct': 44.8, 'go': 49.0}

def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())

def word_times(vo_id, cap_words):
    """Align caption words (may split/merge ASR tokens) to ASR word starts via a char-level match."""
    asr = words[vo_id]['words']; t0 = VO[vo_id]; dur = words[vo_id]['dur']
    chars, ctimes = [], []
    for i, (w, t) in enumerate(asr):
        n = norm(w).replace('doc', 'dock') if norm(w) == 'doc' else norm(w)
        nxt = asr[i + 1][1] if i + 1 < len(asr) else dur
        for j, ch in enumerate(n):
            chars.append(ch); ctimes.append(t + (nxt - t) * j / max(1, len(n)) * 0.8)
    a = ''.join(chars)
    capn = [norm(w) for w in cap_words]; b = ''.join(capn)
    sm = SequenceMatcher(None, b, a, autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): m[blk.a + k] = blk.b + k
    out, pos = [], 0
    for w in capn:
        idx = next((m[p] for p in range(pos, pos + max(1, len(w))) if p in m), None)
        out.append(round(t0 + (ctimes[idx] if idx is not None else (out[-1] - t0 + 0.2 if out else 0)), 3))
        pos += len(w)
    return out

# ---- captions: pages of <=16 columns x 2 rows (the device's own 16x2 LCD)
# mode: 'floor' (embedded in the top-down floor), 'giant' (behind the product), 'lcd' (floating 16x2 LCD strip), 'device' (on the 3D LCD)
CAPS = [
    ('q', 'floor', [['DO YOU FIND', 'YOURSELF'], ['PROCRASTINATING'], ['WITH PHONE', 'WHEN YOU HAVE'], ['TO FOCUS?']]),
    ('built', 'giant_dark', [['I BUILT'], ['FOCUSDOCK'], ['TO HELP', 'FIX THAT.']]),
    ('smart', 'giant', [["IT'S A SMART BOX", 'THAT TRACKS YOUR'], ['PHONE-DOWN', 'TIME']]),
    ('parts', 'lcd', [["HERE WE'VE GOT", 'AN LCD DISPLAY'], ['AND TWO LEDS', 'FOR CLEAR'], ['VISUAL CUES,'], ['AND A PUSH', 'BUTTON ON'], ['THE SIDE TO', 'CONTROL THE MODE']]),
    ('hole', 'lcd', [["AT THE TOP,", "THERE'S A HOLE"], ['WHERE IT DETECTS', 'THE PHONE.']]),
    ('ldr', 'lcd', [['INSIDE THE HOLE,', 'THERE IS A'], ['PHOTORESISTOR,'], ['WHICH SENSES', 'LIGHT.']]),
    ('button', 'lcd', [['I JUST HIT', 'THIS BUTTON'], ['TO TOGGLE THE', 'SESSION ON.']]),
    ('place', 'lcd', [['WHEN I TRY TO', 'FOCUS AND PLACE'], ['THE PHONE ON', 'THE DOCK,'], ['THE LED TURNS', 'TO GREEN'], ['AND THE TIMER', 'COUNTS OUT MY'], ['FOCUS TIME.']]),
    ('warn', 'lcd', [['DURING', 'FOCUS MODE,'], ['IT WARNS ME WITH', 'RED LIGHT'], ["THAT I'M", 'USING PHONE.']]),
    ('acct', 'giant', [['FOCUSDOCK WILL', 'KEEP YOU'], ['ACCOUNTABLE'], ['DURING FOCUS', 'SESSIONS.']]),
    ('go', 'device', [["NOW, LET'S", 'FOCUS.']]),
]
# per-page accents: backlight / dot colour changes that mirror the device's states
ACCENT = {('place', 2): 'green', ('warn', 1): 'red', ('button', 1): 'on', ('smart', 1): 'green', ('q', 1): 'noise',
          ('built', 1): 'title', ('acct', 1): 'green'}

captions = []
for vo_id, mode, pages in CAPS:
    flat = [w for pg in pages for line in pg for w in line.replace('-', ' - ').split() if w != '-']
    tw = word_times(vo_id, flat)
    k = 0; plist = []
    for pi, pg in enumerate(pages):
        lines = []
        for line in pg:
            toks = []
            for w in line.split():
                parts = w.split('-')
                t = tw[k]; toks.append({'w': w, 't': t}); k += len(parts)
            lines.append(toks)
        plist.append({'lines': lines, 'accent': ACCENT.get((vo_id, pi))})
    for pg in plist: pg['t0'] = round(pg['lines'][0][0]['t'] - 0.04, 3)
    for pi, pg in enumerate(plist):
        pg['t1'] = plist[pi + 1]['t0'] if pi + 1 < len(plist) else round(VO[vo_id] + words[vo_id]['dur'] + 0.45, 3)
    captions.append({'vo': vo_id, 'mode': mode, 'pages': plist})

film = {'fps': FPS, 'bpm': BPM, 'total': TOTAL, 'frames': round(TOTAL * FPS), 'shots': [
            {'id': s, 'start': a, 'end': b, **src} for s, a, b, src in SHOTS],
        'vo': [{'id': k, 'start': v, 'dur': words[k]['dur']} for k, v in VO.items()],
        'captions': captions,
        'events': {'slam': 9.6, 'land': 13.2, 'press3d': 22.1, 'beam': 28.85, 'cover': 29.4, 'press_real': 30.92,
                   'focus_on_real': 32.0, 'green_real': 35.8, 'red_real': 42.48, 'hit_cold': 0.62}}
film['endLcdRect'] = {'x': 91.5, 'y': 306.0, 'w': 1762.5, 'h': 429.0}   # blue LCD area in the last outro frame (measured)
film['endLcdRectV'] = {'x': 90.0, 'y': 843.0, 'w': 912.0, 'h': 235.5}   # same, vertical cut (measure_lcd.py)
json.dump(film, open(f'{HERE}/film.json', 'w'), indent=1)
for c in captions:
    print(c['vo'], c['mode'], ' | '.join(f"{p['t0']:.2f}-{p['t1']:.2f} " + ' / '.join(' '.join(t['w'] for t in l) for l in p['lines']) for p in c['pages']))
# sanity: no VO overlaps
vs = sorted((v, v + words[k]['dur'], k) for k, v in VO.items())
for (a0, a1, ka), (b0, b1, kb) in zip(vs, vs[1:]):
    assert a1 <= b0 + 1e-6, f'VO overlap {ka}->{kb}'
print('ok, VO ends', round(max(e for _, e, _ in vs), 2), 'film', TOTAL)
