# SPDX-License-Identifier: MIT
"""Rooftop silhouettes, second half: a dish, the church's atom, a hoist, a tail fin, washing, a flag, vents, two signs.

    python3 mod/megaton-art/build.py preview pieces/roofs_skyline2.py [NAME]
    python3 mod/megaton-art/build.py add pieces/roofs_skyline2.py

Placing them: exactly as pieces/roofs_skyline.py says (origin on row hy_lo - 3 behind a building, feet on the
piece's row 1; the roof hides the lowest 2.6 m).

    rf_dish           a radio dish two metres across on a pedestal, looking at the sky    foot (0,1)
    rf_atom           the Children of Atom's sign in scrap tube; its electrons glow green   foot (0,1)
    rf_hoist          a gin pole with a jib and a chain: an engine hangs over the roof     foot (0,1)
    rf_tail_fin       an airliner's fin set up as a wind-break, its number still on it     feet (0,1) (2,1)
    rf_laundry        two poles and two lines of washing high over the roof                feet (0,1) (4,1)
    rf_flag           a tall pole and a banner: white star on dark blue (the sheriff's)    foot (0,1)
    rf_vents          a swan-neck duct, a louvred box and a mushroom, strapped together    feet (0,1) (2,1)
    rf_sign_supply    SUPPLY on a scaffold, an arrow down (Craterside)                     feet (0,1) (4,1)
    rf_sign_beds      BEDS on a scaffold, a moon beside it (the common house)              feet (0,1) (4,1)
"""
import math

from kit import piece, geo, mat, G
from kit import signs_extra as sx
from kit import gate_extra as gx
from kit import bomb_extra as bx
from kit import roofs_extra as rx

ROOF = G.WALL_H
CONV = {"exposure": 0.25, "contrast": 1.22}
B = G.hex_xy(2, 1)[0] - G.hex_xy(0, 1)[0]


def frame_at(dhx=0.0, rot=geo.U):
    x0, y = G.hex_xy(0, 1)
    return sx.Frame((x0 + B * dhx / 2.0, y, 0.0), rot)


def wire():
    return mat.flat((0.03, 0.03, 0.03), roughness=0.6)


def guys(f, z, reach=1.15, d=0.22, radius=0.012, u=0.0):
    for side in (-1.0, 1.0):
        geo.pipe([f.at(u, 0.03, z), f.at(u + side * reach, d, ROOF + 0.02)], radius, wire(), name="guy")


