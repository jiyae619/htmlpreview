# Builds timeline.json: where every voice line and animation beat lands.
import json, soundfile as sf
S = json.load(open("script.json")); dur = {l["id"]: sf.info(f"tts/af_heart/{l['id']}.wav").duration for l in S}
FPS = 30
DEMO_IN, DEMO_OUT = 495, 1869            # first / last clean demo frame (inclusive)
demo_len = (DEMO_OUT - DEMO_IN + 1) / FPS
A = 0.7; B = A + dur["A"] + 0.5; C = B + dur["B"] + 0.42; D = C + dur["C"] + 0.42
intro = {
  "A": [A, A + dur["A"]], "B": [B, B + dur["B"]], "C": [C, C + dur["C"]], "D": [D, D + dur["D"]],
  "dockDrop": B + 0.22, "dockHit": B + 0.62,          # lands on "FocusDock"
  "titleIn": C + 0.05, "titleOut": D + 0.2,
  "press": D + 0.5,                                    # "focus mode"
  "lift": D + 3.0, "land": D + 4.45,                   # "placing the phone ... on the box"
}
L = intro["land"]
intro.update({"photo1": L + 1.15, "photo2": L + 1.7, "photo3": L + 2.35, "expand": L + 3.35})
intro["dur"] = round(intro["expand"] + 0.8, 3)
# demo voice: original start times relative to the demo cut, nudged only where a line needed room
orig_rel = {"4": 16.95, "5": 24.85, "6": 28.89, "7": 36.09, "8": 44.82, "9": 48.98, "10": 56.92, "11": 60.85}
demo = {k: round(v - DEMO_IN / FPS, 3) for k, v in orig_rel.items()}
outro = {"dur": 9.0}
total = intro["dur"] + demo_len + outro["dur"]
json.dump({"fps": FPS, "demoIn": DEMO_IN, "demoOut": DEMO_OUT, "demoLen": demo_len, "intro": intro, "demo": demo, "outro": outro, "total": total, "voiceDur": dur}, open("timeline.json", "w"), indent=1)
ids = list(demo); 
for i, k in enumerate(ids):
    end = demo[k] + dur[k]; nxt = demo[ids[i + 1]] if i + 1 < len(ids) else demo_len + outro["dur"]
    print(k, round(demo[k], 2), "->", round(end, 2), "gap", round(nxt - end, 2))
print("intro", intro["dur"], "demo", round(demo_len, 3), "total", round(total, 2))
