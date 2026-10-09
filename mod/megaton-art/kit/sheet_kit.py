# SPDX-License-Identifier: MIT
"""Building blocks for TILE SHEETS (roofs and floors): things that lie flat. Blender side.

Sheet coordinates (pipeline/tilegeo.py): x 0..ctx.w runs to the screen's lower left, y 0..ctx.h
to its lower right, z is the height above the tile plane. On screen a square is only 55 x 64 px
and a metre is 40 px across, 17 px in depth: detail along y is squeezed to less than half, so
ridges, seams and boards that run ALONG y (down the screen to the right) read best, and anything
finer than about 0.12 m across them turns to noise.

    tin(x0, y0, x1, y1, z)            one corrugated sheet lying flat (ridges along y, or along x)
    tin_field(x0, y0, x1, y1, ...)    a whole area of overlapping, mismatched sheets
    plank_deck(x0, y0, x1, y1, ...)   boards lying side by side
    plate(x0, y0, x1, y1, ...)        one flat plate of anything (patch, hatch, steel sheet, ground)
    tarp(x0, y0, x1, y1, ...)         a sagging, wrinkled sheet of canvas
    rafters(x0, y0, x1, y1, ...)      beams UNDER the plane: what a hole in a roof shows
    weights(points, ...)              tyres / blocks that hold loose sheets down
Roof sheets are lifted to roof height by the pipeline; build everything around z = 0.
"""
import math
import random

import bmesh
from mathutils import noise as mnoise, Vector

from . import geo, mat


def tin(x0, y0, x1, y1, z=0.0, along="y", slope=0.0, roll=0.0, material=None, wavelength=0.16, depth=0.04,
        rust=0.4, paint=(0.32, 0.33, 0.325), seed=0, layer="main", name="tin"):
    """One sheet of corrugated iron lying on the plane over x0..x1, y0..y1 (x0 < x1, y0 < y1).
    along: the axis its ridges run along ("y": down the slope towards the viewer, the stock look).
    slope: degrees it falls towards +y; roll: degrees of sideways tilt. wavelength 0.16 m is about
    6 px between ridges across x: the finest that still reads as corrugation on a roof."""
    material = material or mat.corrugated(paint=paint, rust=rust, seed=seed)
    return geo.corrugated_panel(x1 - x0, y1 - y0, (x1, y0, z), geo.U, material, wavelength=wavelength, depth=depth,
                                tilt=90.0 + slope, roll=roll, layer=layer, name=name, horizontal=(along == "x"))


ZINC = (0.32, 0.33, 0.325)         # weathered galvanised sheet seen from above: stock roofs are this light


def tin_field(x0, y0, x1, y1, z=0.0, sheet=(0.95, 2.1), jitter=0.25, lift=0.035, seed=1, rust=(0.15, 0.6),
              paints=(), paint_share=0.25, skip=None, along="y", slope=0.0, wavelength=0.16, layer="main", zinc=ZINC):
    """Cover x0..x1, y0..y1 with overlapping sheets, each its own size, rust, height and (some) old
    paint: the mismatched look. Rows run along x; sheets overlap their neighbours by about 8 cm
    and the next row by 15 cm (the upper row lies on top, as on a real roof).
    skip(xa, ya, xb, yb) -> True leaves that sheet out (holes, places for other things).
    Returns the objects."""
    r = random.Random(seed)
    objects = []
    index = 0
    width, length = sheet
    y = y0
    row = 0
    while y < y1 - 0.05:
        ln = min(length * r.uniform(1.0 - jitter, 1.0 + jitter * 0.5), y1 - y)
        if y1 - (y + ln) < length * 0.35:
            ln = y1 - y
        x = x0 - (r.uniform(0.0, width * 0.5) if row % 2 else 0.0)
        while x < x1 - 0.05:
            w = width * r.uniform(1.0 - jitter, 1.0 + jitter)
            xa, xb = max(x0, x), min(x1, x + w)
            x += w - 0.08
            if xb - xa < 0.12:
                continue
            ya, yb = y - (0.15 if row else 0.0), y + ln
            index += 1
            if skip and skip(xa, ya, xb, yb):
                continue
            paint = r.choice(list(paints)) if paints and r.random() < paint_share else None
            if paint is None and zinc is not None:          # bare sheets differ a little in tone
                tone = r.uniform(0.8, 1.1)
                paint = tuple(round(c * tone, 3) for c in zinc)
            material = mat.corrugated(paint=paint, rust=r.uniform(*rust), seed=seed * 31 + index)
            # later rows lie under the row behind them; neighbours alternate over / under
            height = z + lift * (0.4 + (index % 2) * 0.5) - 0.012 * row + r.uniform(0.0, lift * 0.3)
            objects.append(tin(xa, max(y0 - 0.0, ya), xb, yb, max(z, height), along=along, slope=slope + r.uniform(-0.8, 0.8),
                               roll=r.uniform(-1.2, 1.2), material=material, wavelength=wavelength, layer=layer,
                               name=f"tin{index}"))
        y += ln
        row += 1
    return objects


def plate(x0, y0, x1, y1, z=0.0, thickness=0.02, material=None, rot=0.0, layer="main", name="plate", bevel=0.004):
    """A flat plate over x0..x1, y0..y1 with its top at z + thickness; rot turns it about its centre."""
    material = material or mat.steel(rust=0.6)
    return geo.box((x1 - x0, y1 - y0, thickness), ((x0 + x1) / 2.0, (y0 + y1) / 2.0, z), rot, material, bevel=bevel,
                   layer=layer, name=name)


