# SPDX-License-Identifier: MIT
"""Blender scene template: the game's camera, the stock-art light rig, the render passes.

Runs inside Blender (5.x, Cycles). Everything a piece needs is created from
scratch by `reset()`; nothing is read from a .blend file, so a render is a
pure function of the piece script. pipeline/blender_piece.py drives it:

    S.reset()                                   # empty file, camera, sun, sky, ground
    ... the piece's builder creates meshes (kit.geo / kit.mat) ...
    canvas = S.auto_canvas()
    S.render_beauty(path, canvas)               # the piece alone on transparent film
    S.render_shadow(path, canvas)               # ground as shadow catcher: alpha = piece + shadow
    S.render_position(path, canvas)             # where in the world every pixel's surface is
    S.render_mask(path, canvas, objects)        # coverage of some objects (animated palette ranges)

CAMERA  orthographic, 25.659 deg above the horizon, looking along (-0.5, -0.866, 0)
        on the ground; 40 px per metre (pipeline/proj.py explains why this is exact).
        A canvas is (x0, y0, x1, y1) in screen px relative to the origin hex centre;
        pixel (i, j) of the result covers [x0 + i, x0 + i + 1) x [y0 + j, y0 + j + 1).

LIGHT   read off stock sprites (`pipeline/calibrate.py --light` writes the study sheet):
        - one key light from behind the viewer's LEFT shoulder: barrels and tanks are
          brightest about a third in from their left edge, the two wall directions
          are nearly equally bright (walls facing screen-left about 8 % brighter),
          tops are 1.3-1.4x the sides, painted shadows peek out on the RIGHT of the
          object's base and are short. That is a sun 20 deg left of the view axis
          and 50 deg up.
        - soft: stock shadows have no hard edge -> sun disc 12 deg.
        - grey fill, no black sides -> uniform, slightly cool sky at about a sixth of the sun.
        - stock art is DARK and contrasty: mean luminance 35-60 of 255, darkest 5 % at 12-25,
          brightest 5 % at 84-95. EXPOSURE below (with the default grade in convert.py)
          maps a physically plausible albedo (0.1-0.3) onto that range, so materials keep
          sensible values and never need to be darkened by hand.
        - stock shadows are painted on the ground as opaque dark pixels, stippled at the
          rim (car1.frm); ours are the shadow-catcher pass turned into the same stipple.
        Do not add lights to a piece to "fix" it: a second sun direction is what makes a
        sprite look pasted in. Emitters (kit.mat.emitter) are fine: they are part of the piece.
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

from . import proj as P

# ------------------------------------------------------------------ light rig
SUN_AZIMUTH_LEFT_DEG = 20.0      # the sun stands this far to the viewer's left of the view axis
SUN_ELEVATION_DEG = 50.0
SUN_ANGLE_DEG = 12.0             # apparent size: shadow softness
SUN_STRENGTH = 3.6               # W/m2
SUN_COLOR = (1.0, 0.96, 0.9)
SKY_STRENGTH = 0.55
SKY_COLOR = (0.82, 0.86, 1.0)    # slightly cool fill against the warm key
GROUND_ALBEDO = (0.22, 0.18, 0.13)   # wasteland dirt: what bounces up into the piece
EXPOSURE = -1.55                 # stops; calibrated against stock crates / shack walls in the engine
GAMMA = 1.0

DEFAULT_SS = 3                   # supersampling: render at 3x, box-filter down in pipeline/convert.py
DEFAULT_SAMPLES = 48

POS_RANGE = 64.0                 # position pass: metres mapped to 0..1 (x, y around 0; z from -1)
POS_Z0 = -1.0
POS_ZRANGE = 32.0

GROUND_NAME = "MG_ground"
CAMERA_NAME = "MG_camera"
SUN_NAME = "MG_sun"
LAYER_PROP = "mg_layer"          # custom property: which sprite layer an object belongs to ("main" default)


def sun_direction():
    """Unit vector from the scene towards the sun (world space)."""
    az = math.radians(SUN_AZIMUTH_LEFT_DEG)
    el = math.radians(SUN_ELEVATION_DEG)
    gx = -math.sin(az) * P.SCREEN_RIGHT[0] - math.cos(az) * P.SCREEN_INTO[0]
    gy = -math.sin(az) * P.SCREEN_RIGHT[1] - math.cos(az) * P.SCREEN_INTO[1]
    return Vector((gx * math.cos(el), gy * math.cos(el), math.sin(el)))


# ---------------------------------------------------------------------- reset
def reset():
    """Empty file, Cycles, colour management, light rig, shadow-catcher ground."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    cycles.seed = 0
    cycles.use_animated_seed = False
    cycles.samples = DEFAULT_SAMPLES
    cycles.use_adaptive_sampling = False
    cycles.use_denoising = False
    cycles.max_bounces = 4
    cycles.diffuse_bounces = 2
    cycles.glossy_bounces = 2
    cycles.transparent_max_bounces = 8
    cycles.filter_width = 1.5
    cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    _pick_device(scene)

    scene.render.film_transparent = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.use_file_extension = True
    scene.render.dither_intensity = 0.0
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = EXPOSURE
    scene.view_settings.gamma = GAMMA

    world = bpy.data.worlds.new("MG_world")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*SKY_COLOR, 1.0)
    background.inputs["Strength"].default_value = SKY_STRENGTH
    scene.world = world

    sun_data = bpy.data.lights.new(SUN_NAME, "SUN")
    sun_data.energy = SUN_STRENGTH
    sun_data.color = SUN_COLOR
    sun_data.angle = math.radians(SUN_ANGLE_DEG)
    sun = bpy.data.objects.new(SUN_NAME, sun_data)
    scene.collection.objects.link(sun)
    # A sun shines along its local -Z.
    sun.rotation_euler = sun_direction().to_track_quat("Z", "Y").to_euler()

    camera_data = bpy.data.cameras.new(CAMERA_NAME)
    camera_data.type = "ORTHO"
    camera_data.clip_start = 1.0
    camera_data.clip_end = 400.0
    camera = bpy.data.objects.new(CAMERA_NAME, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    ground_mesh = bpy.data.meshes.new(GROUND_NAME)
    r = 150.0
    ground_mesh.from_pydata([(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new(GROUND_NAME, ground_mesh)
    ground[LAYER_PROP] = "ground"
    material = bpy.data.materials.new(GROUND_NAME)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*GROUND_ALBEDO, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    ground_mesh.materials.append(material)
    scene.collection.objects.link(ground)
    return scene


def _pick_device(scene):
    want = os.environ.get("MG_ART_DEVICE", "GPU").upper()
    scene.cycles.device = "CPU"
    if want != "GPU":
        return
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.refresh_devices()
        found = False
        for device in prefs.devices:
            device.use = device.type == "METAL"
            found = found or device.use
        if found:
            scene.cycles.device = "GPU"
    except Exception as error:      # no GPU back end in this build: CPU is fine
        print("[bscene] GPU not available:", error)


# --------------------------------------------------------------------- camera
def set_camera(canvas, ss=DEFAULT_SS):
    """Frame `canvas` = (x0, y0, x1, y1) screen px (integers) at `ss` x resolution."""
    x0, y0, x1, y1 = canvas
    width, height = x1 - x0, y1 - y0
    if width <= 0 or height <= 0:
        raise ValueError(f"empty canvas {canvas}")
    scene = bpy.context.scene
    camera = scene.camera
    scene.render.resolution_x = width * ss
    scene.render.resolution_y = height * ss
    camera.data.sensor_fit = "AUTO"
    camera.data.ortho_scale = max(width, height) / P.PX_PER_M
    right, up, view = Vector(P.CAM_RIGHT), Vector(P.CAM_UP), Vector(P.VIEW_DIR)
    centre_x, centre_y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    target = right * (centre_x / P.PX_PER_M) - up * (centre_y / P.PX_PER_M)
    camera.location = target - view * 150.0
    rotation = Matrix((right, up, -view)).transposed()      # columns: camera x, y, z axes
    camera.rotation_euler = rotation.to_euler()
    return camera


# -------------------------------------------------------------------- objects
def piece_objects(layer=None):
    """Renderable objects of the piece (not the rig); `layer` filters by sprite layer."""
    found = []
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH", "CURVE", "FONT", "SURFACE", "META"}:
            continue
        obj_layer = obj.get(LAYER_PROP, "main")
        if obj_layer == "ground":
            continue
        if layer is None or obj_layer == layer:
            found.append(obj)
    return found


def layers():
    names = []
    for obj in piece_objects():
        name = obj.get(LAYER_PROP, "main")
        if name not in names:
            names.append(name)
    return names


def world_points(objects, spacing=0.12):
    """Sample points (world space) on the evaluated surfaces of `objects`: all vertices plus
    points on every triangle about `spacing` metres apart. Used for canvas and footprint."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        try:
            mesh = evaluated.to_mesh()
        except RuntimeError:
            continue
        if mesh is None:
            continue
        matrix = evaluated.matrix_world
        vertices = [matrix @ v.co for v in mesh.vertices]
        points.extend(vertices)
        mesh.calc_loop_triangles()
        for triangle in mesh.loop_triangles:
            a, b, c = (vertices[i] for i in triangle.vertices)
            longest = max((b - a).length, (c - b).length, (a - c).length)
            n = int(longest / spacing)
            if n < 2:
                continue
            n = min(n, 40)
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    u, v = i / n, j / n
                    points.append(a + (b - a) * u + (c - a) * v)
        evaluated.to_mesh_clear()
    return points


def auto_canvas(objects=None, pad=6, shadow=True):
    """Smallest canvas (screen px, integers) around `objects` (default: every piece object).

    With `shadow`, the canvas also covers where the soft ground shadow can fall
    (to the right and up-screen of the piece, by its height).
    """
    objects = piece_objects() if objects is None else objects
    points = world_points(objects, spacing=1e9)
    if not points:
        raise ValueError("the piece has no geometry")
    xs, ys = [], []
    for point in points:
        px, py = P.world_to_px(point.x, point.y, point.z)
        xs.append(px)
        ys.append(py)
        if shadow and point.z > 0.0:
            reach = point.z / math.tan(math.radians(SUN_ELEVATION_DEG - SUN_ANGLE_DEG / 2))
            towards = -sun_direction()
            ground = Vector((towards.x, towards.y)).normalized() * reach
            sx, sy = P.world_to_px(point.x + ground.x, point.y + ground.y, 0.0)
            xs.append(sx)
            ys.append(sy)
    return (math.floor(min(xs)) - pad, math.floor(min(ys)) - pad,
            math.ceil(max(xs)) + pad, math.ceil(max(ys)) + pad)


# --------------------------------------------------------------------- render
def _render(path, samples):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _show_only(layer):
    """Make exactly the objects of one sprite layer visible to the camera and to light."""
    for obj in bpy.context.scene.objects:
        if obj.type in {"CAMERA", "LIGHT"}:
            continue
        obj_layer = obj.get(LAYER_PROP, "main")
        if obj_layer == "ground":
            continue
        obj.hide_render = obj_layer != layer


def _position_material():
    name = "MG_position"
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    geometry = nodes.new("ShaderNodeNewGeometry")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    combine = nodes.new("ShaderNodeCombineXYZ")
    links.new(geometry.outputs["Position"], separate.inputs[0])
    for axis, (offset, scale) in zip("XYZ", ((POS_RANGE / 2, POS_RANGE), (POS_RANGE / 2, POS_RANGE), (-POS_Z0, POS_ZRANGE))):
        math_node = nodes.new("ShaderNodeMath")
        math_node.operation = "MULTIPLY_ADD"
        math_node.inputs[1].default_value = 1.0 / scale
        math_node.inputs[2].default_value = offset / scale
        links.new(separate.outputs[axis], math_node.inputs[0])
        links.new(math_node.outputs[0], combine.inputs[axis])
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    links.new(combine.outputs[0], emission.inputs["Color"])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def render_beauty(path, canvas, layer="main", ss=DEFAULT_SS, samples=DEFAULT_SAMPLES, ground_bounce=True):
    """Objects of `layer` alone on transparent film (the ground still bounces light, unseen)."""
    scene = bpy.context.scene
    set_camera(canvas, ss)
    _show_only(layer)
    ground = bpy.data.objects[GROUND_NAME]
    ground.hide_render = not ground_bounce
    ground.is_shadow_catcher = False
    ground.visible_camera = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = EXPOSURE
    scene.render.image_settings.color_depth = "8"
    bpy.context.view_layer.material_override = None
    _render(path, samples)


def render_shadow(path, canvas, layer="main", ss=DEFAULT_SS, samples=DEFAULT_SAMPLES):
    """Same view with the ground as shadow catcher: alpha = object + shadow coverage."""
    scene = bpy.context.scene
    set_camera(canvas, ss)
    _show_only(layer)
    ground = bpy.data.objects[GROUND_NAME]
    ground.hide_render = False
    ground.visible_camera = True
    ground.is_shadow_catcher = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = EXPOSURE
    scene.render.image_settings.color_depth = "8"
    bpy.context.view_layer.material_override = None
    _render(path, samples)
    ground.is_shadow_catcher = False
    ground.visible_camera = False


def render_position(path, canvas, layer="main", ss=DEFAULT_SS):
    """World position of the first surface under every sample, as 16-bit RGB (see decode in convert.py)."""
    scene = bpy.context.scene
    set_camera(canvas, ss)
    _show_only(layer)
    ground = bpy.data.objects[GROUND_NAME]
    ground.hide_render = True
    scene.view_settings.view_transform = "Raw"
    scene.view_settings.exposure = 0.0
    scene.render.image_settings.color_depth = "16"
    bpy.context.view_layer.material_override = _position_material()
    filter_width = scene.cycles.filter_width
    scene.cycles.filter_width = 0.01
    _render(path, 1)
    scene.cycles.filter_width = filter_width
    bpy.context.view_layer.material_override = None
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = EXPOSURE
    scene.render.image_settings.color_depth = "8"
    ground.hide_render = False


def render_mask(path, canvas, selected, layer="main", ss=DEFAULT_SS):
    """Coverage of the `selected` objects as seen through everything else of the layer: the
    others still hide them but render as holes (holdout). Alpha of the result is the mask."""
    scene = bpy.context.scene
    set_camera(canvas, ss)
    _show_only(layer)
    ground = bpy.data.objects[GROUND_NAME]
    ground.hide_render = True
    chosen = set(obj.name for obj in selected)
    changed = []
    for obj in piece_objects(layer):
        if obj.name not in chosen:
            obj.is_holdout = True
            changed.append(obj)
    _render(path, 4)
    for obj in changed:
        obj.is_holdout = False
    ground.hide_render = False


def position_meta():
    return {"range": POS_RANGE, "z0": POS_Z0, "zrange": POS_ZRANGE}


def rig_meta():
    direction = sun_direction()
    return {
        "sun_azimuth_left_deg": SUN_AZIMUTH_LEFT_DEG, "sun_elevation_deg": SUN_ELEVATION_DEG,
        "sun_angle_deg": SUN_ANGLE_DEG, "sun_strength": SUN_STRENGTH, "sky_strength": SKY_STRENGTH,
        "exposure": EXPOSURE, "sun_direction": [direction.x, direction.y, direction.z],
    }
