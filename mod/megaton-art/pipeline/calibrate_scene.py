# SPDX-License-Identifier: MIT
"""Blender side of the camera proof: a checkerboard of floor squares and posts of known height.

    Blender -b --python pipeline/calibrate_scene.py -- OUT_DIR

Writes OUT_DIR/checker.png (every second floor square, flat red), posts.png
(blue posts 96 px = one wall height tall on a few hex centres, green posts
1.80 m = one person tall) and calib.json (canvas and what stands where).
pipeline/calibrate.py lays them over the game's own picture.
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from pipeline import bscene as S      # noqa: E402
from pipeline import proj as P        # noqa: E402

SQUARES = range(-4, 5)                              # floor squares around the origin's square
WALL_POSTS = [(0, 0), (4, 0), (-4, 0), (0, 4), (0, -4), (3, 3), (-5, 2)]     # hexes (dhx, dhy)
HUMAN_POSTS = [(2, 2), (-2, -2), (6, -2)]
POST_HALF = 0.05                                    # 4 px wide posts


def flat_material(name, colour):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*colour, 1.0)
    emission.inputs["Strength"].default_value = 4.0
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def add_mesh(name, vertices, faces, material, layer):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj[S.LAYER_PROP] = layer
    bpy.context.scene.collection.objects.link(obj)
    return obj


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    S.reset()
    red = flat_material("red", (1.0, 0.0, 0.0))
    blue = flat_material("blue", (0.0, 0.2, 1.0))
    green = flat_material("green", (0.0, 1.0, 0.0))

    vertices, faces = [], []
    for qy in SQUARES:
        for qx in SQUARES:
            if (qx + qy) & 1:
                continue
            x, y = P.square_corner_xy(qx, qy)
            base = len(vertices)
            vertices += [(x, y, 0.0), (x + P.SQ_U_M, y, 0.0), (x + P.SQ_U_M, y + P.SQ_V_M, 0.0), (x, y + P.SQ_V_M, 0.0)]
            faces.append((base, base + 1, base + 2, base + 3))
    add_mesh("checker", vertices, faces, red, "checker")

    def posts(name, hexes, height, material):
        vertices, faces = [], []
        for dhx, dhy in hexes:
            x, y = P.hex_xy(dhx, dhy)
            # a camera-facing blade: exactly 2 * POST_HALF wide on screen, standing on the hex centre
            rx, ry = P.SCREEN_RIGHT
            base = len(vertices)
            vertices += [(x - rx * POST_HALF, y - ry * POST_HALF, 0.0), (x + rx * POST_HALF, y + ry * POST_HALF, 0.0),
                         (x + rx * POST_HALF, y + ry * POST_HALF, height), (x - rx * POST_HALF, y - ry * POST_HALF, height)]
            faces.append((base, base + 1, base + 2, base + 3))
        add_mesh(name, vertices, faces, material, "posts")

    posts("wall_posts", WALL_POSTS, P.WALL_H, blue)
    posts("human_posts", HUMAN_POSTS, P.HUMAN_H, green)

    canvas = S.auto_canvas(shadow=False, pad=4)
    S.render_beauty(os.path.join(out_dir, "checker.png"), canvas, layer="checker", ss=4, samples=4, ground_bounce=False)
    S.render_beauty(os.path.join(out_dir, "posts.png"), canvas, layer="posts", ss=4, samples=4, ground_bounce=False)
    with open(os.path.join(out_dir, "calib.json"), "w") as f:
        json.dump({"canvas": canvas, "ss": 4, "squares": [SQUARES.start, SQUARES.stop],
                   "wall_posts": WALL_POSTS, "human_posts": HUMAN_POSTS,
                   "wall_px": P.WALL_PX, "human_px": P.HUMAN_PX, "proj": P.describe()}, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1])
