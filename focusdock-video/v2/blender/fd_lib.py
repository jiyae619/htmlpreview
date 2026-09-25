# FocusDock asset library for Blender 5.0 (bpy module). Real-world scale: metres.
import bpy, bmesh, math, os
from mathutils import Vector

# ---------------------------------------------------------------- colour
def lin(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(ch * 2 for ch in h)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

INK, BONE, CREAM = '#0f0f11', '#e9e1ce', '#dcd0b2'
LCD_BLUE, RED, GREEN = '#2a5cff', '#ff3b2e', '#2bff7a'

# ---------------------------------------------------------------- scene
def reset(res=(1280, 720), spp=16, fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'; cy.samples = spp
    cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.05; cy.adaptive_min_samples = 4
    cy.use_denoising = True
    for k, v in dict(denoiser='OPENIMAGEDENOISE', denoising_input_passes='RGB_ALBEDO_NORMAL', denoising_prefilter='ACCURATE').items():
        try: setattr(cy, k, v)
        except Exception: pass
    try: cy.denoising_quality = 'BALANCED'
    except Exception: pass
    cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 4
    cy.transparent_max_bounces = 8; cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = 6.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.film_transparent = False
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    for look in ('AgX - Medium High Contrast', 'Medium High Contrast'):
        try: vs.look = look; break
        except Exception: pass
    vs.exposure = 0.0
    w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
    world_bg = w.node_tree.nodes['Background']; world_bg.inputs['Color'].default_value = (*lin('#1a1917'), 1); world_bg.inputs['Strength'].default_value = 0.0
    return sc

def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj); return obj

def new_mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))

