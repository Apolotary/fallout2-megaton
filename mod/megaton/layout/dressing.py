# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Set dressing: what makes the bones of layout/ look like a town somebody lives in.

    layout.build() -> decorate() -> dressing.dress(m, gf, info)

runs after walls, doors, roofs and the pool exist and BEFORE the cast is
placed. Interiors are in interiors.py (one function per building), everything
under the sky in outdoors.py; this module is the tool box both use.

How furniture works in this engine (all of it read off the retail maps, see
the numbers in the comments of interiors.py):

  * Only critters, scenery and walls close a hex. Containers are ITEMS and
    never block, so retail maps put a "Secret Blocking Hex" under every
    locker and bookcase, and more of them under anything wider than a hex.
    Dresser.box() and Dresser.prop() do that from the picture itself: every
    hex whose centre lies on the lower band of the sprite (its footprint on
    the ground) is closed - except hexes layout.keep_free() reserves.
  * A sprite belongs to one wall. The same locker exists drawn for a back
    wall (hy_lo) and for a right wall (hx_lo); the camera never sees the
    inside of front and left walls, and those walls hide the four to eight
    rows behind them. So furniture stands along the back and right walls
    and rooms are dressed from the back-right corner outwards.
  * Things on the same hex are drawn in the order they were added, and hexes
    are drawn in tile order (row by row, hx rising). Shelf goods and table
    clutter therefore go on the SAME hex as the shelf or table, after it.
  * Wall-mounted pieces (lamps, posters, signs) are flat scenery that stands
    on the hex in front of the wall, or on the wall's own hex; which one is
    noted where each is used.

