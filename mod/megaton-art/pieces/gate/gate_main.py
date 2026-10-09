# SPDX-License-Identifier: MIT
"""THE GATE of Megaton: an airliner wing laid across two plated bays as a lintel, its engine still
hanging under it as the door motor, a salvaged-letter sign above, and two sliding leaves.

Pieces (all share ONE origin: the even / even hex one row BEHIND the door hex; in the town the
door hex is plan.GATE = (100, 127), so every piece here is placed with its origin on (100, 126)):

    mg_gate        the fixed structure. Blocks hexes hx -4..-2 and +2..+4 of the wall row and the
                   four hexes at the feet of the bays; the passage hexes -1, 0, +1 are left to the door.
    mg_gate_sign   the MEGATON sign on the wing, floodlights, bulbs: ONE part, anchored on the hex
                   in front of the door, and the gate's lamp (the engine lights the apron from it).
    mg_gate_shut   the two leaves, closed. One part on the door hex.
    mg_gate_ajar   the leaves half way.
    mg_gate_open   the leaves run back into the bays (only their edges show). One part on the door hex.

The leaves are POCKET doors: they slide in a plane 0.2 m behind the wall line into the bays, so
open leaves hide behind the bay fronts and nothing of them can overlap somebody in the gateway.
pieces/gate/gate_door.py joins shut / ajar / open into one door FRM (frame 0 shut .. last frame
open) for the town's existing door object.

Frame: X.Row(0, 1): r = metres to the screen right of the door centre, f = metres towards the
viewer from the wall line, z up. Left of the passage is r < 0 (rising hx).
"""
import math

import bpy

from kit import piece, geo, mat, G
from kit import gate_extra as X

ROW = X.Row(0, 1)
P = ROW.p

PASS = 1.25                     # half width of the passage between the bays
OUT = 4.5 * X.HEX_R             # outer face of a bay = the boundary between hexes 4 and 5 (3.118 m)
BACK, FRONT = -0.65, 0.10       # bay depth: f of its back and front faces
TOP = 3.0                       # the wing rests on the bays at this height
LEAF_F = -0.26                  # leaves: f of their back face
LEAF_T = 0.12                   # ... and their thickness
LEAF_H = 2.78
LEAF_TEXT = 0.56                # cap height of the stencil on the leaves (20 px)
SIGN_F = 0.10                   # front face of the sign's backing
SIGN_Z0, SIGN_Z1 = 3.44, 4.80

FOOTPRINT = [(2, 1), (3, 1), (4, 1), (-2, 1), (-3, 1), (-4, 1), (3, 2), (-3, 2), (4, 2), (-4, 2)]

STEEL = dict(rust=0.65, seed=3)
PRIMER = (0.20, 0.23, 0.10)             # zinc chromate: the yellow-green inside of every airframe
AIRLINE = (0.30, 0.055, 0.035)          # what is left of the airline's red
CREAM = (0.52, 0.47, 0.34)


def _new_objects(before):
    return [obj for obj in bpy.context.scene.objects if obj.name not in before]


def ghost(build, *args):
    """Build something as a HOLDOUT: it shades the piece being rendered, bounces light on it and
    hides what is behind it, but leaves a hole in the picture. The leaves and the sign are drawn by
    the engine over parts of the gate that were painted before them, so everything of theirs that
    the gate covers must already be missing from their sprites (the leaves run into the bays)."""
    before = {obj.name for obj in bpy.context.scene.objects}
    build(*args)
    for obj in _new_objects(before):
        obj.is_holdout = True
        if obj.type == "LIGHT":
            obj.hide_render = True
        if geo.FX_PROPERTY in obj:
            del obj[geo.FX_PROPERTY]
        geo.set_block(obj, 0.0)


