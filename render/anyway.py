"""Render the house, built anyway, as information for an ink drawing.

    Blender -b -P render/anyway.py -- --res 1600 --out out/anyway/test

Nothing here is a picture. Each pass is an exact, noiseless map of one fact about the visible
surface, written as a 16-bit greyscale PNG:

    nx, ny, nz   which way the surface faces
    plane        the plane it lies in (n . p)
    wx, wy, wz   where it is (wz is height within its level)
    depth        how far it is from the eye
    light        whether the sun reaches it
    id           what it is: building, furniture, the stone, the figure

drawings/anyway_ink.py turns them into lines, hatching and stipple.
"""

import argparse
import json
import math
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

XY = (-80.0, 140.0)          # range of the wx and wy passes, feet
IDS = {"building": 0.25, "furniture": 0.5, "stone": 0.75, "figure": 1.0}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--res", type=int, default=1600)
    p.add_argument("--aspect", type=float, default=0.75)
    p.add_argument("--out", default="out/anyway/test")
    p.add_argument("--elev", type=float, default=32.0)
    p.add_argument("--azim", type=float, default=215.0)
    p.add_argument("--lo", type=int, default=-4)
    p.add_argument("--hi", type=int, default=3)
    p.add_argument("--scale", type=float, default=330.0)
    p.add_argument("--cz", type=float, default=0.0, help="height the camera aims at, in laps")
    p.add_argument("--lens", type=float, default=0.0, help="0 = orthographic; otherwise a perspective lens in mm")
    p.add_argument("--cam", type=float, nargs=3, default=None, help="camera position, feet (perspective)")
    p.add_argument("--look", type=float, nargs=3, default=None, help="point the camera looks at, feet")
    p.add_argument("--roll", type=float, default=0.0)
    p.add_argument("--shift", type=float, nargs=2, default=(0.0, 0.0))
    p.add_argument("--sun", type=float, nargs=2, default=(250.0, 48.0), help="sun azimuth and elevation, degrees")
    p.add_argument("--cut", type=int, default=1, help="cut the top level open like a plan")
    p.add_argument("--ss", type=int, default=2, help="supersampling: render this many times larger")
    p.add_argument("--figure", type=float, nargs=2, default=(-6.5, -0.6),
                   help="where the figure stands, feet from the stone (top level only)")
    p.add_argument("--passes", default="nx,ny,nz,plane,wx,wy,wz,depth,id,light")
    p.add_argument("--border", type=float, nargs=4, default=None,
                   help="render only this part of the frame: x0 x1 y0 y1, 0..1 from the bottom left")
    return p.parse_args(argv)


DEPTH = [0.0, 1.0]
INVERSE = [False]
LAPLEN = [38.666666666666664]


def emission_material(name, kind, value=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    if kind == "id":
        em.inputs["Color"].default_value = (value, value, value, 1)
        return m

    def mapped(socket, lo, hi):
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        mr.inputs["To Min"].default_value = 0.02
        mr.inputs["To Max"].default_value = 1.0
        nt.links.new(socket, mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], em.inputs["Color"])

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    if kind == "plane":
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(geo.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["Position"], dot.inputs[1])
        mapped(dot.outputs["Value"], -1500.0, 1500.0)
    elif kind in ("nx", "ny", "nz"):
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        mapped(sep.outputs[kind[1].upper()], -1.0, 1.0)
    elif kind in ("wx", "wy"):
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        mapped(sep.outputs[kind[1].upper()], *XY)
    elif kind == "wz":
        # height within the level: (z + 5) mod LAP, so the floor sits at 5 and nothing wraps on it
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.inputs[1].default_value = 5.0 + 100 * LAPLEN[0]
        nt.links.new(sep.outputs["Z"], add.inputs[0])
        mod = nt.nodes.new("ShaderNodeMath")
        mod.operation = "MODULO"
        mod.inputs[1].default_value = LAPLEN[0]
        nt.links.new(add.outputs["Value"], mod.inputs[0])
        mapped(mod.outputs["Value"], 0.0, LAPLEN[0])
    else:  # depth
        cam = nt.nodes.new("ShaderNodeCameraData")
        if INVERSE[0]:
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "DIVIDE"
            inv.inputs[0].default_value = 1.0
            nt.links.new(cam.outputs["View Z Depth"], inv.inputs[1])
            mapped(inv.outputs["Value"], 1.0 / DEPTH[1], 1.0 / DEPTH[0])
        else:
            mapped(cam.outputs["View Z Depth"], DEPTH[0], DEPTH[1])
    return m


