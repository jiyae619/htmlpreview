# FocusDock v2: "Noise → Signal"

A 55-second launch film for FocusDock, built from the original project:
- **Voice:** your script, re-voiced.
- **Footage:** your real demo footage.
- **Design:** the real device's own design language.

**Output:** `FocusDock_v2.mp4` (1920×1080, 30 fps, H.264 + AAC, −15 LUFS)

## Concept

The film cuts between two states of the same desk:

| | Phone **up** | Phone **down** |
|---|---|---|
| Light | Dark room, lit only by the screen | Soft daylight studio |
| Motion | Glass notification tiles storm around the phone | Slow, precise camera moves |
| Sound | Notification pings and phone buzz become the beat | Calm groove built from the device's own clicks and ticks |
| Device | Red LED, `PHONE AWAY` | Green LED, `PHONE ON 00:00` counting |

**Typography:** all on-screen text is the LCD's own HD44780 5×7 dot-matrix font, and every caption follows the 16-column × 2-line limit of the real display. Captions show up in four ways:
- **Floor:** printed on the floor, rotating with the camera.
- **Behind the product:** set behind the dock, using the render's object matte.
- **LCD strip:** typed word by word on a floating 16×2 LCD that changes backlight colour on "red light" and "green".
- **End card:** the device's own LCD.

**Palette:** only the object's colours: ink black, cream trim, LCD blue, signal red, focus green.

**References:** Nothing's Ndot dot-matrix type, Teenage Engineering product films and manuals, Apple macro product shots, Braun/Dieter Rams cream-and-black.

## Structure (cuts sit on a 100 BPM grid)

| Time | Shot | Voice |
|---|---|---|
| 0:00 | Cold open, 3D macro: `PHONE AWAY`, then the phone slams down and the LED turns green | none |
| 0:02 | Top-down storm of glass notifications (3D) | "Do you find yourself procrastinating…" |
| 0:09 | The dock slams down and blasts the storm away; the phone flips onto it; lights on | "I built FocusDock…" |
| 0:14 | Hero turntable with a giant `PHONE-DOWN TIME` behind the dock | "It's a smart box…" |
| 0:16 | Macro anatomy: LCD, LEDs, button, sensor opening, cutaway with photoresistor and light beam | "Here we've got an LCD display…", "At the top…", "Inside the hole…" |
| 0:30 | Real footage: session on, phone placed → green, timer push-in, phone lifted → red | "I just hit this button…", "When I try to focus…", "During focus mode…" |
| 0:43 | Crane shot and push into the LCD (3D) | "FocusDock will keep you accountable…" |
| 0:48 | The LCD becomes the end card | "Now, let's focus." |

## Pipeline

| Step | Files |
|---|---|
| Voice | `vo_script.json` → Kokoro TTS (`af_heart`); word timestamps from a speech recogniser |
| Timeline | `film.py` → `film.json`: shots, voice placement, caption pages aligned per word, key events |
| 3D | `blender/` (Blender 5.0, Cycles): `fd_lib.py` models the dock from photo measurements and the phone; `shots.py` animates each shot frame by frame; `anchors.py` exports screen positions of parts for the typography |
| Compositing | `comp/` (canvas, headless Chromium): plates, dot-matrix type, mattes, transitions, grade and grain |
| Sound | `audio_v2.py`: procedural score and foley, voice ducking, loudness normalisation |
| Assembly | `assemble_v2.sh` |

## Vertical cut (9:16, for Twitter/X mobile)

**Output:** `FocusDock_v2_vertical.mp4` (1080×1920, 30 fps, same voice, score and timing as the 16:9 film)

It is re-framed, not cropped:
- **3D:** every shot is re-rendered with a portrait camera (`blender/shots_v.py`, `blender/anchors_v.py`, `blender/queue_v.sh`), so the product fills the tall frame at full resolution.
- **Real footage:** shown 1:1 at native resolution in a square window over a blurred fill of the same clip. Under the window, a dot-matrix status line mirrors the device (`FOCUS OFF` → `PHONE AWAY` → `PHONE ON` → `PHONE AWAY`).
- **Type:** captions re-flow for the narrow frame. Long words stack (`PHONE-` / `DOWN` / `TIME`), and the LCD strip sits in the top third, clear of the product and of the app's bottom UI.

Build it with `VERT=1 ./assemble_v2.sh`: this composites with `comp/render.mjs --v 1`, then muxes the result with `soundtrack.wav`.