# ------------------------------------------------------------------ structure
def bay(side, seed):
    """Steel frame of one bay (side = -1 left, +1 right): four columns, ring beams, a back sheet."""
    steel = mat.steel(**STEEL)
    inner, outer = side * PASS, side * OUT
    lo, hi = min(inner, outer), max(inner, outer)
    for r in (lo + 0.08, hi - 0.08):
        for f in (BACK + 0.07, FRONT - 0.09):
            geo.ibeam(TOP - 0.16, P(r, f, 0.0), geo.U, steel, vertical=True, height=0.16, width=0.13)
    for f in (BACK + 0.07, FRONT - 0.09):
        geo.ibeam(hi - lo, P(lo, f, TOP - 0.16), geo.U, steel, height=0.16, width=0.13)
    # back: corrugated sheet, seen only through gaps and over the top
    geo.corrugated_panel(hi - lo, TOP - 0.2, P(lo, BACK, 0.0), geo.U, mat.corrugated(rust=0.8, seed=seed), name="bay_back")
    # roof plate the wing sits on
    geo.box((hi - lo, FRONT - BACK, 0.04), P((lo + hi) / 2, (FRONT + BACK) / 2, TOP - 0.02), geo.U,
            mat.painted_metal((0.10, 0.10, 0.10), flaking=0.7, seed=seed), bevel=0.0, name="bay_roof")


def left_bay():
    """Fuselage skin: one big bowed panel with three cabin windows and the airline's stripe."""
    bay(-1, 11)
    lo, hi = -OUT, -PASS
    hull = X.skin(tint=(0.52, 0.53, 0.54), panel=(0.64, 0.98), rust=0.16, grime=0.4, seed=2.0, tone=0.2, stagger=False,
                  bands=[("v", 1.18, 1.46, AIRLINE), ("v", 1.50, 1.55, (0.05, 0.05, 0.06)),
                         ("v", 0.0, 0.40, (0.11, 0.12, 0.13))])
    X.plate(hi - lo + 0.04, 2.95, P(lo - 0.02, FRONT, 0.05), geo.U, hull, bulge=0.16, thickness=0.035, name="hull_panel",
            dent=0.008, seed=3)
    frame = X.bright_metal((0.50, 0.51, 0.52), roughness=0.4)
    for k, r in enumerate((-2.74, -2.18, -1.62)):
        bow = 0.16 * math.sin(math.pi * (r - lo) / (hi - lo))
        geo.box((0.42, 0.03, 0.54), P(r, FRONT + bow + 0.012, 1.72), geo.U, frame, bevel=0.10, name="window_frame")
        glass = mat.flat((0.012, 0.016, 0.02), roughness=0.15) if k != 1 else mat.planks(colour=(0.24, 0.14, 0.07), width=0.1, seed=2)
        geo.box((0.30, 0.03, 0.42), P(r, FRONT + bow + 0.03, 1.78), geo.U, glass, bevel=0.07, name="window")
    # the registration, stencilled low on the skin
    geo.lettering("N-7", P(-2.2, FRONT + 0.19, 0.62), geo.U, size=0.48, depth=0.01, bevel=0.0, font="din",
                  material=mat.sign_paint((0.04, 0.04, 0.05), wear=0.7, seed=5))
    # tyres propped against the foot, the usual gatepost dressing
    x, y, _ = P(-2.80, 0.62)
    geo.tire_stack(3, (x, y, 0.0), seed=4)
    geo.tire(P(-2.15, 0.50, 0.0), lying=False, rot=geo.U + 8.0, lean=14.0, seed=7)


