# Exports per-frame screen positions of 3D anchor points (no rendering).
# Usage: python anchors.py SHOT  -> renders/SHOT/anchors.json
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
shot = sys.argv[1]
sys.argv = ['shots.py', shot, '--res', '1280x720', '--out', os.path.join(HERE, 'anchors_tmp')]  # separate LCD scratch so we never touch files a render is reading
src = open(os.path.join(HERE, 'shots.py')).read().replace("if __name__ == '__main__':", 'if False:')
exec(compile(src, 'shots.py', 'exec'))
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

S = SHOTS[shot](); linearize()
sc = bpy.context.scene; cam = sc.camera
def ob(name): return bpy.data.objects.get(name)
out = {'frames': []}
for f in range(1, S.n + 1):
    sc.frame_set(f)
    pts = {}
    def put(name, world):
        v = world_to_camera_view(sc, cam, Vector(world))
        pts[name] = [round(v.x, 5), round(1 - v.y, 5), round(v.z, 4)]
    # floor basis (for text printed on the floor)
    put('O', (0, 0, 0)); put('X', (0.1, 0, 0)); put('Y', (0, 0.1, 0))
    for n in ('dock', 'phone'):
        o = ob(n)
        if o: put(n, o.matrix_world.translation)
    for n, key in (('lcd_panel', 'lcd'), ('led_red_dome', 'led_red'), ('led_green_dome', 'led_green'), ('btn_cap', 'button'), ('ldr', 'ldr'), ('hole_cut', 'hole')):
        o = ob(n)
        if o: put(key, o.matrix_world.translation)
    d = ob('dock')
    if d:
        put('dock_top', d.matrix_world @ Vector((0, 0.004, 0.125)))
        zf = (0.062 + 0.125) / 2 + 0.002
        put('lid_face', d.matrix_world @ Vector((0, -0.0775 - 0.0035, zf)))
        put('lid_face_x', d.matrix_world @ Vector((0.1, -0.0775 - 0.0035, zf)))
    out['frames'].append(pts)
os.makedirs(os.path.join(HERE, 'renders', shot), exist_ok=True)
json.dump(out, open(os.path.join(HERE, 'renders', shot, 'anchors.json'), 'w'))
print('ANCHORS', shot, len(out['frames']))
