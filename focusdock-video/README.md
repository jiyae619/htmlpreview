# FocusDock video: remake

A new cut of *HCDE 539 – FocusDock Video*:

- **New intro:** a 3D and 2D animated opening that ends on real photos.
- **Original demo:** the footage in the middle is unchanged, frame for frame.
- **New outro:** a real-photo collage followed by a 3D end card.
- **New narration:** the same script, re-voiced with clear American-English pronunciation.

**Output:** `FocusDock_remake.mp4` (1920×1080, 30 fps, H.264 + AAC, 73.9 s)

## Structure

| Time | Section | What's on screen |
|---|---|---|
| 0:00–0:19 | **Intro (new)** | A phone buzzes with notifications. The FocusDock drops in on "I built FocusDock". The title appears on "a smart box…". The Focus button is pressed, and the phone flips face-down onto the dock on "placing the phone on the box". The LED turns green and the timer starts. Real photos of the prototype drop in, and the last one grows into the first demo frame. |
| 0:19–1:05 | **Demo (original)** | Original frames 495–1869 (16.50 s–62.30 s of the source), untouched. |
| 1:05–1:14 | **Outro (new)** | The last demo frame shrinks into a collage of real photos and live clips from the demo. The collage clears to a 3D "Thank you" card while the dock's timer keeps counting. |

## Narration (same script as the original)

Only mis-hearings of the product name were corrected ("focus dog / focus talk" → **FocusDock**, "on the dog" → **on the dock**). Otherwise the wording is kept as spoken.

1. Do you find yourself procrastinating with phone when you have to focus?
2. I built FocusDock to help fix that.
3. It's a smart box that tracks your phone-down time.
4. With your focus mode, you can track your phone-down time just by placing the phone on the box.
5. Here we've got an LCD display and two LEDs for clear visual cues, and a push button on the side to control the mode.
6. At the top, there's a hole where it detects the phone.
7. Inside the hole, there is a photoresistor, which senses light and detects the phone through a bright-dark value.
8. Right now it's just chilling in focus-off mode, but when I'm ready to log in and get some work done, I just hit this button to toggle the session on.
9. During focus mode, it warns me with red light that I'm using phone.
10. When I try to focus and place the phone on the dock, the LED turns to green and the timer counts out my focus time.
11. FocusDock will keep you accountable during focus sessions.
12. Now, let's focus.

- **Voice:** Kokoro TTS, voice `af_heart` (American English, female, warm).
- **Timing:** each demo line starts within 0.3 s of the original line, so it stays in sync with the footage.

## How it's built

| File | Role |
|---|---|
| `script.json` | narration lines |
| `audio/tts_gen.py` | synthesizes each line (Kokoro ONNX) |
| `timeline.py` → `timeline.json` | places every voice line and animation beat |
| `scene/` | Three.js scene + HTML overlay, rendered frame by frame in headless Chromium (`render.mjs`) |
| `prepare_assets.sh` | pulls the boundary frames and the live clips from the original video |
| `audio/audio_mix.py` | voice + procedural music bed + light SFX; `--no-music` for voice + SFX only |
| `assemble.sh` | joins intro + original demo + outro and muxes the soundtrack |

Rebuild, from a working dir holding the models, `src/original.mp4` and `tts/`:

```bash
python3 audio/tts_gen.py af_heart          # voice lines
python3 timeline.py                        # timeline.json
./prepare_assets.sh src/original.mp4       # real-footage assets
cd scene && npm install && cd ..
CFG=$(python3 -c "import json;t=json.load(open('timeline.json'));print(json.dumps({'intro':t['intro'],'outro':t['outro']}))")
node scene/render.mjs --shot intro --dur <intro.dur> --cfg "$CFG" --out intro.mp4
node scene/render.mjs --shot outro --dur 9 --cfg "$CFG" --out outro.mp4
python3 audio/audio_mix.py && ffmpeg -i soundtrack_raw.wav -af loudnorm=I=-16:TP=-1.5 soundtrack.wav
./assemble.sh soundtrack.wav FocusDock_remake.mp4
```