def right_bay():
    """Plates in primer green and bare aluminium; the passage side shows the slot the leaf runs into."""
    bay(1, 17)
    lo, hi = PASS, OUT
    green = X.skin(tint=PRIMER, panel=(0.5, 0.7), rust=0.35, grime=0.6, seed=4.0, metallic=0.0, tone=0.3)
    bare = X.skin(tint=(0.40, 0.41, 0.43), panel=(0.48, 0.62), rust=0.3, grime=0.6, seed=6.0,
                  bands=[("v", 2.05, 2.3, CREAM)])
    X.plate(1.02, 2.92, P(lo, FRONT, 0.04), geo.U, green, thickness=0.03, name="plate_green", dent=0.006, seed=5)
    X.plate(hi - lo - 0.98, 2.70, P(lo + 0.98, FRONT + 0.03, 0.04), geo.U, bare, thickness=0.03, name="plate_bare",
            dent=0.006, seed=6, roll=-1.2)
    X.plate(0.8, 0.42, P(hi - 0.86, FRONT + 0.05, 2.58), geo.U, mat.corrugated(rust=0.85, seed=8), thickness=0.02,
            name="plate_patch", roll=2.0)
    # an access hatch with its handle, and a stencil
    hatch = mat.painted_metal((0.16, 0.18, 0.09), flaking=0.5, seed=3)
    geo.box((0.46, 0.03, 0.62), P(lo + 0.52, FRONT + 0.03, 0.42), geo.U, hatch, bevel=0.03, name="hatch")
    geo.box((0.16, 0.03, 0.04), P(lo + 0.52, FRONT + 0.06, 0.74), geo.U, X.bright_metal(), bevel=0.01, name="hatch_handle")
    X.bolt_row(P(lo + 0.06, FRONT + 0.03, 0.2), P(lo + 0.06, FRONT + 0.03, 2.8), count=9, radius=0.028)
    # the side towards the passage: plate, and the dark pocket the leaf slides into
    side = X.skin(tint=(0.30, 0.31, 0.32), panel=(0.4, 0.9), rust=0.45, grime=0.7, seed=9.0)
    slot0, slot1 = LEAF_F - 0.04, LEAF_F + LEAF_T + 0.04
    X.plate(slot0 - BACK, 2.9, P(lo, BACK, 0.02), geo.V, side, thickness=0.03, name="side_back")
    X.plate(FRONT - slot1, 2.9, P(lo, slot1, 0.02), geo.V, side, thickness=0.03, name="side_front")
    geo.box((0.3, slot1 - slot0, 2.86), P(lo + 0.2, (slot0 + slot1) / 2, 0.0), geo.U, mat.flat((0.012, 0.012, 0.012)),
            bevel=0.0, name="pocket")
    # sandbags at the foot, under the engine
    X.sandbags(P(2.05, 0.46)[:2], P(3.20, 0.46)[:2], courses=2, seed=3)
    X.sandbags(P(2.35, 0.74)[:2], P(3.25, 0.74)[:2], courses=1, seed=5)


def portal():
    """Gateposts with warning stripes, the leaf rail across the passage, the control box."""
    steel = mat.steel(**STEEL)
    stripes = X.hazard(uv=False, width=0.34, seed=1.0)
    for side in (-1, 1):
        r = side * (PASS + 0.10)
        geo.box((0.20, 0.18, 1.35), P(r, FRONT + 0.11, 0.0), geo.U, stripes, bevel=0.012, name="post_stripes")
        geo.box((0.18, 0.16, TOP - 1.35), P(r, FRONT + 0.11, 1.35), geo.U, steel, bevel=0.012, name="post")
        geo.box((0.30, 0.26, 0.10), P(r, FRONT + 0.11, 0.0), geo.U, mat.concrete(seed=2), bevel=0.02, name="post_foot")
    # rail the leaves hang from, with its hangers
    geo.ibeam(2 * OUT - 0.3, P(-OUT + 0.15, LEAF_F + LEAF_T / 2, LEAF_H + 0.03), geo.U, steel, height=0.14, width=0.12)
    # control box on the right post: lever, cable, a red lamp that blinks
    box = mat.painted_metal((0.20, 0.22, 0.20), flaking=0.35, seed=7)
    geo.box((0.26, 0.12, 0.36), P(PASS + 0.36, FRONT + 0.10, 1.18), geo.U, box, bevel=0.015, name="control_box")
    geo.pipe([P(PASS + 0.36, FRONT + 0.17, 1.36), P(PASS + 0.36, FRONT + 0.30, 1.52)], 0.02, X.bright_metal(), name="lever")
    geo.bulb(P(PASS + 0.36, FRONT + 0.14, 1.64), colour=(1.0, 0.1, 0.05), radius=0.055, strength=3.0, fx="alarm")
    geo.cable(P(PASS + 0.40, FRONT + 0.12, 1.54), P(2.0, FRONT + 0.22, 2.25), sag=0.35, radius=0.02)