# ---------------------------------------------------------------- materials
def principled(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*lin(color), 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        key = {'transmission': 'Transmission Weight', 'ior': 'IOR', 'coat': 'Coat Weight', 'coat_rough': 'Coat Roughness',
               'sheen': 'Sheen Weight', 'sheen_rough': 'Sheen Roughness', 'spec': 'Specular IOR Level',
               'emit_strength': 'Emission Strength', 'alpha': 'Alpha', 'sss': 'Subsurface Weight'}.get(k)
        if k == 'emit':
            p.inputs['Emission Color'].default_value = (*lin(v), 1)
        elif key:
            p.inputs[key].default_value = v
    return m

def add_bump(m, scale=900.0, strength=0.12, distance=0.0004, weave=True):
    """Procedural book-cloth / paper micro texture."""
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 0.08; noise.inputs['Detail'].default_value = 6
    nt.links.new(mp.outputs['Vector'], noise.inputs['Vector'])
    h = noise.outputs['Fac']
    if weave:
        wx = nt.nodes.new('ShaderNodeTexWave'); wx.wave_type = 'BANDS'; wx.bands_direction = 'X'; wx.inputs['Scale'].default_value = 1.0
        wy = nt.nodes.new('ShaderNodeTexWave'); wy.wave_type = 'BANDS'; wy.bands_direction = 'Y'; wy.inputs['Scale'].default_value = 1.0
        for wv in (wx, wy):
            wv.inputs['Distortion'].default_value = 0.6; nt.links.new(mp.outputs['Vector'], wv.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'
        nt.links.new(wx.outputs['Fac'], mx.inputs[0]); nt.links.new(wy.outputs['Fac'], mx.inputs[1])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'; mix.inputs['Factor'].default_value = 0.35
        nt.links.new(mx.outputs[0], mix.inputs['A']); nt.links.new(noise.outputs['Fac'], mix.inputs['B'])
        h = mix.outputs['Result']
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = strength; bump.inputs['Distance'].default_value = distance
    nt.links.new(h, bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    # tiny roughness variation
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = p.inputs['Roughness'].default_value - 0.08; rr.inputs['To Max'].default_value = p.inputs['Roughness'].default_value + 0.08
    nt.links.new(noise.outputs['Fac'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], p.inputs['Roughness'])
    return m

def image_material(name, path, sequence_len=0, emit=1.0, rough=0.25, coat=0.0, base='#000000', interpolation='Linear'):
    """Emissive image (LCD panel, phone screen). sequence_len>0 -> image sequence starting at frame 1."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*lin(base), 1); p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = coat
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.interpolation = interpolation
    img = bpy.data.images.load(path)
    if sequence_len:
        img.source = 'SEQUENCE'
        tex.image_user.frame_duration = sequence_len; tex.image_user.frame_start = 1; tex.image_user.frame_offset = 0
        tex.image_user.use_auto_refresh = True; tex.image_user.use_cyclic = False
    tex.image = img
    nt.links.new(tex.outputs['Color'], p.inputs['Emission Color'])
    p.inputs['Emission Strength'].default_value = emit
    return m, tex

# ---------------------------------------------------------------- geometry helpers
def rounded_box(name, sx, sy, sz, r_plan=0.0, r_edge=0.0, seg_plan=8, seg_edge=3, mat=None, loc=(0, 0, 0)):
    """Box centred on loc; r_plan rounds the 4 vertical edges, r_edge fillets everything."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if r_plan > 0:
        bw = bm.edges.layers.float.get('bevel_weight_edge') or bm.edges.layers.float.new('bevel_weight_edge')
        for e in bm.edges:
            d = e.verts[0].co - e.verts[1].co
            e[bw] = 1.0 if abs(d.z) > 1e-6 else 0.0
    ob = new_mesh_obj(name, bm); ob.location = loc
    if r_plan > 0:
        b = ob.modifiers.new('plan', 'BEVEL'); b.width = r_plan; b.segments = seg_plan; b.limit_method = 'WEIGHT'
    if r_edge > 0:
        b = ob.modifiers.new('edge', 'BEVEL'); b.width = r_edge; b.segments = seg_edge; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(50)
    for poly in ob.data.polygons: poly.use_smooth = True
    try: ob.data.set_sharp_from_angle(angle=math.radians(35))
    except Exception: pass
    if mat: ob.data.materials.append(mat)
    return ob

def plane(name, sx, sy, mat=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x / sx + 0.5, l.vert.co.y / sy + 0.5)
    ob = new_mesh_obj(name, bm); ob.location = loc; ob.rotation_euler = rot
    if mat: ob.data.materials.append(mat)
    return ob

def cylinder(name, r, depth, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), seg=32):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    ob = new_mesh_obj(name, bm); ob.location = loc; ob.rotation_euler = rot
    for poly in ob.data.polygons: poly.use_smooth = True
    try: ob.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    if mat: ob.data.materials.append(mat)
    return ob

def sphere(name, r, mat=None, loc=(0, 0, 0), seg=32):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    ob = new_mesh_obj(name, bm); ob.location = loc
    for poly in ob.data.polygons: poly.use_smooth = True
    if mat: ob.data.materials.append(mat)
    return ob

def parent(child, par):
    child.parent = par; return child

def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.location = loc; return link(e)

# ---------------------------------------------------------------- studio
def studio(floor_color=BONE, size=12.0):
    """Seamless cyclorama: floor + curved backdrop."""
    m = principled('floor', floor_color, rough=0.85)
    add_bump(m, scale=300, strength=0.05, weave=False)
    bm = bmesh.new()
    # profile: flat floor from y=-size/2 to y=2, then a quarter curve up to a wall at y=3
    prof = [(-size / 2, 0.0), (1.6, 0.0)]
    R = 1.4
    for i in range(1, 17):
        a = i / 16 * math.pi / 2; prof.append((1.6 + math.sin(a) * R, R - math.cos(a) * R))
    prof.append((1.6 + R, 5.0))
    W = size
    rows = []
    for (y, z) in prof:
        rows.append([bm.verts.new((-W / 2, y, z)), bm.verts.new((W / 2, y, z))])
    for a, b in zip(rows[:-1], rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    ob = new_mesh_obj('cyclo', bm)
    for poly in ob.data.polygons: poly.use_smooth = True
    ob.data.materials.append(m)
    return ob, m

def area_light(name, loc, rot, size, energy, color='#ffffff', shape='RECTANGLE', size_y=None):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = lin(color); ld.shape = shape; ld.size = size
    if size_y: ld.size_y = size_y
    ob = link(bpy.data.objects.new(name, ld)); ob.location = loc; ob.rotation_euler = [math.radians(a) for a in rot]
    return ob

def point_light(name, loc, energy, color, radius=0.002):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = lin(color); ld.shadow_soft_size = radius
    ob = link(bpy.data.objects.new(name, ld)); ob.location = loc; return ob

def look_rot(cam_loc, target):
    d = (Vector(target) - Vector(cam_loc)).normalized()
    return d.to_track_quat('-Z', 'Y').to_euler()

def camera(name='cam', lens=50, fstop=2.8, focus=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.004; cd.clip_end = 60
    ob = link(bpy.data.objects.new(name, cd)); bpy.context.scene.camera = ob
    cd.dof.use_dof = fstop is not None
    if fstop: cd.dof.aperture_fstop = fstop; cd.dof.aperture_blades = 7
    return ob

# ---------------------------------------------------------------- the dock
# Real proportions measured from the photos (26 x 15.5 x 12.5 cm).
DW, DD = 0.26, 0.155          # width (x), depth (y)
BASE_H, LID_Z0, LID_Z1 = 0.068, 0.062, 0.125   # base height, lid bottom, lid top
HOLE = (0.062, 0.036)         # sensor opening on the lid (x, y)
FRONT_Y = -DD / 2             # the front face looks toward -y

def build_dock(lcd_path=None, lcd_seq=0, section=False):
    """Returns dict of parts. Group root is an empty 'dock' at the floor centre."""
    root = empty('dock')
    cloth = add_bump(principled('bookcloth', INK, rough=0.72, sheen=0.12, sheen_rough=0.35, spec=0.35), scale=1600, strength=0.18)
    cloth_top = add_bump(principled('bookcloth_top', '#10141e', rough=0.7, sheen=0.12, sheen_rough=0.35, spec=0.35), scale=1600, strength=0.18)
    cream = add_bump(principled('cream', CREAM, rough=0.62), scale=500, strength=0.06, weave=False)
    inner = principled('inner', '#0a0a0b', rough=0.9)
    parts = {'root': root}

    card = add_bump(principled('cardboard', '#e6d79a', rough=0.85), scale=400, strength=0.05, weave=False)
    def drop_face(ob, sign):
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z * sign > 0.9], context='FACES_ONLY')
        bm.to_mesh(ob.data); bm.free()
    def shell(name, w, d, z0, z1, mat, top_mat=None, open_bottom=True):
        ob = rounded_box(name, w, d, z1 - z0, r_edge=0.0012, mat=mat, loc=(0, 0, (z0 + z1) / 2))
        ob.data.materials.append(card); drop_face(ob, +1)   # open top: the lid sits over it
        sol = ob.modifiers.new('shell', 'SOLIDIFY'); sol.thickness = 0.003; sol.offset = -1; sol.material_offset = 1; sol.material_offset_rim = 1
        for poly in ob.data.polygons: poly.use_smooth = False
        parent(ob, root); return ob

    base = shell('base', DW, DD, 0.0, BASE_H, cloth)
    parts['card'] = card
    lid = rounded_box('lid', DW + 0.006, DD + 0.006, LID_Z1 - LID_Z0, r_edge=0.0015, mat=cloth, loc=(0, 0, (LID_Z0 + LID_Z1) / 2))
    lid.data.materials.append(cloth_top); lid.data.materials.append(card); lid.data.materials.append(card)
    # top face gets the navy cloth
    for poly in lid.data.polygons:
        if poly.normal.z > 0.9: poly.material_index = 1
    drop_face(lid, -1)   # open bottom
    sol = lid.modifiers.new('shell', 'SOLIDIFY'); sol.thickness = 0.003; sol.offset = -1; sol.material_offset = 2; sol.material_offset_rim = 2
    for poly in lid.data.polygons: poly.use_smooth = False
    parent(lid, root)
    # sensor opening
    cutter = rounded_box('hole_cut', HOLE[0], HOLE[1], 0.03, r_plan=0.002, loc=(0, 0.004, LID_Z1)); cutter.hide_render = True; cutter.display_type = 'WIRE'
    bo = lid.modifiers.new('hole', 'BOOLEAN'); bo.object = cutter; bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'
    parent(cutter, root)
    parts.update(base=base, lid=lid, hole_cutter=cutter)
    # cream trims: base foot, lid rim (bottom) and lid top edge
    trims = []
    trims.append(rounded_box('trim_foot', DW + 0.003, DD + 0.003, 0.004, r_edge=0.0008, mat=cream, loc=(0, 0, 0.002)))
    trims.append(rounded_box('trim_lid', DW + 0.0085, DD + 0.0085, 0.0045, r_edge=0.0009, mat=cream, loc=(0, 0, LID_Z0 + 0.0022)))
    t = 0.0035
    for (sx, sy, x, y) in [(DW + 0.0085, t, 0, -(DD + 0.006) / 2 + t / 2 - 0.0012), (DW + 0.0085, t, 0, (DD + 0.006) / 2 - t / 2 + 0.0012),
                           (t, DD + 0.006, -(DW + 0.006) / 2 + t / 2 - 0.0012, 0), (t, DD + 0.006, (DW + 0.006) / 2 - t / 2 + 0.0012, 0)]:
        trims.append(rounded_box('trim_top', sx, sy, 0.0026, r_edge=0.0006, mat=cream, loc=(x, y, LID_Z1 - 0.0009)))
    for tr in trims: parent(tr, root)
    parts['trims'] = trims
    if section:
        red = principled('section', '#ff4a2e', rough=0.6)
        cut = rounded_box('section_cut', 1.0, 0.5, 1.0, mat=red, loc=(0, 0.004 - 0.25, 0.3)); cut.hide_render = True; cut.display_type = 'WIRE'
        for ob in [base, lid] + trims:
            bo = ob.modifiers.new('section', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'MANIFOLD'
            try: bo.material_mode = 'TRANSFER'
            except Exception: pass
        parts['section_cut'] = cut

    # ---- LCD module on the front of the base (right of centre)
    fy = FRONT_Y - 0.0045
    lx, lz = 0.045, 0.036
    pcb = rounded_box('lcd_pcb', 0.076, 0.0016, 0.030, r_edge=0.0003, mat=principled('pcb', '#0f3a22', rough=0.5), loc=(lx, FRONT_Y - 0.0008, lz))
    bezel = rounded_box('lcd_bezel', 0.073, 0.0068, 0.027, r_edge=0.0006, mat=principled('bezel', '#08090b', rough=0.35, coat=0.4), loc=(lx, fy + 0.0012, lz))
    parts['lcd_center'] = (lx, fy - 0.0024, lz)
    if lcd_path:
        lcd_mat, lcd_tex = image_material('lcd', lcd_path, lcd_seq, emit=0.9, rough=0.12, coat=1.0, interpolation='Cubic')
        panel = plane('lcd_panel', 0.0645, 0.0165, lcd_mat, loc=(lx, fy - 0.0023, lz + 0.0005), rot=(math.radians(90), 0, 0))
        parts['lcd_tex'] = lcd_tex; parent(panel, root); parts['lcd_panel'] = panel
    for o in (pcb, bezel): parent(o, root)
    parts.update(lcd_pcb=pcb, lcd_bezel=bezel)

    # ---- LEDs (5 mm) left of the LCD, red above green
    leds = {}
    for name, col, z in (('red', RED, 0.046), ('green', GREEN, 0.034)):
        x = -0.010
        mat = principled(f'led_{name}', col, rough=0.18, transmission=0.6, ior=1.5, emit=col, emit_strength=0.0)
        m2 = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']; m2.default_value = (*[c * 0.55 for c in lin(col)], 1)
        body = cylinder(f'led_{name}_body', 0.0025, 0.004, mat, loc=(x, FRONT_Y - 0.002, z), rot=(math.radians(90), 0, 0))
        dome = sphere(f'led_{name}_dome', 0.0025, mat, loc=(x, FRONT_Y - 0.004, z))
        ring = cylinder(f'led_{name}_ring', 0.0029, 0.0008, principled('led_rim', col, rough=0.3, transmission=0.4), loc=(x, FRONT_Y - 0.0004, z), rot=(math.radians(90), 0, 0))
        light = point_light(f'led_{name}_light', (x, FRONT_Y - 0.012, z), 0.0, col, radius=0.003)
        for o in (body, dome, ring, light): parent(o, root)
        leds[name] = dict(mat=mat, light=light, dome=dome)
    parts['leds'] = leds

    # ---- side button on a white mini breadboard (right side, +x)
    sx = DW / 2
    bb_mat = add_bump(principled('breadboard', '#f3f1ea', rough=0.55), scale=400, strength=0.04, weave=False)
    bb = rounded_box('breadboard', 0.009, 0.047, 0.036, r_edge=0.0012, mat=bb_mat, loc=(sx + 0.0045, -0.018, 0.034))
    holes_m = principled('bb_holes', '#2a2a2a', rough=0.8)
    bmh = bmesh.new()
    for iy in range(8):
        for iz in range(5):
            if 2 <= iy <= 5 and 1 <= iz <= 3: continue
            y0, z0 = -0.018 - 0.0175 + iy * 0.005, 0.034 - 0.012 + iz * 0.006
            vs = [bmh.verts.new((sx + 0.0091, y0 + dy, z0 + dz)) for dy, dz in ((-0.0006, -0.0006), (0.0006, -0.0006), (0.0006, 0.0006), (-0.0006, 0.0006))]
            bmh.faces.new(vs)
    hol = new_mesh_obj('bb_holes', bmh); hol.data.materials.append(holes_m); parent(hol, root)
    btn_base = rounded_box('btn_base', 0.0035, 0.012, 0.012, r_edge=0.0006, mat=principled('btn_base', '#1b1b1c', rough=0.5), loc=(sx + 0.0107, -0.018, 0.034))
    btn = cylinder('btn_cap', 0.0034, 0.004, principled('btn_cap', '#0d0d0e', rough=0.4, coat=0.3), loc=(sx + 0.0142, -0.018, 0.034), rot=(0, math.radians(90), 0))
    for o in (bb, btn_base, btn): parent(o, root)
    parts.update(button=btn, breadboard=bb)

    # ---- USB cable out of the back right
    cab = bpy.data.curves.new('usb', 'CURVE'); cab.dimensions = '3D'; cab.bevel_depth = 0.0022; cab.bevel_resolution = 4
    sp = cab.splines.new('BEZIER'); pts = [(DW / 2 - 0.02, DD / 2 + 0.001, 0.012), (DW / 2 + 0.03, DD / 2 + 0.05, 0.003), (DW / 2 + 0.02, DD / 2 + 0.35, 0.0024)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cable = link(bpy.data.objects.new('usb_cable', cab)); cable.data.materials.append(principled('usb', '#6fb3e8', rough=0.25, transmission=0.35, coat=0.6))
    parent(cable, root)

    # ---- internals (visible in the cutaway)
    ints = []
    ard = rounded_box('arduino', 0.0686, 0.0534, 0.0016, r_edge=0.0004, mat=principled('ard_pcb', '#0e6b8f', rough=0.45), loc=(0.06, 0.02, 0.012))
    chip = rounded_box('chip', 0.035, 0.008, 0.004, mat=principled('chip', '#111', rough=0.4), loc=(0.065, 0.02, 0.0148))
    usbb = rounded_box('usb_b', 0.016, 0.012, 0.011, mat=principled('steel', '#b8bcc2', rough=0.28, metal=1.0), loc=(0.092, 0.035, 0.018))
    bread = rounded_box('breadboard_in', 0.082, 0.055, 0.0085, r_edge=0.001, mat=bb_mat, loc=(-0.055, 0.01, 0.009))
    ldr_mat = principled('ldr', '#c9772e', rough=0.35, emit='#ffc36b', emit_strength=0.0)
    ldr = cylinder('ldr', 0.0025, 0.002, ldr_mat, loc=(0, 0.004, LID_Z1 - 0.011))
    ldr_track = cylinder('ldr_track', 0.0018, 0.0022, principled('ldr_track', '#7a2d10', rough=0.4), loc=(0, 0.004, LID_Z1 - 0.0108))
    ints += [ard, chip, usbb, bread, ldr, ldr_track]
    wire_cols = ['#ff4d4d', '#3a7bff', '#ffd23a', '#2ecc71', '#ff8a3a', '#f5f5f5', '#9b59b6']
    import random; rnd = random.Random(3)
    ends = [((0.0, 0.004, LID_Z1 - 0.012), (-0.05, 0.0, 0.014)), ((0.0, 0.004, LID_Z1 - 0.012), (-0.06, 0.02, 0.014)),
            ((-0.03, 0.02, 0.014), (0.04, 0.0, 0.014)), ((-0.07, 0.0, 0.014), (-0.01, FRONT_Y + 0.006, 0.04)),
            ((0.03, 0.0, 0.014), (0.045, FRONT_Y + 0.006, 0.036)), ((0.08, 0.0, 0.014), (DW / 2 - 0.004, -0.018, 0.034)),
            ((-0.04, -0.02, 0.014), (0.05, FRONT_Y + 0.006, 0.03))]
    for i, (a, b) in enumerate(ends):
        cu = bpy.data.curves.new(f'wire{i}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0009; cu.bevel_resolution = 3
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
        mid = ((a[0] + b[0]) / 2 + rnd.uniform(-0.02, 0.02), (a[1] + b[1]) / 2 + rnd.uniform(-0.015, 0.015), min(0.09, (a[2] + b[2]) / 2 + rnd.uniform(0.0, 0.02)))
        for bp, p in zip(sp.bezier_points, (a, mid, b)):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        wo = link(bpy.data.objects.new(f'wire{i}', cu)); wo.data.materials.append(principled(f'wire{i}', wire_cols[i % len(wire_cols)], rough=0.4)); ints.append(wo)
    for o in ints: parent(o, root)
    parts['internals'] = ints; parts['ldr_mat'] = ldr_mat; parts['ldr'] = ldr
    parts['materials'] = dict(cloth=cloth, cloth_top=cloth_top, cream=cream)
    return parts

def set_led(parts, red=0.0, green=0.0):
    for name, v in (('red', red), ('green', green)):
        L = parts['leds'][name]
        L['mat'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 3.5 * v
        L['light'].data.energy = 0.14 * v

def key_led(parts, frame, red, green):
    set_led(parts, red, green)
    for name in ('red', 'green'):
        L = parts['leds'][name]
        L['mat'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].keyframe_insert('default_value', frame=frame)
        L['light'].data.keyframe_insert('energy', frame=frame)

# ---------------------------------------------------------------- the phone
PW, PL, PT = 0.0715, 0.147, 0.0079

def build_phone(screen_path=None, screen_seq=0):
    root = empty('phone')
    frame_m = principled('titanium', '#8e9094', rough=0.32, metal=1.0)
    back_m = principled('back_glass', '#2a2d33', rough=0.38, coat=1.0, coat_rough=0.05)
    body = rounded_box('phone_body', PW, PL, PT, r_plan=0.0095, r_edge=0.0022, seg_plan=10, mat=frame_m)
    back = rounded_box('phone_back', PW - 0.0016, PL - 0.0016, 0.0006, r_plan=0.0088, seg_plan=10, mat=back_m, loc=(0, 0, -PT / 2 - 0.0001))
    parent(body, root); parent(back, root)
    # camera plateau on the back (-z side)
    plat = rounded_box('cam_plateau', 0.032, 0.032, 0.0018, r_plan=0.007, r_edge=0.0006, mat=principled('plateau', '#30343b', rough=0.3, coat=1.0), loc=(-PW / 2 + 0.021, PL / 2 - 0.021, -PT / 2 - 0.0012))
    parent(plat, root)
    lens_m = principled('lens', '#050507', rough=0.05, coat=1.0, metal=0.2)
    ring_m = principled('lens_ring', '#a7aab0', rough=0.25, metal=1.0)
    for dx, dy in ((-0.0075, 0.0075), (0.0075, 0.0075), (-0.0075, -0.0075)):
        c = (plat.location.x + dx, plat.location.y + dy, -PT / 2 - 0.0026)
        parent(cylinder('lens_ring', 0.0058, 0.0022, ring_m, loc=c), root)
        parent(cylinder('lens', 0.0046, 0.0024, lens_m, loc=(c[0], c[1], c[2] - 0.0002)), root)
    parts = {'root': root, 'body': body}
    if screen_path:
        m, tex = image_material('screen', screen_path, screen_seq, emit=1.6, rough=0.08, coat=1.0)
        scr = rounded_box('screen', PW - 0.0035, PL - 0.0035, 0.0004, r_plan=0.0085, seg_plan=10, mat=m, loc=(0, 0, PT / 2 + 0.0001))
        # UVs for the screen: project top view
        me = scr.data
        if not me.uv_layers: me.uv_layers.new(name='UVMap')
        uvl = me.uv_layers.active.data
        for poly in me.polygons:
            for li in poly.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                uvl[li].uv = (v.x / (PW - 0.0035) + 0.5, v.y / (PL - 0.0035) + 0.5)
        parent(scr, root); parts['screen'] = scr; parts['screen_tex'] = tex; parts['screen_mat'] = m
    return parts

# ---------------------------------------------------------------- compositor bloom (Blender 5.0 node-group compositor)
def bloom(strength=0.6, threshold=1.2, size=0.55):
    sc = bpy.context.scene
    ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    rl = ng.nodes.new('CompositorNodeRLayers')
    gl = ng.nodes.new('CompositorNodeGlare')
    try: gl.inputs['Type'].default_value = 'Bloom'
    except Exception as e: print('glare type', e)
    for k, v in (('Threshold', threshold), ('Strength', strength), ('Size', size), ('Quality', 'High')):
        try: gl.inputs[k].default_value = v
        except Exception as e: print('glare', k, e)
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    out = ng.nodes.new('NodeGroupOutput')
    ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
    ng.links.new(gl.outputs['Image'], out.inputs[0])
    return gl