Everything placed is recorded in info["dressing"] (containers with their
loot, lights, blocked hexes) for tests/layout/test_layout.py and for
`cd mod/megaton && python3 -m layout.dressing`, which prints the inventory
of the town per place.
"""
from f2lib import geometry as g, ids

from . import kit, plan, spots

SECRET_BLOCK = kit.SECRET_BLOCK          # invisible, closes the hex, lets light and shots pass
PID_LIGHT = 0x0200008D                   # "Light Source": invisible

# scripts/mgdecor.ssl gives these pieces a name and a description, and the locked containers
# a lock that can be picked. It tells them apart by proto: keep the two lists in step with it.
SCRIPT = "mgdecor"
DESCRIBED = {0x02000254, 0x02000255, 0x020003E8, 0x0200005E, 0x02000144, 0x020004CE, 0x0200020E,
             0x0200027A, 0x0200027B, 0x0200027C, 0x0200036D, 0x02000377, 0x020003E3, 0x02000494,
             0x020004A6, 0x02000009, 0x020004A3, 0x02000388, 0x02000236}
STASHES = {188, 128, 185, 502}           # locker, footlocker, steel desk, floor safe


def described():
    """DESCRIBED plus the custom-art pieces that took the place of some of them (layout/art.py)."""
    from . import art

    return DESCRIBED | art.decor_pids()

OBJECT_NO_BLOCK = 0x10
OBJECT_FLAT = 0x08
FULL_LIGHT = 0x10000

AUTO = "auto"


class DressingError(Exception):
    pass


class Dresser:
    """Places dressing on the map and keeps the books.

        d = Dresser(m, gf, info)
        d.at("saloon")                                   # label for what follows
        d.prop(PID_TABLE, 100, 71)                       # scenery; footprint blocked automatically
        d.prop(PID_RUG, 93, 72)                          # flat / walkable scenery blocks nothing
        d.box(PID_LOCKER, 76, 64, [(PID_ROPE, 1)])       # container with loot and its blocker
        d.lamp(PID_LAMP_POST, 96, 110, radius=7)         # scenery that gives light
        d.glow(81, 86, radius=4, percent=60)             # light without a picture
        d.wall(PID_BAR_PIECE, 110, 66)                   # wall-type pieces (bar counters)
        d.critter(PID_BRAHMIN, 77, 134, rotation=2)      # livestock: no script, the animal team
    """

    def __init__(self, m, gf, info):
        from . import keep_free          # late: layout/__init__ imports this module lazily

        import cast

        self.m, self.gf, self.info = m, gf, info
        self.reserved = keep_free()
        self.hard = {h for h, why in self.reserved.items() if not why.startswith(("access", "doorstep"))}
        # Hexes where the cast will put a scripted object: never a blocker there (see close()).
        self.cast_hexes = {cast.spot_position(e["spot"])[:2] for e in cast.load() if e["type"] in ("thing", "attach")}
        self.place = "?"
        self.record = info.setdefault("dressing", {"containers": [], "lights": [], "objects": [],
                                                   "critters": [], "skipped": [], "scripted": []})
        self.script_ready = gf.scripts.find(SCRIPT) is not None and gf.exists(f"scripts/{SCRIPT}.int")
        self._footprints = {}

    # ------------------------------------------------------------------ book-keeping
    def at(self, place):
        self.place = place
        return self

    def name(self, pid):
        return self.gf.protos.name(pid)

    def blocked(self, hx, hy):
        """True if something already closes the hex."""
        for obj in self.m.objects_at(kit.tile(hx, hy)):
            if obj.obj_type in (ids.OBJ_TYPE_SCENERY, ids.OBJ_TYPE_WALL) and not obj.flags & OBJECT_NO_BLOCK:
                if obj.obj_type == ids.OBJ_TYPE_SCENERY and self.gf.protos.get(obj.pid).subtype_name == "door":
                    continue
                return True
        return False

    def scripted(self, obj):
        """Attach mgdecor.ssl (if it is compiled: a build with --only leaves it out, and the
        piece is then plain furniture; a locked container stays shut)."""
        if self.script_ready and obj.sid == -1:
            self.m.attach_script(obj, SCRIPT)
            self.record["scripted"].append((self.place, self.name(obj.pid), g.tile_xy(obj.tile)))
        return obj

    # ------------------------------------------------------------------ footprints
    def footprint(self, pid, hx, frame=0):
        """Hexes (dx, dy) under a sprite standing on a hex of hx's parity, its own hex included.

        A hex counts when its centre lies on the sprite's lower band, where the
        thing meets the floor: for a picture w wide the band is about 0.42 w
        deep (an isometric footprint is twice as wide as it is deep). Checked
        against the blockers the retail maps put around the same art.
        """
        key = (pid, hx & 1, frame)
        if key in self._footprints:
            return self._footprints[key]
        frm = self.gf.art.load(self.gf.protos.get(pid).fid)
        left, top, width, height = frm.placement(0, frame)
        pixels = frm.frame(0, frame).array()
        band = max(14, min(height, int(width * 0.42)))
        base = 100 + (hx & 1)
        cx, cy = g.hex_center(g.tile_at(base, 100))
        cells = {(0, 0)}
        for dx in range(-7, 8):
            for dy in range(-7, 8):
                x, y = g.hex_center(g.tile_at(base + dx, 100 + dy))
                px, py = x - cx - left, y - cy - top
                if 0 <= px < width and height - band <= py < height:
                    patch = pixels[max(0, py - 3):py + 4, max(0, px - 6):px + 7]
                    if patch.size and (patch != 0).mean() > 0.55:
                        cells.add((dx, dy))
        self._footprints[key] = sorted(cells)
        return self._footprints[key]

    def close(self, hx, hy, why=""):
        """Put a secret blocker on a hex unless it is closed already, reserved, or the cast's.

        The blocker loses its FLAT flag. The engine keeps flat objects at the
        head of a hex's object list, and whatever asks for "the object on this
        hex" (the test driver's use / skill commands) gets the head: without
        the flag the blocker stays behind the container it was added after."""
        if (hx, hy) in self.hard:
            self.record["skipped"].append((self.place, hx, hy, why, self.reserved[(hx, hy)]))
            return False
        if (hx, hy) in self.cast_hexes:
            return False
        if not self.blocked(hx, hy):
            kit.put(self.m, SECRET_BLOCK, hx, hy).flags &= ~OBJECT_FLAT
        return True

    def _close_under(self, pid, hx, hy, block, extra, own, frame=0):
        if block == AUTO:
            block = [c for c in self.footprint(pid, hx, frame) if c != (0, 0)]
        cells = list(block or ()) + list(extra or ())
        if own:
            cells.append((0, 0))
        for dx, dy in cells:
            self.close(hx + dx, hy + dy, why=self.name(pid))

    # ------------------------------------------------------------------ placing
    def prop(self, pid, hx, hy, block=AUTO, extra=(), **fields):
        """Scenery. Blocking protos close their footprint (block=None: only their own hex;
        block=[(dx, dy), ...]: exactly those; extra adds to the automatic ones)."""
        proto = self.gf.protos.get(pid)
        if proto.obj_type != ids.OBJ_TYPE_SCENERY:
            raise DressingError(f"{self.place}: 0x{pid:08X} is not scenery")
        solid = not proto.flags & OBJECT_NO_BLOCK
        if solid and (hx, hy) in self.hard:
            raise DressingError(f"{self.place}: {self.name(pid)} on ({hx}, {hy}) blocks a reserved hex: "
                                f"{self.reserved[(hx, hy)]}")
        obj = kit.put(self.m, pid, hx, hy, **fields)
        if solid:
            self._close_under(pid, hx, hy, block, extra, own=False, frame=fields.get("frame", 0))
        elif extra or (block not in (AUTO, None)):
            self._close_under(pid, hx, hy, None if block == AUTO else block, extra, own=False)
        self.record["objects"].append((self.place, self.name(pid), pid, hx, hy))
        if pid in DESCRIBED:
            self.scripted(obj)
        return obj

    def flat(self, pid, hx, hy, **fields):
        """Scenery or wall art that must never close a hex (decals, rugs, wall-mounted pieces)."""
        obj = kit.put(self.m, pid, hx, hy, **fields)
        obj.flags |= OBJECT_NO_BLOCK
        self.record["objects"].append((self.place, self.name(pid), pid, hx, hy))
        if pid in DESCRIBED:
            self.scripted(obj)
        return obj

    def box(self, pid, hx, hy, items=(), locked=False, block=AUTO, extra=(), note="", tag=None):
        """A container (an item) with its loot [(pid, quantity), ...] and the blockers under it.

        tag names the container for engine tests (@TAG in step files, layout.test_names)."""
        proto = self.gf.protos.get(pid)
        if proto.obj_type != ids.OBJ_TYPE_ITEM or proto.subtype_name != "container":
            raise DressingError(f"{self.place}: 0x{pid:08X} is not a container")
        if (hx, hy) in self.hard:
            raise DressingError(f"{self.place}: {self.name(pid)} on ({hx}, {hy}) is on a reserved hex: "
                                f"{self.reserved[(hx, hy)]}")
        obj = kit.put(self.m, pid, hx, hy)
        for item in items:
            self.m.add_item(obj, item[0], quantity=item[1] if len(item) > 1 else 1)
        if locked:
            if pid not in STASHES:
                raise DressingError(f"{self.place}: mgdecor.ssl has no lock for a {self.name(pid)} (dressing.STASHES)")
            self.m.lock(obj)
            self.scripted(obj)
        self._close_under(pid, hx, hy, block, extra, own=True)
        self.record["containers"].append(dict(place=self.place, name=self.name(pid), pid=pid, hex=(hx, hy),
                                              items=[(self.name(i[0]), i[1] if len(i) > 1 else 1) for i in items],
                                              locked=locked, note=note, tag=tag, obj=obj))
        return obj

    def wall(self, pid, hx, hy):
        obj = kit.put(self.m, pid, hx, hy)
        self.record["objects"].append((self.place, self.name(pid), pid, hx, hy))
        return obj

    def lamp(self, pid, hx, hy, radius=6, percent=100, block=AUTO, **fields):
        """Scenery that is a visible source of light."""
        obj = self.prop(pid, hx, hy, block=block, light_distance=radius,
                        light_intensity=FULL_LIGHT * percent // 100, **fields)
        self.record["lights"].append((self.place, self.name(pid), hx, hy, radius, percent))
        return obj

    def glow(self, hx, hy, radius=5, percent=100, what="glow"):
        """Light without a picture of its own (the lamp is painted on something else)."""
        obj = kit.put(self.m, PID_LIGHT, hx, hy, light_distance=radius, light_intensity=FULL_LIGHT * percent // 100)
        self.record["lights"].append((self.place, what, hx, hy, radius, percent))
        return obj

    def critter(self, pid, hx, hy, rotation=0, team=None, ai=None):
        """An unscripted animal. It stands where it is put: critters without a script do not wander."""
        import cast

        if (hx, hy) in self.hard:
            raise DressingError(f"{self.place}: critter on reserved hex ({hx}, {hy})")
        obj = kit.put(self.m, pid, hx, hy, rotation=rotation)
        obj["team"] = cast.CONSTANTS["TEAM_MG_ANIMAL"] if team is None else team
        obj["ai_packet"] = cast.CONSTANTS["AI_MG_ANIMAL"] if ai is None else ai
        self.record["critters"].append((self.place, self.name(pid), hx, hy))
        return obj


def dress(m, gf, info):
    """Entry point (layout.decorate): interiors first, then the streets and the apron.
    layout.decorate() calls seal_pockets() afterwards, once the custom art stands too."""
    from . import interiors, outdoors

    d = Dresser(m, gf, info)
    interiors.dress(d)
    outdoors.dress(d)
    return d


def after_cast(m, gf, info):
    """Called by layout.build() once the cast stands: a blocker under each container the cast
    brought (they are items and close nothing), added after it so the container stays the
    first object of its hex."""
    done = []
    for entry, obj in info.get("placed", ()):
        if entry["type"] == "thing" and getattr(obj, "obj_type", None) == ids.OBJ_TYPE_ITEM:
            kit.put(m, SECRET_BLOCK, *g.tile_xy(obj.tile)).flags &= ~OBJECT_FLAT
            done.append(g.tile_xy(obj.tile))
    info.setdefault("dressing", {})["cast_blockers"] = done
    return done


def close_trim_rows(d):
    """Nobody walks on the row of hexes just BEHIND a building's back wall.

    A shack's roof starts one row behind its back wall (kit.py: the trim row, as on retail maps),
    and the engine takes a roof off as soon as the player's hex lies under one of its squares. So
    whoever walked along the back of the church on his way to Craterside saw the church roof
    vanish as if he had stepped inside, with the Confessor's wife in plain view behind a wall:
    a click on her answered "You cannot get there." A blocker on every free hex of that row keeps
    the lane one hex further off. Reserved hexes (spots, doorsteps, the middle of a path) are left
    alone; the eave rows in FRONT of a building stay open on purpose: at a front door the roof is
    meant to come off. Returns the hexes closed."""
    from . import walk

    blocked, doors, exits = walk.survey(d.m)
    closed = []
    d.at("behind the back walls")
    for shack in d.info["shacks"].values():
        hy = shack.hy_lo - 1
        for hx in range(shack.hx_lo, shack.hx_hi):
            tile = g.tile_at(hx, hy)
            if tile in blocked or tile in doors or tile in exits or (hx, hy) in d.reserved:
                continue
            if any(obj.obj_type == ids.OBJ_TYPE_CRITTER for obj in d.m.objects_at(tile)):
                continue
            kit.put(d.m, SECRET_BLOCK, hx, hy)
            closed.append((hx, hy))
    d.record["trim rows"] = closed
    return closed


def seal_pockets(d):
    """Close the free hexes furniture has cut off from the rest of the town.

    A bed in a corner leaves a hex or two behind it that nobody can reach on
    foot. They are harmless until a script or a knock-back puts somebody
    there for good, so they get a blocker. Returns the hexes closed."""
    from . import walk

    blocked, doors, exits = walk.survey(d.m)
    reach = walk.flood(spots.tile("ENTRY"), blocked, stop=exits)
    sealed = []
    d.at("sealed pockets")
    for hy in range(plan.BACK + 1, plan.EXIT_ROWS[0]):
        for hx in range(plan.RIGHT - 20, plan.LEFT + 21):
            tile = g.tile_at(hx, hy)
            if tile in blocked or tile in reach or tile in doors:
                continue
            if plan.inside_wall(hx, hy) or (plan.APRON_HX[0] <= hx <= plan.APRON_HX[1] and hy > plan.FRONT):
                if (hx, hy) in d.hard:
                    raise DressingError(f"dressing has cut off the reserved hex ({hx}, {hy}): {d.reserved[(hx, hy)]}")
                kit.put(d.m, SECRET_BLOCK, hx, hy)
                sealed.append((hx, hy))
    d.record["sealed"] = sealed
    return sealed


def report(info, out=print):
    """The town's inventory, place by place: what the decorator's report is written from."""
    record = info["dressing"]
    places = []
    for entry in record["objects"]:
        if entry[0] not in places:
            places.append(entry[0])
    for place in places:
        out(f"== {place}")
        counts = {}
        for where, name, pid, hx, hy in record["objects"]:
            if where == place:
                counts[name] = counts.get(name, 0) + 1
        out("   " + ", ".join(f"{name} x{n}" if n > 1 else name for name, n in sorted(counts.items())))
        for box in record["containers"]:
            if box["place"] == place:
                loot = ", ".join(f"{name} x{n}" if n > 1 else name for name, n in box["items"]) or "empty"
                out(f"   [{box['name']} {box['hex']}{' LOCKED' if box['locked'] else ''}] {loot}"
                    + (f"  ({box['note']})" if box["note"] else ""))
        for where, name, hx, hy, radius, percent in record["lights"]:
            if where == place:
                out(f"   light: {name} ({hx}, {hy}) radius {radius}, {percent}%")
        for where, name, hx, hy in record["critters"]:
            if where == place:
                out(f"   critter: {name} ({hx}, {hy})")
    if record["skipped"]:
        out("== blockers left out because the hex is reserved")
        for place, hx, hy, why, reason in record["skipped"]:
            out(f"   {place}: ({hx}, {hy}) under {why}: {reason}")


if __name__ == "__main__":             # cd mod/megaton && python3 -m layout.dressing [staging dir]
    import os
    import sys

    import layout
    from f2lib import GameFiles

    staging = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(layout.HERE), "out-layout")
    _, built = layout.build(GameFiles(overlay=staging), log=lambda *a: None)
    report(built)