def lintel():
    """The wing, root on the right bay, tip sailing past the left one; and its engine."""
    metal = X.skin(tint=(0.42, 0.43, 0.45), panel=(0.60, 0.52), rust=0.10, grime=0.4, seed=8.0, tone=0.14, stagger=False,
                   bands=[("v", 0.0, 0.20, (0.03, 0.03, 0.035)), ("u", 6.2, 7.0, AIRLINE), ("u", 5.95, 6.08, (0.6, 0.58, 0.5)),
                          ("u", 0.45, 1.3, (0.07, 0.075, 0.08))])
    X.wing(7.75, chord_root=2.0, chord_tip=0.72, thickness=0.12, sweep=0.80, at=P(3.5, 1.08, TOP + 0.10), rot=0.0,
           material=metal, le_front=False, tip_length=0.55, droop=0.06)
    # a landing light let into the leading edge, and the slat's gap line
    geo.bulb(P(-0.9, 0.80, TOP + 0.10), colour=(1.0, 0.9, 0.7), radius=0.07, strength=1.6)
    # shims: timber between bay roof and wing
    wood = mat.planks(axis="X", width=0.3, seed=9)
    for r in (-2.9, -1.5, 1.5, 2.9):
        geo.box((0.22, 0.6, 0.06), P(r, -0.2, TOP - 0.01), geo.U, wood, bevel=0.01, name="shim")
    # engine on its pylon under the leading edge, in front of the right bay
    er, ez, e0, en = 2.22, 2.40, 0.16, 1.5
    X.nacelle(en, 0.50, P(er, e0, ez), geo.U, cowl=mat.painted_metal((0.30, 0.31, 0.32), flaking=0.35, seed=4),
              band=(en * 0.50, en * 0.80, mat.painted_metal(AIRLINE, flaking=0.4, seed=6)))
    geo.box((0.14, 1.0, 0.24), P(er, 0.55, ez + 0.40), geo.U, mat.painted_metal((0.30, 0.31, 0.32), flaking=0.4, seed=2),
            bevel=0.03, name="pylon")
    # the drive: gearbox on the bay front behind the engine, shaft and chain to the rail
    steel = mat.steel(**STEEL)
    geo.box((0.5, 0.14, 0.44), P(er, FRONT + 0.07, 1.62), geo.U, mat.painted_metal((0.07, 0.07, 0.07), flaking=0.5, seed=1),
            bevel=0.02, name="gearbox")
    geo.pipe([P(er, FRONT + 0.14, 1.9), P(er, FRONT + 0.14, 2.05)], 0.06, steel, name="drive")
    geo.pipe([P(er - 0.22, FRONT + 0.16, 1.80), P(PASS + 0.12, FRONT + 0.16, 2.70)], 0.035, steel, name="shaft")
    # string of bulbs slung under the leading edge
    geo.bulb_string(P(-3.35, 0.66, TOP + 0.02), P(1.55, 0.98, TOP - 0.02), count=9, sag=0.34, radius=0.06, strength=1.7,
                    colours=((1.0, 0.66, 0.26), (1.0, 0.74, 0.34), (1.0, 0.42, 0.14)))
    # navigation light on the tip
    geo.bulb(P(-3.62, 0.36, TOP + 0.12), colour=(1.0, 0.12, 0.04), radius=0.06, strength=3.0, fx="alarm")


def structure(ctx=None):
    left_bay()
    right_bay()
    portal()
    lintel()


# ----------------------------------------------------------------------- sign
LETTERS = (
    # char, r, size, font, colour, roll, lift
    ("M", -2.55, 1.04, "black", (0.66, 0.05, 0.03), 0.0, 0.02),
    ("E", -1.70, 0.92, "rockwell", (0.66, 0.60, 0.44), 0.0, 0.10),
    ("G", -0.88, 1.02, "black", (0.66, 0.44, 0.04), 0.0, 0.02),
    ("A", -0.02, 0.90, "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", (0.62, 0.63, 0.60), 0.0, 0.14),
    ("T", 0.80, 1.06, "impact", (0.16, 0.03, 0.02), 0.0, 0.0),
    ("O", 1.62, 0.96, "/System/Library/Fonts/Supplemental/Georgia Bold.ttf", (0.62, 0.24, 0.03), 0.0, 0.06),
    ("N", 2.50, 0.98, "din", (0.64, 0.62, 0.55), -13.0, -0.20),
)