# -------------------------------------------------------------------------------- dish
@piece("rf_dish", title="Radio Dish",
       desc="A dish two metres across, patched with flattened tins, pointed at a piece of sky that has had nothing to say for "
            "two centuries.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert={"exposure": 0.3, "contrast": 1.25})
def rf_dish(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.65, seed=6)
    geo.pipe([f.at(0.0, 0.0, 0.0), f.at(0.0, 0.0, 3.4)], 0.09, mat.painted_metal((0.14, 0.15, 0.14), flaking=0.5, seed=3), name="pedestal")
    geo.box((0.5, 0.5, 0.12), f.at(0.0, 0.0, 0.0), f.rot, mat.concrete(seed=3), bevel=0.02, name="pad")
    for a, b in ((-0.5, 0.0), (0.5, 0.0)):
        geo.pipe([f.at(a, b, ROOF - 0.6), f.at(0.0, 0.0, 3.2)], 0.03, steel, name="strut")
    # the yoke and the dish: axis tipped up and to the screen left
    centre = f.at(-0.05, 0.25, 3.98)          # the whole dish stays under 5 m: behind the empty house the next roof begins there
    geo.box((0.5, 0.3, 0.5), f.at(0.0, 0.05, 3.33), f.rot, steel, bevel=0.03, name="mount")
    radius = 1.12
    skin_a = mat.painted_metal((0.24, 0.24, 0.22), flaking=0.4, seed=5)
    profile = [(0.0, 0.0), (0.3, 0.025), (0.6, 0.095), (0.9, 0.21), (radius, 0.33), (radius - 0.03, 0.34), (0.88, 0.235), (0.6, 0.12),
               (0.3, 0.05), (0.0, 0.03)]
    tilt, roll = 44.0, 40.0
    dish = geo.lathe(profile, centre, skin_a, 28, geo.SCREEN, tilt, roll, name="dish")
    # ribs, a rim hoop, three odd panels (flattened tins riveted over holes) - all in the dish's own frame
    m = dish.matrix_world.copy()
    import bpy
    bpy.context.view_layer.update()
    m = dish.matrix_world.copy()

    def on(r, a_deg, lift=0.0):
        a = math.radians(a_deg)
        z = 0.33 * (r / radius) ** 2 + lift
        return tuple(m @ __import__("mathutils").Vector((r * math.cos(a), r * math.sin(a), z)))
    rib = mat.steel(rust=0.5, seed=2)
    for k in range(8):
        geo.pipe([on(0.12, 45.0 * k, 0.045), on(0.6, 45.0 * k, 0.045), on(radius - 0.02, 45.0 * k, 0.04)], 0.016, rib, name="rib")
    geo.pipe([on(radius, 360.0 * i / 28, 0.012) for i in range(29)], 0.024, rib, name="rim")
    odd = (mat.painted_metal((0.26, 0.07, 0.04), flaking=0.5, seed=7), mat.steel(rust=0.9, seed=8),
           mat.painted_metal((0.08, 0.13, 0.17), flaking=0.5, seed=9))
    for k, (r0, r1, a0, a1) in enumerate(((0.45, 0.95, 95.0, 133.0), (0.25, 0.7, 230.0, 268.0), (0.6, 1.05, 318.0, 350.0))):
        import bmesh
        bm = bmesh.new()
        pts = [on(r0, a0, 0.03), on(r1, a0, 0.03), on(r1, (a0 + a1) / 2, 0.03), on(r1, a1, 0.03), on(r0, a1, 0.03), on(r0, (a0 + a1) / 2, 0.03)]
        bm.faces.new([bm.verts.new(p) for p in pts])
        geo._finish(bm, "tin_patch", odd[k], (0, 0, 0), 0.0, "main", smooth=False, solidify=0.012)
    # the feed: three struts to a can at the focus, a cable back down the pedestal
    focus = on(0.0, 0.0, 1.0)
    for k in range(3):
        geo.pipe([on(radius - 0.05, 90.0 + 120.0 * k, 0.02), focus], 0.018, rib, name="feed_strut")
    geo.lathe([(0.0, -0.1), (0.1, -0.1), (0.1, 0.12), (0.0, 0.12)], focus, mat.painted_metal((0.30, 0.22, 0.05), flaking=0.4, seed=4), 10,
              geo.SCREEN, tilt, roll, name="feed")
    geo.cable(focus, f.at(0.12, 0.1, 3.25), sag=0.25, radius=0.016, material=wire())
    geo.cable(f.at(0.12, 0.1, 3.25), f.at(0.1, 0.1, 0.3), sag=0.0, radius=0.016, material=wire())
    guys(f, 3.25, reach=1.2)


# -------------------------------------------------------------------------------- atom
@piece("rf_atom", title="Atom of the Children",
       desc="Three hoops of bent conduit round a float from a cistern, wired to a pole: the sign of the Children of Atom. "
            "The lamps on its orbits burn green all night.",
       # it blocks nothing: its post stands on the edge of the lane behind the church (kept free by the town), hidden
       # behind the roof; the sign itself hangs 3 m up
       footprint=[], anchors=[(0, 1)], shadow="none", convert={"exposure": 0.3, "contrast": 1.25, "saturation": 1.1})
def rf_atom(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.6, seed=4)
    # the sign hangs out to the screen LEFT of its post on a cranked arm, and no higher than 5.5 m: behind the
    # church the only open sky is the gap between Craterside's roof (right) and the saloon's (left)
    off, cz = -0.8, 4.2
    g = sx.Frame(f.at(off, 0.12, 0.0), geo.SCREEN)
    sx.lattice_post(f, 0.0, 3.3, width=0.3, chord=0.04, lacing=0.022, material=steel, bay=0.45)
    geo.pipe([f.at(0.0, 0.0, 3.2), f.at(-0.25, 0.04, 3.55), g.at(0.0, -0.04, cz - 0.35), g.at(0.0, -0.04, cz)], 0.05, steel, name="arm")
    geo.pipe([f.at(0.0, 0.0, 2.75), g.at(0.0, -0.04, cz - 0.5)], 0.028, steel, name="arm_brace")
    yellow = sx.enamel((0.50, 0.38, 0.05), chips=0.35, seed=3)
    for k, spin in enumerate((0.0, 60.0, 120.0)):
        sx.ring((0.0, cz), 1.22, 0.45, g.moved(d=0.03 * k), yellow, tube=0.05, spin=spin, count=30)
    sx.sphere(0.3, g.at(0.0, 0.05, cz), mat.painted_metal((0.36, 0.10, 0.03), flaking=0.45, seed=6), name="nucleus")
    geo.pipe([g.at(-0.31 * math.cos(t), 0.05 + 0.0, cz + 0.31 * math.sin(t) * 0.25) for t in [math.pi * i / 10 for i in range(11)]], 0.025,
             yellow, name="nucleus_band")
    for k, spin in enumerate((0.0, 60.0, 120.0)):                        # an electron lamp at one end of every orbit
        a = math.radians(spin + (0.0 if k != 1 else 180.0))
        p = g.at(1.22 * math.cos(a), 0.03 * k + 0.02, cz + 1.22 * math.sin(a))
        geo.bulb(p, (0.3, 1.0, 0.25), 0.105, 2.0, fx="slime")
        q = g.at(1.22 * math.cos(a), 0.03 * k - 0.09, cz + 1.22 * math.sin(a))
        sx.sphere(0.12, q, steel, name="lamp_cup", squash=0.9)
    for u, z in ((-0.55, cz - 0.42), (0.55, cz - 0.42)):                 # wire ties so that it does not turn in the wind
        geo.pipe([g.at(u, 0.0, z), f.at(0.0, 0.0, 3.25)], 0.014, wire(), name="tie")
    sx.cloth(f.moved(d=0.05), 0.0, 3.3, 0.5, 0.6, bx.cloth_mat((0.40, 0.09, 0.05), seed=3), folds=1.5, depth=0.04, seed=2, taper=0.2)
    guys(f, 3.2, reach=1.2)


# ------------------------------------------------------------------------------- hoist
@piece("rf_hoist", title="Gin Pole",
       desc="A gin pole and jib with a chain block. The engine on the hook has hung there so long that the chain has rusted "
            "to it.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert=CONV)
def rf_hoist(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.7, seed=7)
    yellow = mat.painted_metal((0.34, 0.24, 0.04), flaking=0.5, seed=4)
    mast = 5.2
    sx.lattice_post(f, 0.0, mast, width=0.4, chord=0.045, lacing=0.026, material=steel, bay=0.5)
    jib_z, reach = 4.35, 2.35
    geo.ibeam(reach + 0.75, f.at(-0.75, 0.05, jib_z), f.rot, yellow, height=0.2, width=0.13)
    geo.pipe([f.at(0.0, 0.05, mast), f.at(reach - 0.1, 0.05, jib_z + 0.2)], 0.022, steel, name="tie_rod")
    geo.pipe([f.at(0.0, 0.05, mast), f.at(-0.7, 0.05, jib_z + 0.2)], 0.022, steel, name="back_stay")
    geo.pipe([f.at(0.0, 0.05, jib_z - 0.9), f.at(0.9, 0.05, jib_z)], 0.03, steel, name="knee")
    # counterweight: a drum of concrete hung on the short end
    geo.pipe([f.at(-0.62, 0.05, jib_z), f.at(-0.62, 0.05, jib_z - 0.5)], 0.02, steel, name="hanger")
    geo.barrel(f.at(-0.62, 0.05, jib_z - 1.25), radius=0.27, height=0.78, material=mat.painted_metal((0.10, 0.045, 0.02), flaking=0.7, seed=3))
    # trolley, chain block, hook and the load: an engine block
    u = 1.75
    geo.box((0.34, 0.2, 0.16), f.at(u, 0.05, jib_z - 0.16), f.rot, steel, bevel=0.01, name="trolley")
    geo.box((0.24, 0.2, 0.3), f.at(u, 0.05, jib_z - 0.52), f.rot, mat.painted_metal((0.30, 0.05, 0.03), flaking=0.4, seed=5), bevel=0.03,
            name="chain_block")
    chain = mat.steel(rust=0.85, seed=2)
    load_z = 3.0
    geo.pipe([f.at(u, 0.05, jib_z - 0.5), f.at(u, 0.05, load_z + 0.85)], 0.022, chain, name="chain")
    geo.pipe([f.at(u - 0.12, 0.05, jib_z - 0.5), f.at(u - 0.3, 0.05, 3.5), f.at(u - 0.25, 0.05, ROOF - 0.2)], 0.016, chain, name="hand_chain")
    for du in (-0.3, 0.3):
        geo.pipe([f.at(u, 0.05, load_z + 0.85), f.at(u + du, 0.05, load_z + 0.55)], 0.018, chain, name="sling")
    block = mat.steel(rust=0.6, colour=(0.07, 0.07, 0.075), seed=9)
    geo.box((0.85, 0.5, 0.42), f.at(u, 0.05, load_z + 0.1), f.rot, block, bevel=0.03, name="engine_block")
    geo.box((0.75, 0.34, 0.16), f.at(u, 0.05, load_z + 0.5), f.rot, mat.painted_metal((0.07, 0.12, 0.16), flaking=0.5, seed=6), bevel=0.03,
            name="rocker_cover")
    geo.box((0.6, 0.4, 0.14), f.at(u, 0.05, load_z - 0.03), f.rot, mat.steel(rust=0.9, seed=4), bevel=0.02, name="sump")
    for k in range(4):
        geo.cylinder(0.05, 0.14, f.at(u - 0.27 + 0.18 * k, 0.32, load_z + 0.32), mat.steel(rust=0.9, seed=k), 8, name="exhaust_port", tilt=90.0,
                     rot=f.rot)
    sx.disc(0.2, f.at(u + 0.45, 0.07, load_z + 0.28), f.rot + 90.0, mat.steel(rust=0.5, seed=5), thickness=0.05, name="flywheel")
    guys(f, mast - 0.1, reach=1.3)


# ---------------------------------------------------------------------------- tail fin
@piece("rf_tail_fin", title="Tail Fin",
       desc="The fin of an airliner, stood on end behind the house to break the wind. Its rudder is wired hard over and the "
            "number is still on it.",
       footprint=[(0, 1), (2, 1)], anchors=[(2, 1)], shadow="none", convert=CONV)
def rf_tail_fin(ctx):
    import bpy
    from mathutils import Matrix
    f = frame_at(1)
    steel = mat.steel(rust=0.7, seed=5)
    half = B / 2.0
    for u in (-half, half):
        sx.scaffold_pole(f.at(u, 0.0, 0.0), 3.3, radius=0.05, material=steel)
    geo.pipe([f.at(-half, 0.0, 1.0), f.at(half, 0.0, 2.6)], 0.03, steel, name="brace")
    root_z, span = 2.35, 3.3
    skin = gx.skin(tint=(0.36, 0.37, 0.38), panel=(0.8, 0.55), rust=0.3, grime=0.6, wear=0.4, seed=6, tone=0.4,
                   bands=(("u", 2.05, 2.5, (0.30, 0.045, 0.03)), ("u", 2.58, 2.72, (0.42, 0.40, 0.34)), ("u", 0.0, 0.3, (0.05, 0.05, 0.055))))
    fin = gx.wing(span, chord_root=2.35, chord_tip=1.0, thickness=0.2, sweep=1.05, at=(0, 0, 0), rot=0.0, material=skin, tip_length=0.4,
                  name="fin")
    # stand it up: local X (root -> tip) becomes world up, the chord runs along the row to the screen right
    base = f.at(-1.2, 0.0, root_z)
    fin.matrix_world = (Matrix.Translation(base) @ Matrix.Rotation(math.radians(90.0), 4, "Z")
                        @ Matrix.Rotation(math.radians(-90.0), 4, "Y"))
    # rudder hinge line and the trim tab: dark gaps; the number; a rust run under the root fairing
    dark = mat.flat((0.02, 0.02, 0.022), roughness=0.6)
    geo.pipe([f.at(0.62, 0.11, root_z + 0.05), f.at(0.75, 0.09, root_z + span - 0.5)], 0.02, dark, name="hinge_line")
    geo.pipe([f.at(0.62, 0.11, root_z + 1.2), f.at(1.0, 0.07, root_z + 1.15)], 0.016, dark, name="tab_line")
    sx.letters("N27", f, -0.2, root_z + 0.72, 0.55, font="din", material=mat.sign_paint((0.045, 0.045, 0.05), wear=0.5, seed=3), d=0.135,
               depth=0.02, gap=0.1)
    rx.runs(f, [(-0.7, root_z + 2.0, 0.9), (-0.1, root_z + 2.05, 0.6), (0.45, root_z + 2.0, 1.1), (0.0, root_z + 0.3, 0.5)], d=0.125)
    geo.box((2.5, 0.26, 0.2), f.at(0.0, 0.0, root_z - 0.12), f.rot, mat.steel(rust=0.85, seed=3), bevel=0.02, name="root_frame")
    sx.bolts(f, [(-1.0 + 0.4 * i, root_z - 0.02) for i in range(6)], d=0.14, radius=0.03)
    geo.pipe([f.at(0.3, 0.05, root_z + span - 0.3), f.at(1.6, 0.25, ROOF + 0.05)], 0.012, wire(), name="guy")
    geo.pipe([f.at(-0.2, 0.05, root_z + span - 0.5), f.at(-1.7, 0.25, ROOF + 0.05)], 0.012, wire(), name="guy")


# ----------------------------------------------------------------------------- laundry
@piece("rf_laundry", title="Roof Washing",
       desc="Two lines of washing strung high between scaffold poles, where the dust is thinner.",
       footprint=[(0, 1), (4, 1)], anchors=[(4, 1)], shadow="none", convert={"exposure": 0.3, "contrast": 1.2, "saturation": 1.15})
def rf_laundry(ctx):
    f = frame_at(2)
    steel = mat.steel(rust=0.7, seed=3)
    for u, h in ((-B, 4.5), (B, 4.25)):
        sx.scaffold_pole(f.at(u, 0.0, 0.0), h, radius=0.045, material=steel, lean=(0.0, 0.0))
        geo.pipe([f.at(u - 0.35, 0.0, h - 0.1), f.at(u + 0.35, 0.0, h - 0.12)], 0.03, steel, name="arm")
        geo.pipe([f.at(u, 0.0, h - 0.7), f.at(u + (0.35 if u < 0 else -0.35), 0.0, h - 0.12)], 0.02, steel, name="strut")
    colours = ((0.46, 0.43, 0.37), (0.30, 0.06, 0.045), (0.09, 0.15, 0.24), (0.36, 0.28, 0.09), (0.12, 0.20, 0.10), (0.40, 0.33, 0.25),
               (0.22, 0.10, 0.16))
    k = 0
    for d, z0, sag, items in ((0.12, 4.36, 0.22, ((-1.0, 0.55, 0.85), (-0.35, 0.5, 0.6), (0.3, 0.7, 1.0), (1.0, 0.45, 0.7))),
                              (-0.1, 4.1, 0.3, ((-0.75, 0.6, 0.55), (0.0, 0.42, 0.95), (0.7, 0.75, 0.5)))):
        p0, p1 = f.at(-B, d, z0 + 0.05), f.at(B, d, z0 - 0.15)
        geo.cable(p0, p1, sag=sag, radius=0.014, material=wire())
        for u, width, height in items:
            t = (u + B) / (2.0 * B)
            z = z0 + 0.05 - 0.2 * t - sag * 4.0 * t * (1.0 - t)
            stripes = ((0.40, 0.38, 0.33), 0.09) if k == 2 else None
            sx.cloth(f.moved(d=d), u, z, width, height, sx.fabric(colours[k % len(colours)], stripes=stripes, seed=k), folds=1.5 + 0.5 * (k % 2),
                     depth=0.05, seed=k, taper=0.15 if k % 3 == 0 else 0.0, sway=0.05)
            k += 1
    guys(f, 4.2, reach=0.9, u=-B)
    guys(f, 4.0, reach=0.9, u=B)


# -------------------------------------------------------------------------------- flag
@piece("rf_flag", title="Sheriff's Banner",
       desc="A scaffold pole as tall as the wall with a banner on a yard: a white star on two blues that do not match, "
            "cut from somebody's Sunday dress and somebody else's curtains.",
       footprint=[(0, 1)], anchors=[(0, 1)], shadow="none", convert={"exposure": 0.3, "contrast": 1.22})
def rf_flag(ctx):
    f = frame_at(0)
    steel = mat.steel(rust=0.6, seed=4)
    top = 5.85
    geo.pipe([f.at(0.0, 0.0, 0.0), f.at(0.0, 0.0, 3.2), f.at(0.02, 0.0, top)], 0.05, steel, name="pole")
    geo.cylinder(0.18, 0.1, f.at(0.0, 0.0, 0.0), mat.concrete(seed=2), 12, name="foot")
    geo.cylinder(0.075, 0.07, f.at(0.0, 0.0, 3.15), steel, 10, name="sleeve")
    sx.sphere(0.085, f.at(0.02, 0.0, top + 0.06), sx.brass(tarnish=0.6, seed=2), name="truck")
    yard_z = top - 0.25
    geo.pipe([f.at(-0.1, 0.05, yard_z), f.at(1.45, 0.05, yard_z + 0.06)], 0.028, steel, name="yard")
    geo.pipe([f.at(0.02, 0.05, top), f.at(1.4, 0.05, yard_z + 0.08)], 0.012, wire(), name="lift")
    # two lengths of cloth sewn side by side, not the same blue and not the same length; a brown patch over a tear
    navy = sx.fabric((0.05, 0.075, 0.13), seed=5)
    faded = sx.fabric((0.085, 0.105, 0.135), seed=9)
    sx.cloth(f.moved(d=0.06), 0.40, yard_z - 0.02, 0.66, 1.78, navy, folds=1.0, depth=0.05, seed=4, taper=0.1, sway=0.08, name="banner_a")
    sx.cloth(f.moved(d=0.065), 1.03, yard_z - 0.02, 0.66, 1.52, faded, folds=1.0, depth=0.05, seed=7, taper=0.08, sway=0.1, name="banner_b")
    sx.cloth(f.moved(d=0.11), 1.08, yard_z - 0.95, 0.3, 0.34, sx.fabric((0.22, 0.13, 0.07), seed=3), folds=0.5, depth=0.02, seed=5,
             name="patch")
    sx.star(0.4, f.at(0.72, 0.13, yard_z - 0.75), f.rot, sx.fabric((0.48, 0.46, 0.40), seed=3), relief=0.0, tilt=0.0)
    for z in (yard_z - 1.45, yard_z - 1.6):                                # frayed bottom: two strips of another cloth
        sx.cloth(f.moved(d=0.07), 0.45 + (z - yard_z + 1.6) * 3.0, z, 0.3, 0.32, sx.fabric((0.30, 0.06, 0.045), seed=7), folds=1.0, depth=0.03,
                 seed=6, taper=0.5)
    geo.cable(f.at(0.03, 0.06, top - 0.1), f.at(0.06, 0.08, 1.2), sag=0.0, radius=0.012, material=wire())
    guys(f, 4.6, reach=1.3)


# ------------------------------------------------------------------------------- vents
@piece("rf_vents", title="Vent Stacks",
       desc="A swan-necked duct, a louvred box and a mushroom cap, strapped to each other for company.",
       footprint=[(0, 1), (2, 1)], anchors=[(2, 1)], shadow="none", convert=CONV)
def rf_vents(ctx):
    f = frame_at(1)
    steel = mat.steel(rust=0.75, seed=4)
    half = B / 2.0
    # the swan neck: fat pipe up, over and down again, a bird mesh on its mouth
    duct = mat.painted_metal((0.20, 0.10, 0.04), flaking=0.55, seed=3)
    u = -half
    geo.pipe([f.at(u, 0.0, 0.0), f.at(u, 0.0, 3.85), f.at(u + 0.2, 0.0, 4.25), f.at(u + 0.6, 0.0, 4.35), f.at(u + 0.95, 0.0, 4.15),
              f.at(u + 1.05, 0.0, 3.75)], 0.2, duct, name="swan_neck", resolution=8)
    for z in (1.2, 2.4, 3.6):
        geo.cylinder(0.23, 0.07, f.at(u, 0.0, z), steel, 14, name="flange")
    geo.cylinder(0.21, 0.04, f.at(u + 1.05, 0.0, 3.72), mat.flat((0.012, 0.012, 0.014)), 14, name="mouth")
    geo.cylinder(0.212, 0.62, f.at(u, 0.0, 2.72), mat.painted_metal((0.08, 0.12, 0.15), flaking=0.6, seed=11), 14, name="odd_section")
    rx.runs(f, [(u - 0.08, 3.6, 0.5), (u + 0.1, 3.6, 0.3), (u + 0.02, 2.72, 0.2)], d=0.205, width=0.07)
    # the box: square trunk, louvred head with a tin lid weighted by a brick
    tin = mat.painted_metal((0.17, 0.18, 0.17), flaking=0.5, seed=6)
    v = half
    geo.box((0.5, 0.5, 3.3), f.at(v, 0.0, 0.0), f.rot, tin, bevel=0.012, name="trunk")
    geo.box((0.86, 0.66, 0.74), f.at(v, 0.0, 3.3), f.rot, mat.painted_metal((0.10, 0.13, 0.15), flaking=0.55, seed=8), bevel=0.02, name="head")
    for k in range(4):
        geo.box((0.7, 0.03, 0.09), f.at(v, 0.335, 3.42 + 0.15 * k), f.rot, mat.flat((0.012, 0.012, 0.014)), bevel=0.0, name="louvre", tilt=-20.0)
    geo.box((1.0, 0.8, 0.05), f.at(v, 0.02, 4.05), f.rot + 3.0, mat.corrugated(rust=0.6, seed=5), bevel=0.004, name="lid", tilt=4.0)
    geo.box((0.22, 0.11, 0.07), f.at(v + 0.15, 0.1, 4.11), f.rot + 25.0, mat.painted_metal((0.26, 0.085, 0.045), flaking=0.3, seed=2), bevel=0.01,
            name="brick")
    geo.box((0.3, 0.012, 0.42), f.at(v - 0.1, 0.34, 2.9), f.rot, mat.flat((0.02, 0.016, 0.014)), bevel=0.0, name="grease")
    rx.runs(f, [(v - 0.3, 3.4, 0.5), (v + 0.28, 3.4, 0.7), (v + 0.05, 3.38, 0.35)], d=0.34, width=0.07)
    rx.runs(f, [(v - 0.15, 3.28, 0.5), (v + 0.12, 3.28, 0.32)], d=0.256, width=0.06)
    geo.box((0.3, 0.02, 0.36), f.at(v + 0.06, 0.255, 2.75), f.rot, mat.steel(rust=0.95, seed=6), bevel=0.004, name="patch", roll=-7.0)
    # the mushroom on a thin stack between them, higher than both
    geo.pipe([f.at(0.05, -0.12, 0.0), f.at(0.05, -0.12, 4.75)], 0.07, mat.corrugated(rust=0.45, seed=9), name="thin_stack")
    geo.lathe([(0.07, 0.0), (0.26, 0.03), (0.28, 0.08), (0.2, 0.2), (0.07, 0.26), (0.0, 0.26)], f.at(0.05, -0.12, 4.72),
              mat.painted_metal((0.30, 0.22, 0.05), flaking=0.5, seed=4), 14, name="mushroom")
    for z in (3.0, 3.9):
        geo.pipe([f.at(u, 0.2, z), f.at(0.05, 0.05, z + 0.03), f.at(v - 0.25, 0.26, z)], 0.016, steel, name="strap")
    guys(f, 4.5, reach=1.5, u=0.05, d=0.25)


# ------------------------------------------------------------------------------- signs
def scaffold_sign(text, face, ink, extra=None, seed=0, font="impact", panels=3, patch=None):
    """A sign board on two scaffold poles (feet on (0,1) and (4,1)): returns its frame and the board's box."""
    f = frame_at(2)
    steel = mat.steel(rust=0.7, seed=seed + 3)
    for u, h in ((-B, 5.15), (B, 5.0)):
        sx.scaffold_pole(f.at(u, 0.0, 0.0), h, radius=0.05, material=steel)
    for z in (ROOF + 0.25, 4.95):
        geo.pipe([f.at(-B - 0.15, 0.0, z), f.at(B + 0.15, 0.0, z + 0.03)], 0.032, steel, name="ledger")
    geo.pipe([f.at(-B, 0.0, ROOF - 0.2), f.at(B, 0.0, 3.55)], 0.026, steel, name="brace")
    u0, u1, z0, z1 = -B - 0.45, B + 0.45, 3.45, 4.85
    sx.sheet_panel(f, u0, u1, z0, z1, d=0.09, colour=face, panels=panels, seed=seed, flaking=0.4, patch=patch)
    sx.frame_rim(f, u0, u1, z0, z1, d=0.1, material=steel)
    r = geo.rng(seed)
    rx.runs(f, [(u0 + 0.15 + (u1 - u0 - 0.3) * (k + r.uniform(0.1, 0.9)) / 6.0, z1 - 0.01, r.uniform(0.25, 0.95)) for k in range(6)], d=0.108,
            width=0.07)
    sx.bolts(f, [(u0 + 0.12 + (u1 - u0 - 0.24) * k / 5.0, z) for k in range(6) for z in (z0 + 0.1, z1 - 0.1)], d=0.11, radius=0.03)
    sx.letters(text, f, 0.0 if extra is None else extra, z0 + 0.36, 0.72, font=font, material=sx.enamel(ink, chips=0.3, seed=seed + 1), d=0.115,
               depth=0.03, gap=0.09, jitter=0.02, seed=seed)
    return f, (u0, u1, z0, z1)


@piece("rf_sign_supply", title="Supply Sign",
       desc="SUPPLY, in letters cut from road signs, and an arrow for those who cannot read.",
       footprint=[(0, 1), (4, 1)], anchors=[(4, 1)], shadow="none", convert={"exposure": 0.28, "contrast": 1.2, "saturation": 1.1})
def rf_sign_supply(ctx):
    f, (u0, u1, z0, z1) = scaffold_sign("SUPPLY", rx.TEAL, (0.52, 0.40, 0.05), extra=-0.28, seed=4, patch=(2, (0.06, 0.10, 0.14)))
    yellow = sx.enamel((0.52, 0.40, 0.05), chips=0.35, seed=7)
    sx.arrow(0.9, f.at(u1 - 0.34, 0.125, z0 + 1.2), f.rot, yellow, shaft=0.2, head=0.5, thickness=0.02, spin=-90.0)
    sx.bulbs_on([f.at(u0 + 0.25 + (u1 - u0 - 0.5) * k / 6.0, 0.13, z1 + 0.12) for k in range(7)],
                [(1.0, 0.8, 0.45), None, "fire", (1.0, 0.8, 0.45), None, (1.0, 0.8, 0.45), "fire"], radius=0.06, drop=0.0)
    guys(f, 5.0, reach=0.8, u=-B)
    guys(f, 4.9, reach=0.8, u=B)


@piece("rf_sign_beds", title="Beds Sign",
       desc="BEDS, and a moon cut from a hub cap. The common house charges nothing and the sign says so by saying nothing else.",
       footprint=[(0, 1), (4, 1)], anchors=[(4, 1)], shadow="none", convert={"exposure": 0.28, "contrast": 1.2})
def rf_sign_beds(ctx):
    f, (u0, u1, z0, z1) = scaffold_sign("BEDS", (0.05, 0.05, 0.06), (0.50, 0.48, 0.40), extra=0.38, seed=9, font="rockwell", panels=4,
                                        patch=(0, (0.16, 0.05, 0.03)))
    pale = sx.enamel((0.52, 0.48, 0.32), chips=0.3, seed=5)
    # a crescent: a disc with a dark disc set off-centre on it
    sx.disc(0.46, f.at(u0 + 0.62, 0.12, z0 + 0.7), f.rot, pale, thickness=0.02, name="moon")
    sx.disc(0.4, f.at(u0 + 0.78, 0.14, z0 + 0.78), f.rot, mat.painted_metal((0.16, 0.05, 0.03), flaking=0.2, seed=3), thickness=0.012, name="moon_cut")
    sx.star(0.13, f.at(u0 + 1.02, 0.15, z0 + 1.05), f.rot, pale, relief=0.0)
    sx.gooseneck(f, -0.2, z1 + 0.02, reach=0.4, rise=0.3, lit=False, d0=0.1)
    geo.set_fx(geo.bulb(f.at(-0.2, 0.47, z1 + 0.14), (1.0, 0.6, 0.2), 0.06, 2.5), "fire")
    guys(f, 5.0, reach=0.8, u=-B)
    guys(f, 4.9, reach=0.8, u=B)
