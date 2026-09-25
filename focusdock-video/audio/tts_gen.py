import json, sys, re, numpy as np, soundfile as sf, os
from kokoro_onnx import Kokoro
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
voice = sys.argv[1]; speed = float(sys.argv[2]) if len(sys.argv)>2 else 1.0
SPEED = {"4": 1.06, "8": 1.05}
outdir = f"tts/{voice}"; os.makedirs(outdir, exist_ok=True)
def say(t):  # spelling hints for the synthesizer only
    t = t.replace("FocusDock", "Focus Dock").replace("phone-down", "phone down").replace("bright-dark", "bright, dark")
    return t
for line in json.load(open("script.json")):
    s, sr = k.create(say(line["text"]), voice=voice, speed=SPEED.get(line["id"], speed), lang="en-us")
    s = np.asarray(s, dtype=np.float32)
    # trim silence
    thr = 0.01*np.max(np.abs(s)); nz = np.where(np.abs(s) > thr)[0]
    s = s[max(0,nz[0]-int(0.03*sr)): nz[-1]+int(0.08*sr)]
    sf.write(f"{outdir}/{line['id']}.wav", s, sr)
    print(voice, line["id"], round(len(s)/sr,2))