def _m_bulbs(r0, z0, size, lit):
    """Marquee bulbs on the five corners of the M: enough to say "lit", few enough to leave the M."""
    w = size * 0.74
    for n, (a, b) in enumerate(((-0.41, 0.07), (-0.41, 0.93), (0.0, 0.36), (0.41, 0.93), (0.41, 0.07))):
        on = lit[n % len(lit)]
        geo.bulb(P(r0 + a * w, SIGN_F + 0.17, z0 + b * size), colour=(1.0, 0.82, 0.45) if on else (0.25, 0.16, 0.08),
                 radius=0.042, strength=2.4 if on else 0.25)


def sign(ctx=None):
    frame = ctx.frame if ctx else 0
    steel = mat.steel(rust=0.75, seed=5)
    # frame: uprights standing on the wing, two rails, rakers back to the trailing edge
    for r in (-2.75, -0.95, 0.95, 2.75):
        geo.ibeam(SIGN_Z1 + 0.12 - (TOP + 0.08), P(r, SIGN_F - 0.14, TOP + 0.08), geo.U, steel, vertical=True,
                  height=0.13, width=0.11)
        geo.pipe([P(r, SIGN_F - 0.2, SIGN_Z1 - 0.1), P(r + 0.05, -0.55, TOP + 0.22)], 0.035, steel, name="raker")
    for z in (SIGN_Z0 + 0.22, SIGN_Z1 - 0.2):
        geo.pipe([P(-3.1, SIGN_F - 0.06, z), P(3.1, SIGN_F - 0.06, z)], 0.04, steel, name="sign_rail")
    # backing: four sheets that never belonged together
    # (the M's sheet is PALE: a red letter on a dark sheet has no contrast at 22 px and the sign read "EGATON")
    geo.corrugated_panel(1.10, 1.30, P(-3.10, SIGN_F, SIGN_Z0 + 0.02), geo.U, mat.corrugated(paint=(0.50, 0.46, 0.34), rust=0.22, seed=31),
                         wavelength=0.13, depth=0.02, roll=0.8, name="back_a")
    geo.slab(2.30, 1.36, 0.04, P(-2.04, SIGN_F + 0.01, SIGN_Z0 - 0.04), geo.U, mat.painted_metal((0.035, 0.085, 0.05), flaking=0.35, seed=33),
             name="back_b")
    X.plate(1.50, 1.26, P(0.22, SIGN_F + 0.02, SIGN_Z0 + 0.06), geo.U,
            X.skin(tint=(0.13, 0.15, 0.18), panel=(0.5, 0.42), rust=0.3, grime=0.5, seed=35.0, metallic=0.2), thickness=0.03,
            name="back_c", roll=-0.8)
    geo.boards(P(1.66, SIGN_F + 0.03)[:2], P(3.10, SIGN_F + 0.03)[:2], height=1.34, z=SIGN_Z0 - 0.02, seed=37, ragged=0.10,
               material=mat.planks(colour=(0.11, 0.07, 0.04), width=0.2, seed=6), board=0.21, lean=1.0)
    # letters
    lit = [True] * 5
    if frame == 1:
        lit[3] = False
    if frame == 3:
        lit[1] = False
    for char, r, size, font, colour, roll, lift in LETTERS:
        z = SIGN_Z0 + 0.14 + lift
        if char == "T":
            # a neon letter: dead paint behind, the tube still burning (animated fire colours)
            X.letter(char, P(r, SIGN_F + 0.06, z), size, font, mat.sign_paint(colour, wear=0.5, seed=41), depth=0.05)
            tube = X.letter(char, P(r, SIGN_F + 0.14, z), size, font, mat.emitter((1.0, 0.22, 0.04), 2.2 if frame != 2 else 1.2),
                            outline=0.028)
            geo.set_fx(tube, "fire")
            continue
        X.letter(char, P(r, SIGN_F + 0.07, z), size, font, mat.sign_paint(colour, wear=0.3, seed=40 + len(char) + int(abs(r) * 10)),
                 roll=roll, depth=0.07)
        if char == "M":
            # a two-tone letter: the dark shadow of an older coat of paint shows round the red
            X.letter(char, P(r + 0.04, SIGN_F + 0.045, z - 0.035), size, font, mat.sign_paint((0.05, 0.035, 0.03), wear=0.1, seed=3), depth=0.04)
            _m_bulbs(r, z, size, lit)
        if char == "N":
            # hanging by one corner from the top rail: a chain where the second bolt used to be
            geo.cable(P(r - 0.30, SIGN_F + 0.04, SIGN_Z1 - 0.18), P(r - 0.36, SIGN_F + 0.07, z + size * 0.96), sag=0.0, radius=0.022)
    # floodlights on outriggers at both top corners, turned onto the lettering
    for side in (-1, 1):
        head = P(side * 3.0, SIGN_F + 0.85, SIGN_Z1 + 0.42)
        geo.pipe([P(side * 2.75, SIGN_F - 0.14, SIGN_Z1 + 0.1), P(side * 2.85, SIGN_F + 0.3, SIGN_Z1 + 0.5), head], 0.035, steel,
                 name="outrigger")
        target = P(side * 1.3, SIGN_F, SIGN_Z0 + 0.5)
        aim = tuple(t - h for t, h in zip(target, head))
        X.floodlight(head, aim, size=0.2, strength=7.0)
        X.spot(head, aim, watts=260.0, angle=95.0)
    # bulbs along the top edge
    geo.bulb_string(P(-2.75, SIGN_F + 0.02, SIGN_Z1 + 0.16), P(2.75, SIGN_F + 0.02, SIGN_Z1 + 0.16), count=11, sag=0.16,
                    radius=0.05, strength=1.8, colours=((1.0, 0.70, 0.30),))
    # the pool of light on the apron in front of the gate
    x, y, _ = P(0.0, 1.9)
    geo.halo((x, y, 0.0), radius=3.0, strength=0.7)
    ghost(structure)


