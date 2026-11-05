"""Blender scene for the photographs of No. 1 Holonomy Lane.

    Blender -b -P render/scene.py -- --shot lookup --res 1500 --samples 256 --out out/renders/lookup.png

Light is simulated, not painted: Cycles traces it bouncing off concrete and
plaster. What the camera sees is the stair hall's *universal cover* — the
building as it is actually experienced from inside. Climb four flights and you
are back on the landing where you started, so looking up the well you see that
same landing again, and again, forever.

All dimensions are in feet and match nonexistence/holonomy_lane.py exactly.
"""

import math
import sys
import argparse

import bpy
import bmesh
from mathutils import Vector

# ----------------------------------------------------------------------------- dimensions
RISER = 7.25 / 12
TREAD = 11 / 12
RISERS = 16
STOREY = RISERS * RISER            # 9'-8"
LAP = 4 * STOREY                   # 38'-8"
FW = 4.0                           # flight width
LAND = 4.0                         # landing
FL = LAND + 15 * TREAD             # 17'-9"
S = FL + FW                        # 21'-9"
C = S / 2
WALL_T = 1.0
SLAB = 0.75
PARAPET_T = 0.5
PARAPET_H = 3.0
PITCH = RISER / TREAD

DIN = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--shot", default="lookup")
    p.add_argument("--res", type=int, default=1200)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--out", default="out/renders/test.png")
    p.add_argument("--laps", type=int, default=40)
    p.add_argument("--aspect", type=float, default=0.75)
    p.add_argument("--sun_elev", type=float, default=38.0)
    p.add_argument("--sun_az", type=float, default=200.0)
    p.add_argument("--exposure", type=float, default=0.0)
    p.add_argument("--haze", type=float, default=0.010)
    return p.parse_args(argv)