def plank_deck(x0, y0, x1, y1, z=0.0, along="y", board=0.2, gap=0.015, thickness=0.035, seed=1, colour=(0.27, 0.14, 0.06),
               ragged=0.0, missing=0.0, grey=0.35, layer="main"):
    """Boards lying side by side over x0..x1, y0..y1, running along `along`. ragged: metres by which
    board ends differ; missing: share of boards left out (gaps to look through)."""
    r = random.Random(seed)
    objects = []
    span_across = (x1 - x0) if along == "y" else (y1 - y0)
    count = max(1, int(round(span_across / (board + gap))))
    step = span_across / count
    for i in range(count):
        if r.random() < missing:
            continue
        a = r.uniform(0.0, ragged)
        b = r.uniform(0.0, ragged)
        material = mat.planks(colour=tuple(c * r.uniform(0.75, 1.2) for c in colour), width=board * 3, axis="X",
                              grey=min(1.0, grey * r.uniform(0.5, 1.6)), seed=seed * 17 + i)
        if along == "y":
            length = (y1 - y0) - a - b
            centre = (x0 + step * (i + 0.5), y0 + a + length / 2.0, z + r.uniform(0.0, 0.012))
            rot = 90.0 + r.uniform(-1.0, 1.0)
        else:
            length = (x1 - x0) - a - b
            centre = (x0 + a + length / 2.0, y0 + step * (i + 0.5), z + r.uniform(0.0, 0.012))
            rot = r.uniform(-1.0, 1.0)
        objects.append(geo.box((length, step - gap, thickness), centre, rot, material, bevel=0.006, layer=layer,
                               name=f"plank{i}"))
    return objects


def tarp(x0, y0, x1, y1, z=0.03, colour=(0.20, 0.17, 0.10), sag=0.06, wrinkle=0.035, seed=1, layer="main", name="tarp"):
    """Canvas thrown over the plane: a wrinkled sheet whose edges lie on z and whose middle bulges
    or sags by `sag` (negative sags). Its corners are not pinned: add weights()."""
    nx = max(4, int((x1 - x0) / 0.12))
    ny = max(4, int((y1 - y0) / 0.12))
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v
            edge = math.sin(math.pi * u) * math.sin(math.pi * v)
            bump = mnoise.noise(Vector((x * 2.3 + seed * 7.1, y * 2.3 - seed * 3.3, seed * 1.7)))
            fold = mnoise.noise(Vector((x * 6.0 + seed, y * 1.5, 0.37 + seed)))
            row.append(bm.verts.new((x, y, z + sag * edge + wrinkle * (0.6 * bump + 0.4 * fold) * (0.35 + 0.65 * edge))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    return geo._finish(bm, name, mat.tarp(colour, seed=seed), (0, 0, 0), 0.0, layer, smooth=True, solidify=0.012)


def rafters(x0, y0, x1, y1, z=-0.16, along="y", spacing=0.6, size=(0.07, 0.14), material=None, purlins=True, layer="main"):
    """Roof timbers under the plane over x0..x1, y0..y1: beams running along `along` every `spacing`
    metres with their top at z, and (purlins) two cross battens on top of them. Put them under
    a gap in the sheets: they are all one sees of the building through a hole."""
    material = material or mat.planks(colour=(0.16, 0.09, 0.045), width=0.4, axis="X", grey=0.2, seed=5)
    objects = []
    across = (x1 - x0) if along == "y" else (y1 - y0)
    count = max(2, int(across / spacing) + 1)
    for i in range(count):
        t = i / (count - 1)
        if along == "y":
            centre, length, rot = (x0 + across * t, (y0 + y1) / 2.0, z - size[1]), y1 - y0, 90.0
        else:
            centre, length, rot = ((x0 + x1) / 2.0, y0 + across * t, z - size[1]), x1 - x0, 0.0
        objects.append(geo.box((length, size[0], size[1]), centre, rot, material, bevel=0.006, layer=layer, name=f"rafter{i}"))
    if purlins:
        for t in (0.3, 0.72):
            if along == "y":
                centre, length, rot = ((x0 + x1) / 2.0, y0 + (y1 - y0) * t, z), x1 - x0, 0.0
            else:
                centre, length, rot = (x0 + (x1 - x0) * t, (y0 + y1) / 2.0, z), y1 - y0, 90.0
            objects.append(geo.box((length, 0.05, 0.035), centre, rot, material, bevel=0.004, layer=layer, name="purlin"))
    return objects


def weights(points, kind="tire", seed=1, z=0.04, layer="main"):
    """Things that hold loose sheets down, one per (x, y): "tire", "block" (cinder block) or "mix"."""
    r = random.Random(seed)
    objects = []
    for k, (x, y) in enumerate(points):
        what = kind if kind != "mix" else r.choice(("tire", "tire", "block"))
        if what == "tire":
            objects.append(geo.tire((x, y, z), radius=r.uniform(0.3, 0.36), lying=True, rot=r.uniform(0, 180), seed=seed + k,
                                    layer=layer))
        else:
            objects.append(geo.box((0.4, 0.2, 0.19), (x, y, z), r.uniform(0, 180), mat.concrete(seed=seed + k),
                                   bevel=0.01, layer=layer, name="block"))
    return objects