# --------------------------------------------------------------------- leaves
def leaves(opening):
    """The two sliding leaves; opening 0 = shut .. 1 = run back into the bays (0.1 m still showing)."""
    travel = (PASS + 0.02 - 0.10) * opening
    steel = mat.steel(rust=0.55, seed=8)
    stripes = X.hazard(a=(0.85, 0.58, 0.05), uv=True, width=0.42, seed=3.0, wear=0.3)
    for side in (-1, 1):
        inner = side * (0.0 + travel)                     # the meeting edge
        lo = inner if side > 0 else inner - (PASS + 0.02)
        width = PASS + 0.02
        if side < 0:
            face = X.skin(tint=(0.13, 0.25, 0.23), panel=(0.64, 0.7), rust=0.25, grime=0.45, seed=21.0, metallic=0.0)
        else:
            face = X.skin(tint=(0.27, 0.12, 0.07), panel=(0.42, 0.93), rust=0.40, grime=0.5, seed=23.0, metallic=0.0)
        X.plate(width, LEAF_H - 0.62, P(lo, LEAF_F + LEAF_T, 0.66), geo.U, face, thickness=0.04, name="leaf_skin")
        X.plate(width, 0.60, P(lo, LEAF_F + LEAF_T, 0.06), geo.U, stripes, thickness=0.04, name="leaf_stripes",
                uv_offset=(0.0 if side < 0 else 0.21, 0.0))
        # frame: stiles, rails, one diagonal
        for r in (lo + 0.06, lo + width - 0.06):
            geo.box((0.12, 0.07, LEAF_H), P(r, LEAF_F + LEAF_T + 0.03, 0.04), geo.U, steel, bevel=0.01, name="leaf_stile")
        for z in (0.04, 0.66, 1.70, LEAF_H - 0.08):
            geo.box((width, 0.07, 0.11), P(lo + width / 2, LEAF_F + LEAF_T + 0.03, z), geo.U, steel, bevel=0.01, name="leaf_rail")
        a = P(lo + 0.08, LEAF_F + LEAF_T + 0.07, 1.80) if side < 0 else P(lo + width - 0.08, LEAF_F + LEAF_T + 0.07, 1.80)
        b = P(lo + width - 0.08, LEAF_F + LEAF_T + 0.07, 2.64) if side < 0 else P(lo + 0.08, LEAF_F + LEAF_T + 0.07, 2.64)
        geo.pipe([a, b], 0.04, steel, name="leaf_brace")
        # the town's name stencilled across both leaves, low enough to be on screen from the arrival hex
        # even in a 380 px high view (the sign above is not): MEGA | TON, pale paint on the two dark skins
        text, spacing = ("MEGA", 0.94) if side < 0 else ("TON", 1.2)
        middle = inner + side * 0.50                      # of the part of a shut leaf that the gatepost leaves visible
        geo.set_block(geo.lettering(text, P(middle, LEAF_F + LEAF_T + 0.048, 0.82), geo.U, size=LEAF_TEXT, depth=0.012,
                                    bevel=0.0, font="din", spacing=spacing,
                                    material=mat.sign_paint((0.74, 0.71, 0.60), wear=0.35, seed=51 + side), name="leaf_text"), 0.0)
        # hangers up to the rail
        for r in (lo + 0.2, lo + width - 0.2):
            geo.box((0.08, 0.05, 0.16), P(r, LEAF_F + LEAF_T / 2, LEAF_H - 0.02), geo.U, steel, bevel=0.0, name="leaf_hanger")
    # the bar that locks them, on the left leaf
    if opening < 0.5:
        geo.box((0.7, 0.06, 0.09), P(-travel - 0.15, LEAF_F + LEAF_T + 0.09, 1.58), geo.U, X.bright_metal((0.3, 0.3, 0.31), 0.5),
                bevel=0.01, name="lock_bar")