def mesh_from(data, name):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in data["verts"]], [], [tuple(f) for f in data["faces"]])
    me.validate()
    me.update()
    return me


def stone_mesh(seed=7):
    """The court's single stone: a low boulder, the same in every copy, because it is the pivot."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    rnd = random.Random(seed)
    bumps = [(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))).normalized(),
              rnd.uniform(0.05, 0.16)) for _ in range(9)]
    for v in bm.verts:
        d = v.co.normalized()
        r = 1.0 + sum(a * max(0.0, d.dot(b)) ** 3 for b, a in bumps)
        v.co = Vector((d.x * 3.1 * r, d.y * 2.4 * r, max(-0.2, d.z) * 1.7 * r))
    me = bpy.data.meshes.new("stone")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me


def sphere_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    me = bpy.data.meshes.new("sphere")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me


def figure_mesh():
    """A man in an overcoat and a bowler hat, six feet tall, facing +y. Feet at the origin."""
    bm = bmesh.new()

    def cone(r1, r2, z0, z1, x=0.0, y=0.0, sy=1.0, seg=32):
        m = Matrix.Translation((x, y, (z0 + z1) / 2)) @ Matrix.Diagonal((1.0, sy, 1.0, 1.0))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=z1 - z0, matrix=m)

    def ball(r, x, y, z, sx=1.0, sy=1.0, sz=1.0):
        m = Matrix.Translation((x, y, z)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r, matrix=m)

    for s in (-1, 1):
        cone(0.2, 0.17, 0.08, 1.9, x=0.25 * s)                        # trouser legs
        ball(0.18, 0.25 * s, 0.14, 0.1, sx=1.0, sy=2.0, sz=0.55)       # shoes
        cone(0.17, 0.14, 2.9, 4.55, x=0.74 * s, sy=1.1)                # sleeves
        ball(0.13, 0.75 * s, 0.03, 2.82)                               # hands
    cone(0.66, 0.56, 1.6, 4.65, sy=0.6)                                # the overcoat
    ball(0.62, 0.0, 0.0, 4.6, sx=1.2, sy=0.62, sz=0.34)                # shoulders
    cone(0.17, 0.16, 4.65, 5.15)                                       # neck
    ball(0.34, 0.0, 0.02, 5.42, sx=0.9, sy=1.0, sz=1.12)               # head
    ball(0.35, 0.0, 0.0, 5.6, sx=1.0, sy=1.12, sz=0.9)                 # the bowler's crown
    cone(0.6, 0.58, 5.54, 5.6, sy=1.18, seg=48)                        # and its brim
    me = bpy.data.meshes.new("figure")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me


def link(sc, name, me, loc, rot=0.0, scale=1.0):
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (scale, scale, scale)
    sc.collection.objects.link(ob)
    return ob


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = json.load(open("out/anyway/level.json"))
    LAP, (px, py) = data["lap"], data["pivot"]
    LAPLEN[0] = LAP
    sc = bpy.context.scene

    level = mesh_from(data, "level")
    level_cut = mesh_from(json.load(open("out/anyway/level_cut.json")), "level_cut")
    fdata = json.load(open("out/anyway/furniture.json"))
    furn = mesh_from(fdata, "furniture")
    furn_cut = mesh_from(json.load(open("out/anyway/furniture_cut.json")), "furniture_cut")
    stone, ball, man = stone_mesh(), sphere_mesh(), figure_mesh()
    for n in range(a.lo, a.hi + 1):
        top = a.cut and n == a.hi
        z = n * LAP
        link(sc, f"level{n}", level_cut if top else level, (0, 0, z))
        link(sc, f"furniture{n}", furn_cut if top else furn, (0, 0, z))
        link(sc, f"stone{n}", stone, (px, py, z - 0.4))
        for i, (x, y, sz, r) in enumerate(fdata["spheres"]):
            link(sc, f"sphere{n}_{i}", ball, (x, y, z + sz), scale=r)
    fx, fy = px + a.figure[0], py + a.figure[1]
    face = math.atan2(-(px - fx), (py - fy))          # he faces the stone
    link(sc, "figure", man, (fx, fy, a.hi * LAP - 0.4), rot=face)
    meshes = {"building": [level, level_cut], "furniture": [furn, furn_cut, ball], "stone": [stone], "figure": [man]}

    cam = bpy.data.cameras.new("cam")
    cam.clip_start = 1.0
    cam.clip_end = 20000
    co = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(co)
    if a.lens:
        cam.type = "PERSP"
        cam.lens = a.lens
        cam.sensor_width = 36
        co.location = Vector(a.cam)
        q = (Vector(a.look) - co.location).to_track_quat("-Z", "Y")
        co.rotation_euler = q.to_euler()
        co.rotation_euler.rotate_axis("Z", math.radians(a.roll))
        cam.shift_x, cam.shift_y = a.shift
        INVERSE[0] = True
        DEPTH[:] = [5.0, 4000.0]
    else:
        cam.type = "ORTHO"
        cam.ortho_scale = a.scale
        el, az = math.radians(a.elev), math.radians(a.azim)
        target = Vector((px, py, a.cz * LAP))
        dirn = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
        dist = 3000.0
        co.location = target + dirn * dist
        co.rotation_euler = (-dirn).to_track_quat("-Z", "Y").to_euler()
        DEPTH[:] = [dist - 450.0, dist + 450.0]
    sc.camera = co

    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("GPU setup failed:", e)
    sc.cycles.samples = 1
    sc.cycles.filter_width = 0.01
    sc.cycles.use_animated_seed = False
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.cycles.use_adaptive_sampling = False
    sc.render.film_transparent = True
    sc.render.dither_intensity = 0.0
    sc.render.resolution_x = a.ss * (int(a.res * a.aspect) if a.aspect < 1 else a.res)
    sc.render.resolution_y = a.ss * (a.res if a.aspect < 1 else int(a.res / a.aspect))
    sc.render.resolution_percentage = 100
    if a.border:
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        (sc.render.border_min_x, sc.render.border_max_x,
         sc.render.border_min_y, sc.render.border_max_y) = a.border
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "BW"
    sc.render.image_settings.color_depth = "16"
    try:
        sc.view_settings.view_transform = "Raw"
    except Exception:
        sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

    def assign(mat_for):
        for cls, mlist in meshes.items():
            m = mat_for(cls)
            for me in mlist:
                me.materials.clear()
                me.materials.append(m)

    passes = a.passes.split(",")
    for kind in passes:
        if kind == "light":
            continue
        if kind == "id":
            mats = {cls: emission_material(f"id_{cls}", "id", v) for cls, v in IDS.items()}
            assign(lambda cls: mats[cls])
        else:
            m = emission_material(kind, kind)
            assign(lambda cls: m)
        sc.render.filepath = f"{a.out}_{kind}.png"
        bpy.ops.render.render(write_still=True)
        print("WROTE", sc.render.filepath, flush=True)

    # sun: direct light only, so each pixel is lit (n.l) or in shadow (0)
    saz, sel = math.radians(a.sun[0]), math.radians(a.sun[1])
    sd = Vector((math.sin(saz) * math.cos(sel), math.cos(saz) * math.cos(sel), math.sin(sel)))
    if "light" in passes:
        m = bpy.data.materials.new("white")
        m.use_nodes = True
        nt = m.node_tree
        for n_ in list(nt.nodes):
            nt.nodes.remove(n_)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
        dif.inputs["Color"].default_value = (1, 1, 1, 1)
        nt.links.new(dif.outputs["BSDF"], out.inputs["Surface"])
        assign(lambda cls: m)
        sun = bpy.data.lights.new("sun", "SUN")
        sun.energy = math.pi * 0.9
        sun.angle = 0.0
        so = bpy.data.objects.new("sun", sun)
        sc.collection.objects.link(so)
        so.rotation_euler = sd.to_track_quat("Z", "Y").to_euler()
        sc.cycles.max_bounces = 1
        sc.cycles.diffuse_bounces = 0
        sc.render.filepath = f"{a.out}_light.png"
        bpy.ops.render.render(write_still=True)
        print("WROTE", sc.render.filepath, flush=True)
    json.dump({"depth": DEPTH, "inverse": INVERSE[0], "ss": a.ss, "lap": LAP, "pivot": [px, py],
               "cut_z": a.hi * LAP + data["cut"], "top_z": a.hi * LAP, "xy": XY, "sun": list(sd),
               "figure": [fx, fy], "ids": IDS, "width": sc.render.resolution_x},
              open(f"{a.out}_meta.json", "w"))


main()