# ----------------------------------------------------------------------------- materials
def material(name, color, rough=0.8, noise=0.0, noise_scale=3.0, bump=0.0, spec=0.3,
             emit=None, emit_strength=0.0, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = spec
            break
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if noise > 0 or bump > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = noise_scale
        nz.inputs["Detail"].default_value = 8.0
        nz.inputs["Roughness"].default_value = 0.62
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if noise > 0:
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].position = 0.3
            ramp.color_ramp.elements[1].position = 0.7
            lo = [max(0, c * (1 - noise)) for c in color]
            hi = [min(1, c * (1 + noise * 0.6)) for c in color]
            ramp.color_ramp.elements[0].color = (*lo, 1)
            ramp.color_ramp.elements[1].color = (*hi, 1)
            nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        if bump > 0:
            nz2 = nt.nodes.new("ShaderNodeTexNoise")
            nz2.inputs["Scale"].default_value = noise_scale * 18
            nz2.inputs["Detail"].default_value = 4.0
            nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
            b = nt.nodes.new("ShaderNodeBump")
            b.inputs["Strength"].default_value = bump
            b.inputs["Distance"].default_value = 0.02
            nt.links.new(nz2.outputs["Fac"], b.inputs["Height"])
            nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def board_concrete(name="concrete"):
    """Light board-formed concrete: faint horizontal banding plus mottling."""
    m = material(name, (0.40, 0.385, 0.36), rough=0.86, noise=0.24, noise_scale=1.4, bump=0.25, spec=0.25)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.9
    wave.inputs["Distortion"].default_value = 1.2
    wave.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.06
    src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].is_linked else None
    if src:
        nt.links.new(src, mix.inputs["A"])
    nt.links.new(wave.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return m


# ----------------------------------------------------------------------------- geometry helpers
class MeshBuilder:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def _mat(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def box(self, x0, y0, z0, x1, y1, z1, mat):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        z0, z1 = min(z0, z1), max(z0, z1)
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        v = [self.bm.verts.new(p) for p in (
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        idx = self._mat(mat)
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            face = self.bm.faces.new([v[i] for i in f])
            face.material_index = idx

    def prism_xz(self, profile, y0, y1, mat):
        """Extrude a polygon in the x-z plane between y0 and y1 (profile counter-clockwise in x-z)."""
        idx = self._mat(mat)
        a = [self.bm.verts.new((x, y0, z)) for x, z in profile]
        b = [self.bm.verts.new((x, y1, z)) for x, z in profile]
        n = len(profile)
        f = self.bm.faces.new(a[::-1] if True else a)
        f.material_index = idx
        f = self.bm.faces.new(b)
        f.material_index = idx
        for i in range(n):
            j = (i + 1) % n
            f = self.bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = idx

    def finish(self, collection, transform=None):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        collection.objects.link(ob)
        if transform:
            ob.matrix_world = transform
        return ob


def wall_with_openings(mb, axis, fixed0, fixed1, u0, u1, v0, v1, openings, mat):
    """A wall slab spanning u in [u0,u1], height v in [v0,v1], thickness between fixed0 and fixed1.
    axis 'x': u runs along x, wall thickness in y.  axis 'y': u along y, thickness in x.
    openings: (a, b, lo, hi) rectangles in (u, v) to leave open."""
    cuts = sorted({u0, u1, *[o[0] for o in openings], *[o[1] for o in openings]})
    cuts = [c for c in cuts if u0 <= c <= u1]
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        holes = sorted([(o[2], o[3]) for o in openings if o[0] < mid < o[1]])
        z = v0
        spans = []
        for lo, hi in holes:
            if lo > z:
                spans.append((z, lo))
            z = max(z, hi)
        if z < v1:
            spans.append((z, v1))
        for lo, hi in spans:
            if axis == "x":
                mb.box(a, fixed0, lo, b, fixed1, hi, mat)
            else:
                mb.box(fixed0, a, lo, fixed1, b, hi, mat)


def text_object(body, size, collection, mat, font_path=DIN, extrude=0.0):
    cu = bpy.data.curves.new(f"txt_{body}", "FONT")
    cu.body = body
    try:
        cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    except Exception:
        pass
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude
    ob = bpy.data.objects.new(f"txt_{body}", cu)
    ob.data.materials.append(mat)
    collection.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------- the stair hall
def flight_matrix(k, lap=0):
    """Flight k's local frame -> stair-hall frame (origin at the hall's south-west inner corner)."""
    from mathutils import Matrix
    ang = k * math.pi / 2
    R = Matrix.Rotation(ang, 4, "Z")
    T1 = Matrix.Translation((-C, -C, 0))
    T2 = Matrix.Translation((C, C, k * STOREY + lap * LAP))
    return T2 @ R @ T1


def build_stair_lap(col, M):
    """One lap of the stair hall: four flights, four landings, four walls."""
    from mathutils import Matrix
    for k in range(4):
        mb = MeshBuilder(f"flight{k}")
        # Monolithic concrete flight: landing, sixteen risers, sloped soffit.
        top = [(0.0, 0.0), (LAND, 0.0)]
        for i in range(15):
            x = LAND + i * TREAD
            top.append((x, (i + 1) * RISER))
            top.append((x + TREAD, (i + 1) * RISER))
        top.append((FL, STOREY))
        WAIST = 0.55
        x_soffit = LAND - (SLAB - WAIST) / PITCH
        prof = top + [(FL, STOREY - SLAB), (FL, (FL - LAND) * PITCH - WAIST), (x_soffit, -SLAB), (0.0, -SLAB)]
        prof = list(reversed(prof))
        mb.prism_xz(prof, 0.0, FW, M["concrete"])

        # Parapet on the well side, following the pitch.
        def soffit(x):
            return max(-SLAB, (x - LAND) * PITCH - WAIST)

        def nosing(x):
            return RISER + (x - LAND) * PITCH

        y0, y1 = FW - PARAPET_T, FW
        steps = 24
        par_top = [(LAND + (FL - LAND) * i / steps, nosing(LAND + (FL - LAND) * i / steps) + PARAPET_H)
                   for i in range(steps + 1)]
        par_bot = [(x, soffit(x)) for x, _ in par_top][::-1]
        pprof = par_bot[::-1]
        poly = [(x, z) for x, z in par_bot] + [(x, z) for x, z in par_top]
        # counter-clockwise in x-z: bottom left->right, then top right->left
        poly = [(x, soffit(x)) for x, _ in par_top] + [(x, z) for x, z in reversed(par_top)]
        mb.prism_xz(poly, y0, y1, M["concrete"])
        # Newel at the landing corner.
        mb.box(LAND - PARAPET_T, FW - PARAPET_T, -SLAB, LAND, FW, RISER + PARAPET_H, M["concrete"])
        # Steel handrail cap on the parapet (a thin dark line that reads from below).
        cap = [(x, z) for x, z in par_top]
        cap_poly = [(x, z - 0.0) for x, z in cap] + [(x, z + 0.09) for x, z in reversed(cap)]
        cap_poly = [(x, z) for x, z in cap] [::1]
        rail = [(x, z) for x, z in par_top] + [(x, z + 0.10) for x, z in reversed(par_top)]
        mb.prism_xz(rail[::-1], y0 - 0.06, y1 + 0.06, M["steel"])
        # Outer walls of this flight: the long wall (local y<0) and the landing's end wall (local x<0).
        win_long = [(11 - 1.25, 11 + 1.25, 4.0, 12.6)]
        if k != 0:
            win_long.append((2 - 1.25, 2 + 1.25, 0.5, 9.0))
        else:
            win_long.append((2 - 1.5, 2 + 1.5, 0.0, 6.67))     # the door to the hall
        win_rhythm = [(11 - 0.9, 11 + 0.9, j * STOREY + 4.2, j * STOREY + 8.6) for j in (1, 2, 3)]
        wall_with_openings(mb, "x", -WALL_T, 0.0, -WALL_T, FL, -SLAB, LAP - SLAB, win_long + win_rhythm, M["plaster"])
        wall_with_openings(mb, "y", -WALL_T, 0.0, 0.0, FW, -SLAB, LAP - SLAB,
                           [(0.9, 3.1, 1.5, 10.5)] if k in (1, 3) else [], M["plaster"])
        ob = mb.finish(col, M["lap"] @ flight_matrix(k))

        # Window frames, the door, the numeral, the lamp.
        F = mb  # noqa
        fr = MeshBuilder(f"frames{k}")
        for (a, b, lo, hi) in win_long + win_rhythm:
            if k == 0 and a < 2:
                continue
            t = 0.12
            fr.box(a, -0.35, lo, b, -0.22, lo + t, M["steel"])
            fr.box(a, -0.35, hi - t, b, -0.22, hi, M["steel"])
            fr.box(a, -0.35, lo, a + t, -0.22, hi, M["steel"])
            fr.box(b - t, -0.35, lo, b, -0.22, hi, M["steel"])
            fr.box(a, -0.30, lo + t, b, -0.27, hi - t, M["glass"])
        if k == 0:
            fr.box(0.5, -0.55, 0.0, 3.5, -0.42, 6.67, M["oak"])        # door leaf
            fr.box(3.05, -0.38, 3.1, 3.12, -0.20, 3.4, M["brass"])    # pull
        fr.finish(col, M["lap"] @ flight_matrix(k))

        from mathutils import Matrix as Mx
        if k not in (1, 3):
            # On the landing's end wall (local x = 0), facing +x into the landing. Landings II and IV
            # have a window there instead, so their numeral is on the long wall only.
            num = text_object(str(k + 1), 3.4, col, M["paint"])
            num.matrix_world = M["lap"] @ flight_matrix(k) @ Mx.Translation((0.012, FW / 2, 5.6)) @ \
                Mx.Rotation(math.pi / 2, 4, "Z") @ Mx.Rotation(math.pi / 2, 4, "X")
        if k in (1, 3):
            # on the landing's long wall instead, above its window, facing into the hall
            n2 = text_object(str(k + 1), 3.4, col, M["paint"])
            n2.matrix_world = M["lap"] @ flight_matrix(k) @ Mx.Translation((LAND / 2, 0.012, 11.0)) @ \
                Mx.Rotation(math.pi, 4, "Z") @ Mx.Rotation(math.pi / 2, 4, "X")
        nf = text_object(str(k + 1), 3.1, col, M["floorpaint"])
        nf.matrix_world = M["lap"] @ flight_matrix(k) @ Mx.Translation((LAND / 2, FW / 2 - 0.15, 0.006)) @ \
            Mx.Rotation(-k * math.pi / 2, 4, "Z")
        lamp = MeshBuilder(f"lamp{k}")
        lamp.box(0.0, FW / 2 - 1.2, 8.05, 0.14, FW / 2 + 1.2, 8.2, M["lamp"])
        lamp.box(0.0, FW / 2 - 1.25, 8.2, 0.22, FW / 2 + 1.25, 8.3, M["steel"])
        lamp.finish(col, M["lap"] @ flight_matrix(k))


PLASTER = [(0.86, 0.83, 0.77)]        # warm beige; the hard-light shots switch to white


def make_materials():
    M = {}
    M["concrete"] = board_concrete()
    M["plaster"] = material("plaster", PLASTER[0], rough=0.93, noise=0.04, noise_scale=0.8, bump=0.08, spec=0.2)
    M["paint"] = material("paint", (0.035, 0.035, 0.037), rough=0.55, spec=0.35)
    M["floorpaint"] = material("floorpaint", (0.05, 0.05, 0.052), rough=0.7, spec=0.2)
    M["steel"] = material("steel", (0.05, 0.048, 0.045), rough=0.42, metallic=0.85)
    M["brass"] = material("brass", (0.6, 0.45, 0.25), rough=0.3, metallic=1.0)
    M["oak"] = material("oak", (0.42, 0.28, 0.16), rough=0.55, noise=0.25, noise_scale=6, spec=0.4)
    M["lamp"] = material("lamp", (1.0, 0.85, 0.65), rough=0.5, emit=(1.0, 0.70, 0.42), emit_strength=60.0)
    g = bpy.data.materials.new("glass")
    g.use_nodes = True
    nt = g.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.02
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.08
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    M["glass"] = g
    return M


# ----------------------------------------------------------------------------- world, render
def setup_world(sun_elev=38, sun_az=200, sun_strength=6.0, sky=(0.62, 0.72, 0.85), sky_strength=1.6):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    # A soft vertical gradient: pale near the horizon, bluer overhead.
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.92, 0.90, 0.86, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (*sky, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.5
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = sky_strength

    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = sun_strength
    sun.angle = math.radians(1.2)
    sun.color = (1.0, 0.93, 0.84)
    ob = bpy.data.objects.new("sun", sun)
    bpy.context.scene.collection.objects.link(ob)
    el, az = math.radians(sun_elev), math.radians(sun_az)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def setup_render(a):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("GPU setup failed, using CPU:", e)
    sc.cycles.samples = a.samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.008
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 14
    sc.cycles.diffuse_bounces = 8
    sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.transmission_bounces = 4
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles.blur_glossy = 1.0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x = int(a.res * a.aspect) if a.aspect < 1 else a.res
    sc.render.resolution_y = a.res if a.aspect < 1 else int(a.res / a.aspect)
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "16"
    sc.render.filepath = a.out
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    sc.view_settings.exposure = 0.7


def camera(loc, look_at=None, rot=None, lens=24, shift=(0, 0), sensor=36):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.sensor_width = sensor
    cam.sensor_fit = "AUTO"
    cam.shift_x, cam.shift_y = shift
    cam.clip_start = 0.1
    cam.clip_end = 5000
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if look_at is not None:
        d = Vector(look_at) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if rot is not None:
        ob.rotation_euler = [math.radians(r) for r in rot]
    bpy.context.scene.camera = ob
    return ob


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ----------------------------------------------------------------------------- shots
def stair_scene(a, laps_below=2):
    from mathutils import Matrix
    M = make_materials()
    lap_col = bpy.data.collections.new("lap")
    M["lap"] = Matrix.Identity(4)
    build_stair_lap(lap_col, M)
    # Instance the lap up (and a little down) the shaft.
    sc = bpy.context.scene
    for n in range(-laps_below, a.laps):
        e = bpy.data.objects.new(f"lap{n}", None)
        e.instance_type = "COLLECTION"
        e.instance_collection = lap_col
        e.location = (0, 0, n * LAP)
        sc.collection.objects.link(e)


def shot_lookup(a):
    stair_scene(a, laps_below=1)
    setup_world(sun_elev=52, sun_az=160, sun_strength=7.0)
    # Standing at the corner of the Level 1 landing, leaning out over the parapet, looking straight up.
    camera((C - 0.6, C - 0.9, 3.2), rot=(180, 0, 8), lens=14, sensor=36)


def shot_landing(a):
    stair_scene(a, laps_below=3)
    setup_world(sun_elev=34, sun_az=150, sun_strength=6.0)
    # On the Level 1 landing, eye height, looking across the well.
    camera((1.4, 1.2, 5.25), look_at=(C + 3.0, C + 4.0, 7.5), lens=16)


def shot_lookup_tele(a):
    stair_scene(a, laps_below=1)
    setup_world(sun_elev=52, sun_az=160, sun_strength=7.0)
    camera((C + 0.4, C - 0.2, 2.0), rot=(180, 0, 3), lens=24, sensor=36)


def shot_up_corner(a):
    stair_scene(a, laps_below=1)
    setup_world(sun_elev=48, sun_az=165, sun_strength=8.0)
    camera((3.3, 3.5, 5.0), look_at=(C + 0.5, C + 0.5, 70), lens=16)


def shot_landing_up(a):
    stair_scene(a, laps_below=2)
    setup_world(sun_elev=40, sun_az=160, sun_strength=8.0)
    camera((1.1, 1.0, 5.3), look_at=(C + 2.5, C + 3.5, 21), lens=17)


def shot_down(a):
    stair_scene(a, laps_below=a.laps)
    setup_world(sun_elev=48, sun_az=165, sun_strength=8.0)
    camera((3.3, 3.5, 5.2), look_at=(C + 0.3, C + 0.3, -70), lens=16)


def shot_hero_a(a):
    stair_scene(a, laps_below=2)
    setup_world(sun_elev=40, sun_az=200, sun_strength=8.0)
    p = (S - 1.2, 1.1, STOREY + 5.3)
    camera(p, look_at=(2.0, S - 2.0, STOREY + 34), lens=16)


def shot_hero_b(a):
    stair_scene(a, laps_below=2)
    setup_world(sun_elev=40, sun_az=200, sun_strength=8.0)
    p = (S - 3.6, 3.7, STOREY + 4.6)
    camera(p, look_at=(C - 1.0, C + 1.0, STOREY + 60), lens=15)


def shot_landing_view(a):
    stair_scene(a, laps_below=3)
    setup_world(sun_elev=34, sun_az=200, sun_strength=8.0)
    camera((9.0, 2.1, 3 * RISER + 5.3), rot=(90, 0, 82), lens=17, shift=(0.0, -0.19))


def shot_vertigo(a):
    """Leaning over the parapet on Level 1, looking straight down the well."""
    stair_scene(a, laps_below=a.laps)
    setup_world(sun_elev=50, sun_az=200, sun_strength=8.0)
    camera((C - 0.5, C - 0.4, 6.0), rot=(0, 0, 0), lens=20)


def shot_vertigo_corner(a):
    stair_scene(a, laps_below=a.laps)
    setup_world(sun_elev=50, sun_az=200, sun_strength=8.0)
    camera((5.2, 5.0, 6.4), look_at=(C + 0.6, C + 0.8, -80), lens=17)


SHOTS = {"vertigo": shot_vertigo, "vertigo_corner": shot_vertigo_corner, "hero_a": shot_hero_a, "hero_b": shot_hero_b, "landing_view": shot_landing_view, "lookup": shot_lookup, "landing": shot_landing, "lookup_tele": shot_lookup_tele,
         "up_corner": shot_up_corner, "landing_up": shot_landing_up, "down": shot_down}




# ============================================================================= THE HALL
HALL_L = 38.5 + 1 / 48          # 38'-6 1/4"
HALL_W = 5.0
HALL_H = 9.0
TAPE_PNG = __import__("os").path.abspath("out/textures/tape.png")


def oak_floor(name="oakfloor"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.42
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.37
    br.offset_frequency = 2           # alternate rows, so the board ends stagger
    br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.004
    br.inputs["Brick Width"].default_value = 6.5
    br.inputs["Row Height"].default_value = 0.52
    br.inputs["Color1"].default_value = (0.56, 0.40, 0.25, 1)
    br.inputs["Color2"].default_value = (0.48, 0.33, 0.20, 1)
    br.inputs["Mortar"].default_value = (0.20, 0.13, 0.08, 1)
    br.inputs["Bias"].default_value = 0.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    # Grain runs along each board (x). Each board's random brick colour shifts the grain, so
    # neighbouring boards never share a figure.
    shift = nt.nodes.new("ShaderNodeVectorMath")
    shift.operation = "MULTIPLY_ADD"
    shift.inputs[1].default_value = (23.0, 17.0, 0.0)
    nt.links.new(br.outputs["Color"], shift.inputs[0])
    nt.links.new(tc.outputs["Object"], shift.inputs[2])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 15.0
    wave.inputs["Distortion"].default_value = 1.1
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 2.2
    wave.inputs["Detail Roughness"].default_value = 0.55
    nt.links.new(shift.outputs["Vector"], wave.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.22
    nt.links.new(br.outputs["Color"], mix.inputs["A"])
    nt.links.new(wave.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    grain = nt.nodes.new("ShaderNodeBump")
    grain.inputs["Strength"].default_value = 0.06
    grain.inputs["Distance"].default_value = 0.001
    nt.links.new(wave.outputs["Fac"], grain.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], grain.inputs["Normal"])
    nt.links.new(grain.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def stone_floor(name="stone", size=2.0, c1=(0.78, 0.76, 0.71), c2=(0.70, 0.68, 0.63)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Brick Width"].default_value = size
    br.inputs["Row Height"].default_value = size
    br.inputs["Color1"].default_value = (*c1, 1)
    br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (0.5, 0.48, 0.44, 1)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def tape_material():
    m = bpy.data.materials.new("tape")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.32
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(TAPE_PNG)
    tex.interpolation = "Cubic"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def tape(col, x_hook, x_case, y, width=1 / 12):
    """A tape measure blade lying on the floor, hook at x_hook, reading at x_case."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    ROW_IN, ROWS = 120, 4
    length_in = abs(x_case - x_hook) * 12
    marks = [float(i) for i in range(int(length_in) + 1)]
    if marks[-1] < length_in:
        marks.append(length_in)
    sgn = 1 if x_case > x_hook else -1
    for a_in, b_in in zip(marks, marks[1:]):
        row = int(a_in // ROW_IN)
        u0, u1 = (a_in - row * ROW_IN) / ROW_IN, (b_in - row * ROW_IN) / ROW_IN
        v0, v1 = 1 - (row + 1) / ROWS, 1 - row / ROWS
        xa, xb = x_hook + sgn * a_in / 12, x_hook + sgn * b_in / 12

        def zz(xx):
            t = abs(xx - x_hook) / max(1e-6, abs(x_case - x_hook))
            return 0.004 + 0.003 * math.sin(t * 37.0) * math.sin(t * 5.0) ** 2
        q = [bm.verts.new((xa, y + width / 2, zz(xa))), bm.verts.new((xb, y + width / 2, zz(xb))),
             bm.verts.new((xb, y - width / 2, zz(xb))), bm.verts.new((xa, y - width / 2, zz(xa)))]
        f = bm.faces.new(q)
        # Image top toward the wall, so the markings read upright from the room.
        for loop, (u, v) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            loop[uv].uv = (u, v)
    me = bpy.data.meshes.new("tape")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(tape_material())
    ob = bpy.data.objects.new("tape", me)
    col.objects.link(ob)
    # The case, its back against the wall, and the hook at the far end. The case is exactly
    # 3-1/8 in long, so the blade reads 459-1/8 where it enters, and the case says what to add.
    from mathutils import Matrix as Mx
    CL = 3.125 / 12
    yellow = material("caseyellow", (0.78, 0.52, 0.04), rough=0.40, noise=0.03, noise_scale=160, bump=0.03, spec=0.5)
    black = material("caseblack", (0.015, 0.015, 0.015), rough=0.62)
    chrome = material("chrome", (0.86, 0.86, 0.86), rough=0.16, metallic=1.0, spec=0.5)
    d = -1 if x_case > x_hook else 1
    cx = x_case + d * CL / 2
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, y, 0.125))
    case = bpy.context.active_object
    case.scale = (CL, 0.14, 0.25)
    bev = case.modifiers.new("bevel", "BEVEL")
    bev.width = 0.045
    bev.segments = 14
    case.data.materials.append(yellow)
    bpy.ops.object.shade_smooth()
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.056, depth=0.012, vertices=96,
                                            location=(cx, y + side * 0.07, 0.158), rotation=(math.pi / 2, 0, 0))
        grip = bpy.context.active_object
        gb = grip.modifiers.new("bevel", "BEVEL")
        gb.width = 0.003
        gb.segments = 4
        grip.data.materials.append(black)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_cylinder_add(radius=0.011, depth=0.016, vertices=48,
                                            location=(cx, y + side * 0.07, 0.158), rotation=(math.pi / 2, 0, 0))
        bpy.context.active_object.data.materials.append(chrome)
        bpy.ops.object.shade_smooth()
    # printed on the side facing the room
    face = Mx.Translation((cx, y + 0.0712, 0.0)) @ Mx.Rotation(math.pi, 4, "Z") @ Mx.Rotation(math.pi / 2, 4, "X")
    for body, size, z in (("INSIDE MEASURE", 0.0165, 0.081), ("ADD 3-1/8 IN", 0.029, 0.052)):
        t = text_object(body, size, col, black)
        t.matrix_world = Mx.Translation((0, 0, z)) @ face
    mb = MeshBuilder("hook")
    mb.box(x_hook - d * 0.01, y - width / 2, 0.0, x_hook + d * 0.004, y + width / 2, 0.06, M_STEEL[0])
    mb.box(x_case + d * (CL - 0.005), y - 0.06, 0.0, x_case + d * (CL + 0.01), y + 0.06, 0.03, black)
    # the blade lock, on the top at the front
    mb.box(x_case + d * (CL - 0.075), y - 0.022, 0.236, x_case + d * (CL - 0.022), y + 0.022, 0.262, black)
    mb.finish(col)

M_STEEL = []


def hall_scene(a):
    M = make_materials()
    M_STEEL.append(M["steel"])
    M["oakfloor"] = oak_floor()
    M["entry"] = stone_floor("entrystone", 2.0)
    M["gallery"] = stone_floor("gallerystone", 1.75, (0.72, 0.70, 0.66), (0.68, 0.66, 0.62))
    M["gravel"] = material("gravel", (0.62, 0.60, 0.55), rough=0.95, noise=0.3, noise_scale=40, bump=0.6)
    M["ceramic"] = material("ceramic", (0.12, 0.11, 0.10), rough=0.35)
    col = bpy.context.scene.collection
    L, W, H, T = HALL_L, HALL_W, HALL_H, 0.5
    E = L + 0.479                   # where the entrance hall begins
    mb = MeshBuilder("hall")
    # floors
    mb.box(-20, -0.5, -1, L + 0.479, W + 0.5, 0, M["oakfloor"])
    mb.box(E, -21, -1, E + 10, W + 0.5, 0, M["entry"])
    mb.box(-12, W + T, -1, 20, W + T + 7, 0, M["gallery"])
    mb.box(-12, W + T + 7, -1, 20, 40, -0.05, M["gravel"])
    # hall walls
    wall_with_openings(mb, "x", -T, 0.0, -T, E + 10.5, 0, H, [], M["plaster"])                   # south
    wall_with_openings(mb, "x", W, W + T, -T, L, 0, H,
                       [(9.5, 13.5, 0, 8.0), (20.0, 23.0, 0, 6.667)], M["plaster"])               # north
    wall_with_openings(mb, "y", -T, 0.0, 0, W, 0, H, [(0.5, 4.5, 0, 8.0)], M["plaster"])          # west end
    wall_with_openings(mb, "y", L, E, -T, W + T, 0, 12, [(0.5, 4.5, 0, 8.0)], M["plaster"])       # east end
    # ceiling with a skylight slot running the length of the hall
    sl0, sl1, sw0, sw1 = 1.5, L - 1.5, 1.85, 3.15
    mb.box(-T, -T, H, L, sw0, H + 0.4, M["plaster"])
    mb.box(-T, sw1, H, L, W + T, H + 0.4, M["plaster"])
    mb.box(-T, sw0, H, sl0, sw1, H + 0.4, M["plaster"])
    mb.box(sl1, sw0, H, L, sw1, H + 0.4, M["plaster"])
    mb.box(sl0, sw0 - 0.2, H + 0.4, sl1, sw0, H + 1.0, M["plaster"])
    mb.box(sl0, sw1, H + 0.4, sl1, sw1 + 0.2, H + 1.0, M["plaster"])
    # shadow-gap skirting: a dark reveal where walls meet the floor
    for (x0, y0, x1, y1) in ((0, 0, L, 0.02), (0, W - 0.02, 9.5, W), (13.5, W - 0.02, 20, W), (23, W - 0.02, L, W)):
        mb.box(x0, y0, 0, x1, y1, 0.04, M["paint"])
    # entrance hall: walls, a tall ceiling, light from a roof lantern
    wall_with_openings(mb, "x", W, W + T, E, E + 10, 0, 12, [], M["plaster"])
    wall_with_openings(mb, "y", E + 10, E + 10.5, -21, W + T, 0, 12, [(-10.0, -7.0, 0, 6.667)], M["plaster"])
    mb.box(E, -21, 12, E + 3, W + T, 12.4, M["plaster"])
    mb.box(E + 7, -21, 12, E + 10.5, W + T, 12.4, M["plaster"])
    mb.box(E + 3, -21, 12, E + 7, -1.5, 12.4, M["plaster"])
    mb.box(E + 3, 4.5, 12, E + 7, W + T, 12.4, M["plaster"])
    # round table and a dark vessel in the entrance hall
    tb = bpy.data.meshes.new("table")
    # gallery beyond the north opening, with its colonnade onto the court
    G0 = W + T
    wall_with_openings(mb, "x", G0 + 7, G0 + 7.75, -12, 20, 0, 10,
                       [(-10 + i * 5, -7 + i * 5, 0, 8.0) for i in range(7)], M["plaster"])
    mb.box(-12, G0, 10, 20, G0 + 7.75, 10.4, M["plaster"])
    wall_with_openings(mb, "y", -12.5, -12, G0, G0 + 7, 0, 10, [], M["plaster"])
    wall_with_openings(mb, "y", 20, 20.5, G0, G0 + 7, 0, 10, [], M["plaster"])
    # stair-hall door, closed
    mb.box(20.0, W + 0.12, 0, 23.0, W + 0.30, 6.667, M["oak"])
    mb.box(22.55, W - 0.05, 3.1, 22.62, W + 0.12, 3.45, M["brass"])
    mb.finish(col)
    TX, TY = E + 5.0, 1.5
    bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=0.12, vertices=96, location=(TX, TY, 2.4))
    t = bpy.context.active_object
    t.data.materials.append(M["oak"])
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=2.3, vertices=48, location=(TX, TY, 1.2))
    bpy.context.active_object.data.materials.append(M["oak"])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, segments=64, ring_count=32, location=(TX, TY, 2.95))
    bpy.ops.object.shade_smooth()
    v = bpy.context.active_object
    v.scale = (1, 1, 1.15)
    v.data.materials.append(M["ceramic"])
    # The inspector's tape: hook at the far end, case against the near jamb.
    tape(col, L, 0.0, 0.26)


def shot_hall(a):
    hall_scene(a)
    setup_world(sun_elev=68, sun_az=182, sun_strength=7.5)
    bpy.context.scene.view_settings.exposure = 0.45
    cam = camera((0.55, 2.5, 4.9), rot=(90, 0, -90), lens=17)
    cam.data.shift_y = -0.06


def shot_tape(a):
    hall_scene(a)
    setup_world(sun_elev=58, sun_az=168, sun_strength=7.5)
    cam = camera((1.35, 1.05, 0.42), look_at=(0.25, 0.26, 0.05), lens=70)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 1.30
    cam.data.dof.aperture_fstop = 2.4


SHOTS.update({"hall": shot_hall, "tape": shot_tape})


# ============================================================================= LIGHT AND AIR
# The first renders were lit like a showroom: soft sky everywhere, no shadow, no air. These
# shots use a hard sun, a dim sky, and a little haze inside the rooms, so light has a shape.
def haze(x0, y0, z0, x1, y1, z1, density=0.010, anisotropy=0.55, color=(1.0, 0.98, 0.95)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new("haze")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("haze", me)
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    ob.scale = (x1 - x0, y1 - y0, z1 - z0)
    m = bpy.data.materials.new("haze")
    m.use_nodes = True
    nt = m.node_tree
    out = nt.nodes.get("Material Output")
    for n in list(nt.nodes):
        if n != out:
            nt.nodes.remove(n)
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = anisotropy
    vol.inputs["Color"].default_value = (*color, 1)
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    me.materials.append(m)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def hard_light(sun_elev, sun_az, sun_strength=12.0, sky_strength=0.30, exposure=0.0,
               look="AgX - High Contrast", sun_angle=0.6):
    setup_world(sun_elev=sun_elev, sun_az=sun_az, sun_strength=sun_strength,
                sky=(0.42, 0.56, 0.82), sky_strength=sky_strength)
    bpy.data.lights["sun"].angle = math.radians(sun_angle)
    sc = bpy.context.scene
    sc.view_settings.exposure = exposure
    try:
        sc.view_settings.look = look
    except Exception:
        pass
    sc.cycles.volume_bounces = 1


def shot_well(a):
    """Vertigo, in hard light: sun through the stair windows, the shaft falling away into lit air."""
    PLASTER[0] = (0.90, 0.895, 0.88)
    stair_scene(a, laps_below=a.laps)
    hard_light(sun_elev=a.sun_elev, sun_az=a.sun_az, exposure=a.exposure)
    haze(0.02, 0.02, -LAP * a.laps - 5, S - 0.02, S - 0.02, 14, density=a.haze, color=(0.97, 0.98, 1.0))
    camera((C - 0.5, C - 0.4, 6.0), rot=(0, 0, 0), lens=20)


def shot_hall_light(a):
    PLASTER[0] = (0.90, 0.895, 0.88)
    hall_scene(a)
    hard_light(sun_elev=a.sun_elev, sun_az=a.sun_az, exposure=a.exposure)
    haze(-0.4, 0.02, 0.02, HALL_L + 12, HALL_W - 0.02, HALL_H + 0.98, density=a.haze)
    cam = camera((0.55, 2.5, 4.9), rot=(90, 0, -90), lens=17)
    cam.data.shift_y = -0.06


def shot_tape_light(a):
    PLASTER[0] = (0.90, 0.895, 0.88)
    hall_scene(a)
    hard_light(sun_elev=a.sun_elev, sun_az=a.sun_az, exposure=a.exposure)
    haze(-0.4, 0.02, 0.02, HALL_L + 12, HALL_W - 0.02, HALL_H + 0.98, density=a.haze)
    cam = camera((1.35, 1.05, 0.42), look_at=(0.25, 0.26, 0.05), lens=70)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 1.30
    cam.data.dof.aperture_fstop = 2.4


SHOTS.update({"well": shot_well, "hall_light": shot_hall_light, "tape_light": shot_tape_light})


def main():
    a = args()
    clear()
    setup_render(a)
    SHOTS[a.shot](a)
    bpy.ops.render.render(write_still=True)
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