def _leaves_piece(opening):
    def build(ctx):
        leaves(opening)
        ghost(structure)
    return build


# Grade of the whole gate set (pipeline/convert.py). Stock structures - the car-wreck wall, the guard shack, the
# fence - have far deeper darks and less colour than a raw render: a quarter of their pixels are near black
# (Oklab L < 0.2) against a twentieth of ours, and their mean chroma is 0.02-0.03 against 0.04. More contrast and no
# saturation boost bring the set to the same range, so it stops looking pasted onto the wall next to them.
GRADE = {"contrast": 1.42, "saturation": 1.0}

GATE_DESC = "The gate of Megaton: a wing off some airliner for a lintel, its engine still hanging there to haul the leaves."

piece("mg_gate", title="Megaton Gate", desc=GATE_DESC, footprint=FOOTPRINT, overhang=2.6, see_through="u",
      shadow="flat", convert=GRADE)(structure)

piece("mg_gate_sign", title="Megaton Sign", desc="Seven letters off seven dead signs. Together they still spell a town.",
      footprint=[], anchors=[(0, 2)], shadow="none", light=(8, 100), light_hex=(0, 2), frames=4, fps=3,
      convert={"contrast": 1.3})(sign)

LEAF_DESC = "Two slabs of scrap on a rail. When the engine above them turns, they move."
# mg_gate_door is the art slot of the animated door FRM: the pipeline renders it shut, and
# pieces/gate/gate_door.py then replaces its FRM with the frames shut .. open (same size and shift).
# mg_gate_f25 / _f75 are in-between frames for that FRM only: never `build.py add` them.
for _name, _opening in (("mg_gate_shut", 0.0), ("mg_gate_ajar", 0.5), ("mg_gate_open", 1.0), ("mg_gate_door", 0.0),
                        ("mg_gate_f25", 0.25), ("mg_gate_f75", 0.75)):
    piece(_name, title="Megaton Gate", desc=LEAF_DESC, footprint=[], anchors=[(0, 1)], shadow="none", see_through="u",
          convert=GRADE)(
        _leaves_piece(_opening))
