# FocusDock v2 VERTICAL (9:16) - same animation as shots.py, cameras re-composed for a tall frame.
# Blender sensor fit AUTO: the 36 mm sensor spans the frame HEIGHT, so horizontal span = 20.25/lens * distance.
# Usage: python shots.py SHOT [--res 1280x720] [--spp 14] [--stills 1,20,40] [--frames a-b] [--matte] [--out DIR]
import sys, os, math, json, argparse, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Euler, Quaternion
import fd_lib as L
from lcd import lcd_image, phone_line, mmss

FPS = 30
ap = argparse.ArgumentParser()
ap.add_argument('shot'); ap.add_argument('--res', default='720x1280'); ap.add_argument('--spp', type=int, default=14)
ap.add_argument('--stills', default=''); ap.add_argument('--frames', default=''); ap.add_argument('--matte', action='store_true')
ap.add_argument('--out', default=os.path.join(HERE, 'renders_v'))
A = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
RES = tuple(int(v) for v in A.res.split('x'))

# ------------------------------------------------------------------ easing
def clamp01(x): return max(0.0, min(1.0, x))
def seg(t, a, b): return clamp01((t - a) / (b - a))
def lerp(a, b, k): return a + (b - a) * k
def inout(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def outc(x): return 1 - (1 - x) ** 3
def outq(x): return 1 - (1 - x) ** 5
def inc(x): return x ** 3
def outback(x, s=1.7): return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def smooth(x): return x * x * (3 - 2 * x)
def V(*a): return Vector(a)
def lerpv(a, b, k): return Vector(a).lerp(Vector(b), k)

def keys_path(keys, t):
    """keys: [(t, value)] piecewise with inout easing between keys (value: float or tuple)."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            k = inout(seg(t, t0, t1))
            return tuple(lerp(a, b, k) for a, b in zip(v0, v1)) if isinstance(v0, tuple) else lerp(v0, v1, k)
    return keys[-1][1]

# ------------------------------------------------------------------ framework
class Shot:
    def __init__(self, name, n):
        self.name, self.n = name, n
        self.dir = os.path.join(A.out, name); os.makedirs(self.dir, exist_ok=True)
        self.animated = []
    def t(self, f): return (f - 1) / FPS

def key_obj(ob, f, loc=None, rot=None, scale=None):
    if loc is not None: ob.location = loc; ob.keyframe_insert('location', frame=f)
    if rot is not None:
        ob.rotation_mode = 'XYZ'; ob.rotation_euler = rot; ob.keyframe_insert('rotation_euler', frame=f)
    if scale is not None: ob.scale = scale; ob.keyframe_insert('scale', frame=f)

def key_val(owner, prop, f, value, index=-1):
    setattr(owner, prop, value) if index < 0 else getattr(owner, prop).__setitem__(index, value)
    owner.keyframe_insert(prop, frame=f, index=index)

def key_socket(sock, f, v):
    sock.default_value = v; sock.keyframe_insert('default_value', frame=f)

def linearize():
    for coll in (bpy.data.objects, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for idb in coll:
            ads = [idb.animation_data]
            if hasattr(idb, 'node_tree') and idb.node_tree: ads.append(idb.node_tree.animation_data)
            for ad in ads:
                if ad and ad.action:
                    try:
                        for fc in ad.action.fcurves:
                            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
                    except Exception:
                        for layer in ad.action.layers:
                            for strip in layer.strips:
                                for cb in strip.channelbags:
                                    for fc in cb.fcurves:
                                        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

def cam_key(cam, f, pos, look, focus=None, lens=None, roll=0.0):
    cam.location = pos; q = (V(*look) - V(*pos)).normalized().to_track_quat('-Z', 'Y')
    e = q.to_euler()
    if roll: e = (q @ Quaternion((0, 0, 1), math.radians(roll))).to_euler()
    cam.rotation_euler = e
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    fd = (V(*(focus or look)) - V(*pos)).length
    cam.data.dof.focus_distance = fd; cam.data.dof.keyframe_insert('focus_distance', frame=f)
    if lens: cam.data.lens = lens; cam.data.keyframe_insert('lens', frame=f)

def lcd_sequence(shot, fn):
    """fn(t) -> (line1, line2). Writes shot/lcd/0001.png... (re-uses files for identical text)."""
    d = os.path.join(shot.dir, 'lcd'); os.makedirs(d, exist_ok=True)
    cache = {}
    for f in range(1, shot.n + 1):
        l1, l2 = fn(shot.t(f)); key = l1 + '|' + l2
        p = os.path.join(d, f'{f:04d}.png')
        if key not in cache: lcd_image(l1, l2).save(p); cache[key] = p
        else:
            if os.path.exists(p): os.remove(p)
            os.link(cache[key], p)
    return os.path.join(d, '0001.png')

# ------------------------------------------------------------------ lighting rigs
def bright_rig(sc, k=1.0):
    lights = dict(
        key=L.area_light('key', (-0.55, -0.45, 0.75), (48, 0, -40), 0.9, 55 * k, '#fff4e6'),
        fill=L.area_light('fill', (0.7, -0.5, 0.3), (70, 0, 55), 1.2, 6 * k, '#e8eeff'),
        rim=L.area_light('rim', (0.25, 0.55, 0.35), (-65, 0, 160), 0.5, 45 * k, '#ffe9cc'))
    bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*L.lin(L.BONE), 1); bg.inputs['Strength'].default_value = 0.04 * k
    return lights
BRIGHT = dict(key=55, fill=6, rim=45, world=0.04)

def set_rig(lights, sc, f, k, cool_rim=0.0):
    for name, ob in lights.items():
        if name in BRIGHT: key_val(ob.data, 'energy', f, BRIGHT[name] * k)
    key_socket(sc.world.node_tree.nodes['Background'].inputs['Strength'], f, BRIGHT['world'] * k)

# ------------------------------------------------------------------ glass notification tiles
def build_tiles(n, seed=5):
    glass = L.principled('tile_glass', '#f4f7ff', rough=0.03, transmission=1.0, ior=1.45, coat=0.0)
    tex_dir = os.path.join(HERE, 'tex'); decals = []
    for i in range(6):
        m = bpy.data.materials.new(f'decal{i}'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
        tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(f'{tex_dir}/tile_{i}.png')
        nt.links.new(tx.outputs['Color'], p.inputs['Base Color']); nt.links.new(tx.outputs['Color'], p.inputs['Emission Color'])
        nt.links.new(tx.outputs['Alpha'], p.inputs['Alpha']); p.inputs['Emission Strength'].default_value = 0.9; p.inputs['Roughness'].default_value = 0.4
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
        decals.append(m)
    rnd = random.Random(seed); tiles = []
    for i in range(n):
        root = L.empty(f'tile{i}')
        g = L.rounded_box(f'tile{i}_glass', 0.066, 0.017, 0.0048, r_plan=0.0082, r_edge=0.0021, seg_plan=8, mat=glass); L.parent(g, root)
        dcl = L.plane(f'tile{i}_decal', 0.0655, 0.0169, decals[i % 6], loc=(0, 0, 0.0)); L.parent(dcl, root)
        tiles.append(dict(root=root, i=i, r=0.09 + 0.12 * rnd.random(), z=0.02 + 0.10 * rnd.random(), th0=rnd.random() * math.tau,
                          w=0.7 + 0.5 * rnd.random(), tilt=(rnd.uniform(-0.35, 0.35), rnd.uniform(-0.25, 0.25)), ph=rnd.random() * 6,
                          spin=(rnd.uniform(-9, 9), rnd.uniform(-9, 9), rnd.uniform(-12, 12)), vout=1.6 + 1.2 * rnd.random(), vup=0.5 + 0.9 * rnd.random()))
    return tiles

# ------------------------------------------------------------------ SHOTS
def shot_H1():
    """Cold open (72f, 0-2.4s): macro on LCD 'PHONE AWAY', snap back as the phone slams down, LED red->green."""
    S = Shot('H1', 72); sc = L.reset(RES, A.spp)
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    cyc, _ = L.studio(); lights = bright_rig(sc, 0.22)
    L.area_light('rimH', (0.3, 0.35, 0.35), (-55, 0, 145), 0.4, 18, '#9fb8ff')
    HIT = 0.62
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('away', 0)) if t < HIT + 0.03 else ('FOCUS ON', phone_line('on', 0 if t < HIT + 1.0 else 1)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n)
    ph = L.build_phone()
    cam = L.camera(lens=50, fstop=3.2)
    rest = L.LID_Z1 + L.PT / 2 + 0.0008
    for f in range(1, S.n + 1):
        t = S.t(f)
        # phone falls flat, face down, and lands with a 2 mm bounce
        if t < HIT: z = rest + 0.34 * (1 - seg(t, HIT - 0.2, HIT)) ** 2 + (0.5 if t < HIT - 0.2 else 0)
        else: z = rest + 0.002 * math.sin(seg(t, HIT, HIT + 0.12) * math.pi)
        tilt = 0.05 * (1 - seg(t, HIT - 0.16, HIT))
        key_obj(ph['root'], f, loc=(0.004, 0.004, z), rot=(math.pi + tilt, 0, math.pi / 2 + 0.03))
        red = 1.0 if t < HIT + 0.03 else 0.0
        green = 0.0 if t < HIT + 0.03 else (1.0 + 0.6 * (1 - seg(t, HIT + 0.03, HIT + 0.35)))
        L.key_led(dock, f, red, green)
        # camera: macro on the LCD, then snap back to reveal the top edge as the phone arrives
        k = outq(seg(t, HIT - 0.22, HIT + 0.05))
        pos = lerpv((0.036, L.FRONT_Y - 0.235, 0.046), (0.022, L.FRONT_Y - 0.52, 0.17), k)
        look = lerpv((0.036, L.FRONT_Y, 0.040), (0.022, L.FRONT_Y, 0.112), k)
        shake = 0.0025 * math.exp(-(t - HIT) * 14) * math.sin((t - HIT) * 90) if t > HIT else 0
        drift = 0.012 * seg(t, HIT, 2.4)
        pos = pos + V(0, drift, shake); look = look + V(0, 0, shake * 0.6)
        cam_key(cam, f, tuple(pos), tuple(look), focus=tuple(lerpv((0.03, L.FRONT_Y - 0.007, 0.04), (0.02, L.FRONT_Y, 0.09), k)))
    return S

def shot_N():
    """Noise -> slam -> lights on (360f, 2.4-14.4s). Top-down. local t: slam at 7.2, phone lands at 10.8."""
    S = Shot('N', 360); sc = L.reset(RES, A.spp)
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.4
    cyc, floor_m = L.studio(); lights = bright_rig(sc, 0.0)
    cool = L.area_light('cool', (0.35, 0.3, 0.7), (-30, 25, 40), 0.4, 1.0, '#a9c4ff')
    SLAM, LIFT, LAND = 7.2, 9.6, 10.8
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('away', 0)) if t < LAND else ('FOCUS ON', phone_line('on', t - LAND)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n)
    D0 = V(-0.055, -0.215, 0.0); DROT = math.radians(-6)
    ph = L.build_phone(screen_path=os.path.join(HERE, 'tex', 'phone_screen.png'))
    P0 = V(-0.075, -0.005, L.PT / 2 + 0.0002); PROT0 = math.radians(14)
    tiles = build_tiles(26)
    cam = L.camera(lens=35, fstop=9.0)
    spawn = [0.25 + i * 0.23 for i in range(len(tiles))]
    scr_bsdf = ph['screen_mat'].node_tree.nodes['Principled BSDF']
    for f in range(1, S.n + 1):
        t = S.t(f)
        # ---- dock: parked out of sight, slams down at SLAM
        if t < SLAM - 0.2: dz = 3.0
        elif t < SLAM: dz = 0.62 * (1 - seg(t, SLAM - 0.2, SLAM)) ** 1.6
        else: dz = 0.004 * math.sin(seg(t, SLAM, SLAM + 0.14) * math.pi)
        key_obj(dock['root'], f, loc=(D0.x, D0.y, dz), rot=(0, 0, DROT))
        # ---- phone: face up with notifications; lifts, flips, lands on the dock
        rest_top = V(D0.x, D0.y, L.LID_Z1 + L.PT / 2 + 0.0008)
        if t < LIFT:
            buzz = sum(math.sin(seg(t, s, s + 0.25) * math.pi * 8) * (1 - seg(t, s, s + 0.25)) for s in spawn if s <= t < s + 0.25)
            key_obj(ph['root'], f, loc=tuple(P0), rot=(0, 0, PROT0 + 0.03 * buzz))
        else:
            k = inout(seg(t, LIFT, LAND))
            p = P0.lerp(rest_top, k); p.z += 0.22 * math.sin(k * math.pi)
            if t > LAND: p.z = rest_top.z + 0.002 * math.sin(seg(t, LAND, LAND + 0.12) * math.pi)
            flip = math.pi * inout(seg(t, LIFT + 0.1, LAND - 0.05))
            yaw = lerp(PROT0, DROT + math.pi / 2, inout(seg(t, LIFT, LAND - 0.1)))
            key_obj(ph['root'], f, loc=tuple(p), rot=(0, flip, yaw))
        # screen light: flashes with every notification, dies when the phone flips
        flash = max([1 - seg(t, s, s + 0.3) for s in spawn if s <= t] + [0])
        key_socket(scr_bsdf.inputs['Emission Strength'], f, (1.5 + 2.0 * flash) * (1 - seg(t, LIFT + 0.1, LIFT + 0.5)))
        # ---- tiles: pop out of the screen, orbit in an accelerating storm, blasted away by the slam
        centre = V(P0.x, P0.y, 0.0)
        for tl, s in zip(tiles, spawn):
            if t < s:
                key_obj(tl['root'], f, loc=(P0.x, P0.y, -0.05), rot=(0, 0, 0), scale=(0.001,) * 3); continue
            age = t - s; kp = outback(seg(age, 0, 0.45), 1.4)
            omega_int = tl['w'] * (0.5 * age + 0.06 * (age ** 2))   # accelerating
            th = tl['th0'] + omega_int
            r = tl['r'] * kp; zz = 0.008 + (tl['z'] + 0.006 * math.sin(age * 2.3 + tl['ph'])) * kp
            pos = centre + V(math.cos(th) * r, math.sin(th) * r, zz)
            rot = V(tl['tilt'][0] + 0.2 * math.sin(age * 1.7 + tl['ph']), tl['tilt'][1], th + math.pi / 2)
            if t >= SLAM:  # ballistic escape from the impact point
                dt = t - SLAM; P = pos_at_slam(tl, s, SLAM, centre)
                d = (P - V(D0.x, D0.y, 0)); d.z = 0; d = d.normalized()
                pos = P + d * tl['vout'] * dt + V(0, 0, tl['vup'] * dt - 4.9 * dt * dt)
                pos.z = max(pos.z, 0.003)
                rot = rot + V(*tl['spin']) * dt
            sc_ = max(0.001, kp)
            key_obj(tl['root'], f, loc=tuple(pos), rot=tuple(rot), scale=(sc_,) * 3)
        # ---- lights on at landing
        on = smooth(seg(t, LAND, LAND + 0.55))
        set_rig(lights, sc, f, on)
        key_val(cool.data, 'energy', f, 1.0 * (1 - on) + 0.6)
        L.key_led(dock, f, 1.0 if SLAM <= t < LAND else 0.0, (1.0 + 0.6 * (1 - seg(t, LAND, LAND + 0.3))) if t >= LAND else 0.0)
        # ---- camera: top-down over the storm, widens for the slam, settles over the dock
        cx = keys_path([(0, -0.075), (6.4, -0.07), (7.05, -0.065), (LIFT, -0.065), (LAND + 0.3, D0.x), (12.0, D0.x)], t)
        cy = keys_path([(0, -0.005), (6.4, -0.005), (7.05, -0.10), (LIFT, -0.10), (LAND + 0.3, D0.y - 0.02), (12.0, D0.y - 0.035)], t)
        cz = keys_path([(0, 0.50), (6.4, 0.58), (7.05, 0.80), (LIFT, 0.78), (LAND + 0.3, 0.62), (12.0, 0.56)], t)
        spin = keys_path([(0, 0.0), (7.05, 14.0), (12.0, 20.0)], t)
        shake = 0.006 * math.exp(-(t - SLAM) * 9) * math.sin((t - SLAM) * 80) if t > SLAM else 0
        # during the storm keep the phone in the upper part of frame: floor below it carries the captions
        w_off = 1 - inout(seg(t, 6.3, 7.05)); off = 0.21 * cz * w_off; rr = math.radians(spin)
        cx += off * math.sin(rr); cy -= off * math.cos(rr)
        pos = (cx + shake, cy, cz); look = (cx + shake, cy + 0.0005, 0.0)
        cam_key(cam, f, pos, look, focus=(cx, cy, 0.02 if t < SLAM else 0.1), roll=spin)
    return S

_slam_cache = {}
def pos_at_slam(tl, s, SLAM, centre):
    key = tl['i']
    if key not in _slam_cache:
        age = SLAM - s; kp = outback(seg(age, 0, 0.45), 1.4)
        th = tl['th0'] + tl['w'] * (0.5 * age + 0.06 * age ** 2)
        _slam_cache[key] = centre + V(math.cos(th) * tl['r'] * kp, math.sin(th) * tl['r'] * kp, 0.008 + (tl['z'] + 0.006 * math.sin(age * 2.3 + tl['ph'])) * kp)
    return _slam_cache[key].copy()

def docked_phone(ph, f, yaw=math.pi / 2):
    key_obj(ph['root'], f, loc=(0.0, 0.004, L.LID_Z1 + L.PT / 2 + 0.0008), rot=(math.pi, 0, yaw))

def shot_N3():
    """Hero (72f, 14.4-16.8): low 3/4 orbit, phone docked, green, timer 00:01->00:03."""
    S = Shot('N3', 72); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('on', 1.2 + t)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); ph = L.build_phone(); cam = L.camera(lens=58, fstop=4.5)
    for f in range(1, S.n + 1):
        t = S.t(f); docked_phone(ph, f); L.key_led(dock, f, 0, 1)
        k = inout(seg(t, 0, 2.4))
        a = math.radians(lerp(-36, -22, k)); r = 1.02
        pos = (math.sin(-a) * r * 0.9, -math.cos(a) * r, lerp(0.21, 0.23, k))
        cam_key(cam, f, pos, (0.0, 0.0, 0.19), focus=(0.02, L.FRONT_Y, 0.06))
    return S

def shot_M1():
    """LCD macro slide (72f, 16.8-19.2): 'FOCUS OFF / PRESS TO START'."""
    S = Shot('M1', 72); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS OFF', 'PRESS TO START'))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); cam = L.camera(lens=50, fstop=4.0)
    for f in range(1, S.n + 1):
        t = S.t(f); L.key_led(dock, f, 0, 0); k = inout(seg(t, 0, 2.4))
        x = lerp(0.018, 0.052, k)
        cam_key(cam, f, (x, L.FRONT_Y - 0.19, 0.050), (x + 0.002, L.FRONT_Y, 0.040), focus=(x, L.FRONT_Y - 0.007, 0.037))
    return S

def shot_M2():
    """LED macro (72f, 19.2-21.6): red, then green on the downbeat."""
    S = Shot('M2', 72); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc, 0.55)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('away', 0)) if t < 1.2 else ('FOCUS ON', phone_line('on', 0)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); cam = L.camera(lens=100, fstop=5.0)
    for f in range(1, S.n + 1):
        t = S.t(f); red = 1.0 if t < 1.2 else 0.0; green = 0.0 if t < 1.2 else 1.0 + 0.5 * (1 - seg(t, 1.2, 1.45))
        L.key_led(dock, f, red, green); k = inout(seg(t, 0, 2.4))
        pos = lerpv((-0.012, L.FRONT_Y - 0.19, 0.050), (-0.008, L.FRONT_Y - 0.165, 0.046), k)
        cam_key(cam, f, tuple(pos), (-0.004, L.FRONT_Y, 0.040), focus=(-0.010, L.FRONT_Y - 0.004, 0.040))
    return S

def shot_M3():
    """Button macro + pull back (72f, 21.6-24.0): press at 0.5s, LCD turns FOCUS ON, red LED."""
    S = Shot('M3', 72); sc = L.reset(RES, A.spp); sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
    L.studio(); bright_rig(sc); PRESS = 0.5
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS OFF', 'PRESS TO START') if t < PRESS + 0.08 else ('FOCUS ON', phone_line('away', 0)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); cam = L.camera(lens=90, fstop=4.0)
    btn = dock['button']; bx = btn.location.x
    for f in range(1, S.n + 1):
        t = S.t(f)
        pr = math.sin(seg(t, PRESS - 0.06, PRESS + 0.14) * math.pi)
        key_obj(btn, f, loc=(bx - 0.0016 * pr, btn.location.y, btn.location.z))
        L.key_led(dock, f, 1.0 if t > PRESS + 0.08 else 0.0, 0)
        k = inout(seg(t, 1.0, 2.35))
        pos = lerpv((0.36, -0.03, 0.045), (0.52, -0.78, 0.30), k); look = lerpv((0.14, -0.018, 0.034), (0.01, 0.0, 0.10), k)
        lens = lerp(90, 55, k)
        cam_key(cam, f, tuple(pos), tuple(look), focus=tuple(lerpv((0.145, -0.018, 0.034), (0.03, L.FRONT_Y, 0.06), k)), lens=lens)
    return S

def shot_M5():
    """Crane over the lid to the sensor opening (72f, 24.0-26.4)."""
    S = Shot('M5', 72); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('away', 0)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); cam = L.camera(lens=50, fstop=4.0)
    for f in range(1, S.n + 1):
        t = S.t(f); L.key_led(dock, f, 1, 0)
        k = inout(seg(t, 0, 2.4))
        a = lerp(math.radians(34), math.radians(88), k); r = lerp(0.78, 0.30, k)
        pos = (0.0, 0.004 - math.cos(a) * r, L.LID_Z1 + math.sin(a) * r)
        cam_key(cam, f, pos, (0.0, 0.004, L.LID_Z1 - 0.02 * k), focus=(0, 0.004, L.LID_Z1), roll=90 * inout(seg(t, 0.6, 2.4)))
    return S

def shot_M6():
    """Cutaway (108f, 26.4-30.0): section through the opening; light pours in, the photoresistor glows."""
    S = Shot('M6', 108); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc, 0.8)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('away', 0)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n, section=True)
    for ob in bpy.data.objects:   # front-mounted parts live in the removed half
        if ob.name.split('.')[0] in ('lcd_panel', 'lcd_pcb', 'lcd_bezel', 'breadboard', 'bb_holes', 'btn_base', 'btn_cap') or ob.name.startswith('led_'):
            ob.hide_render = True
    spot = L.lin('#fff1d6')
    ld = bpy.data.lights.new('beam', 'SPOT'); ld.energy = 0; ld.spot_size = math.radians(16); ld.spot_blend = 0.4; ld.color = spot; ld.shadow_soft_size = 0.01
    beam_l = L.link(bpy.data.objects.new('beam', ld)); beam_l.location = (0, 0.004, 0.62); beam_l.rotation_euler = (0, 0, 0)
    # visible shaft: open cone with a transparent emissive gradient
    cone = bpy.data.materials.new('shaft'); cone.use_nodes = True; nt = cone.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); mix = nt.nodes.new('ShaderNodeAddShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*spot, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['From Min'].default_value = 0.0; ramp.inputs['From Max'].default_value = 1.0; ramp.inputs['To Min'].default_value = 0.0; ramp.inputs['To Max'].default_value = 1.0
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector']); nt.links.new(sep.outputs['Z'], ramp.inputs['Value'])
    strength = nt.nodes.new('ShaderNodeMath'); strength.operation = 'MULTIPLY'; strength.inputs[1].default_value = 0.0
    nt.links.new(ramp.outputs['Result'], strength.inputs[0]); nt.links.new(strength.outputs[0], em.inputs['Strength'])
    nt.links.new(tr.outputs[0], mix.inputs[0]); nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.022, radius2=0.11, depth=0.5)
    shaft = L.new_mesh_obj('shaft', bm); shaft.location = (0, 0.004, L.LID_Z1 + 0.25); shaft.data.materials.append(cone)
    ph = L.build_phone(); cam = L.camera(lens=60, fstop=5.0)
    BEAM, COVER = 2.45, 3.0
    for f in range(1, S.n + 1):
        t = S.t(f)
        cover = inout(seg(t, COVER, COVER + 0.45))
        key_obj(ph['root'], f, loc=(lerp(0.34, 0.0, cover), 0.004, L.LID_Z1 + L.PT / 2 + 0.0008 + 0.02 * (1 - cover)), rot=(math.pi, 0, math.pi / 2))
        light = smooth(seg(t, BEAM, BEAM + 0.3)) * (1 - smooth(seg(t, COVER + 0.25, COVER + 0.45)))
        key_val(ld, 'energy', f, 12.0 * light)
        key_socket(strength.inputs[1], f, 1.6 * light)
        key_socket(dock['ldr_mat'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'], f, 6.0 * light)
        k = inout(seg(t, 0, 3.6))
        pos = lerpv((0.0, -0.95, 0.24), (0.012, -0.76, 0.22), k)
        cam_key(cam, f, tuple(pos), tuple(lerpv((0.0, 0.0, 0.215), (0.0, 0.0, 0.205), k)), focus=(0, 0.004, 0.1))
    return S

def shot_O1():
    """Outro (162f, 43.8-49.2): crane from above around to the front, push into the LCD while the timer races."""
    S = Shot('O1', 162); sc = L.reset(RES, A.spp); L.studio(); bright_rig(sc)
    lcd0 = lcd_sequence(S, lambda t: ('FOCUS ON', phone_line('on', 13 + (seg(t, 0.2, 4.6) ** 2.2) * 3586)))
    dock = L.build_dock(lcd_path=lcd0, lcd_seq=S.n); ph = L.build_phone(); cam = L.camera(lens=40, fstop=5.6)
    lx, _, lz = dock['lcd_center']
    for f in range(1, S.n + 1):
        t = S.t(f); docked_phone(ph, f); L.key_led(dock, f, 0, 1)
        k1 = inout(seg(t, 0.0, 3.3)); k2 = inout(seg(t, 3.0, 5.4))
        a = math.radians(lerp(80, 10, k1)); az = math.radians(lerp(-35, 0, k1)); r = lerp(1.0, 0.66, k1)
        p1 = V(math.sin(az) * math.cos(a) * r, -math.cos(az) * math.cos(a) * r, 0.05 + math.sin(a) * r)
        l1 = V(0.0, 0.0, 0.09)
        pend = V(lx, L.FRONT_Y - 0.0068 - 0.19, lz); lend = V(lx, L.FRONT_Y, lz)
        pos = p1.lerp(pend, k2); look = l1.lerp(lend, k2)
        cam_key(cam, f, tuple(pos), tuple(look), focus=tuple(V(0.02, L.FRONT_Y, 0.06).lerp(V(lx, L.FRONT_Y - 0.007, lz), k2)), lens=lerp(40, 52, k2))
    return S

SHOTS = dict(H1=shot_H1, N=shot_N, N3=shot_N3, M1=shot_M1, M2=shot_M2, M3=shot_M3, M5=shot_M5, M6=shot_M6, O1=shot_O1)

# ------------------------------------------------------------------ render
def matte_setup(sc):
    """White silhouette of everything except the studio -> alpha matte for text-behind-object."""
    sc.render.film_transparent = True; sc.cycles.samples = 1; sc.cycles.use_denoising = False
    sc.render.image_settings.color_mode = 'RGBA'
    sc.compositing_node_group = None
    for ob in bpy.data.objects:
        if ob.name in ('cyclo', 'shaft'): ob.hide_render = True
    m = bpy.data.materials.new('matte'); m.use_nodes = True; nt = m.node_tree
    nt.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 1, 1, 1); nt.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1
    bpy.context.view_layer.material_override = m

if __name__ == '__main__':
    S = SHOTS[A.shot]()
    linearize()
    sc = bpy.context.scene
    if not A.matte: L.bloom(strength=0.55, threshold=1.0, size=0.6)
    else: matte_setup(sc)
    sc.frame_start, sc.frame_end = 1, S.n
    sub = 'matte' if A.matte else 'rgb'
    outdir = os.path.join(S.dir, sub); os.makedirs(outdir, exist_ok=True)
    if A.stills:
        for fr in [int(x) for x in A.stills.split(',')]:
            sc.frame_set(fr); sc.render.filepath = os.path.join(A.out, f'still_{A.shot}_{fr:04d}.png')
            bpy.ops.render.render(write_still=True)
    else:
        if A.frames: a, b = [int(x) for x in A.frames.split('-')]; sc.frame_start, sc.frame_end = a, b
        sc.render.filepath = os.path.join(outdir, '####')
        bpy.ops.render.render(animation=True)
    print('DONE', A.shot)
