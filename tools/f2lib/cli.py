"""Command line for f2lib (run as ``python3 -m f2lib`` from the tools directory).

    python3 -m f2lib dat2 list    patch000.dat
    python3 -m f2lib dat2 extract patch000.dat out/ 'maps/*.map'
    python3 -m f2lib dat2 pack    mod/megaton/data mod/megaton/patch001.dat
    python3 -m f2lib map info     arvillag            # or a path to a .map file
    python3 -m f2lib map info     mod/x/data/maps/x.map --overlay mod/x/data --validate
    python3 -m f2lib proto        0x02000002          # by PID
    python3 -m f2lib proto        "wooden door"       # name search
    python3 -m f2lib lst art tiles edg5000.frm        # name -> index
    python3 -m f2lib lst proto scenery 2              # index -> name
    python3 -m f2lib lst scripts acklint

Select game data with --game DIR, FALLOUT2_DIR, or the remembered choice.
--base accepts an extracted tree; --overlay adds files with higher precedence.
"""
import argparse
import collections
import os
import sys

from . import dat2, geometry, ids
from .gamefiles import GameFiles
from .gamepath import GamePathError, resolve_game
from .map import ELEVATION_COUNT, MapFile


def _int(text):
    return int(text, 0)


def _hex(value):
    return f"0x{value & 0xFFFFFFFF:08X}"


def _tree(args):
    return GameFiles(base=args.base or resolve_game(args.game), overlay=args.overlay or None)


# ----------------------------------------------------------------------- dat2
def cmd_dat2_list(args):
    with dat2.Dat2(args.archive) as archive:
        total = 0
        for key in archive.order:
            entry = archive.entries[key]
            total += entry.real_size
            print(f"{entry.real_size:10d} {entry.packed_size:10d} {'z' if entry.compressed else '-'} {key}")
        print(f"# {len(archive.order)} entries, {total} bytes unpacked", file=sys.stderr)


def cmd_dat2_extract(args):
    with dat2.Dat2(args.archive) as archive:
        count = archive.extract(args.outdir, lower=not args.keep_case, globs=args.globs)
    print(f"extracted {count} files to {args.outdir}", file=sys.stderr)


def cmd_dat2_pack(args):
    count = dat2.pack_dir(args.directory, args.archive, compress=not args.store)
    print(f"packed {count} files into {args.archive} ({os.path.getsize(args.archive)} bytes)", file=sys.stderr)


# ------------------------------------------------------------------------ map
def cmd_map_info(args):
    gf = _tree(args)
    if os.path.isfile(args.map):
        with open(args.map, "rb") as f:
            m = MapFile.from_bytes(f.read(), gf)
    else:
        m = MapFile.load(args.map, gf)

    hx, hy = geometry.tile_xy(m.entering_tile)
    print(f"name            {m.name}")
    print(f"version         {m.version}")
    print(f"entering        tile {m.entering_tile} (hx {hx}, hy {hy}), elevation {m.entering_elevation}, "
          f"rotation {m.entering_rotation} ({geometry.DIR_NAMES[m.entering_rotation % 6]})")
    script = "none"
    if m.script_index > 0:
        script = f"{m.script_index} ({gf.scripts.name(m.script_index - 1)}.int)"
    print(f"map script      {script}")
    print(f"flags           {_hex(m.flags)}  elevations with squares: {sorted(m.tiles)}")
    print(f"header index    {m.index}   darkness {m.darkness}   last visit {m.last_visit_time}")
    print(f"variables       {len(m.global_vars)} global, {len(m.local_vars)} local")
    for elevation in sorted(m.tiles):
        squares = m.tiles[elevation]
        floors = int(((squares & 0xFFF) != 1).sum())
        roofs = int((((squares >> 16) & 0xFFF) != 1).sum())
        print(f"elevation {elevation}     {floors} floor squares, {roofs} roof squares")
    for script_type, script_list in enumerate(m.script_lists):
        if script_list.count:
            names = collections.Counter(gf.scripts.name(s.index) or f"#{s.index}" for s in script_list.live())
            listing = ", ".join(f"{name} x{n}" if n > 1 else name for name, n in sorted(names.items()))
            print(f"{ids.SCRIPT_TYPE_NAMES[script_type] + ' scripts':<15} {script_list.count}: {listing}")

    for elevation in range(ELEVATION_COUNT):
        block = m.objects[elevation]
        if not block:
            continue
        by_type = collections.Counter(obj.kind for obj in block)
        nested = sum(1 for obj in m.all_objects(elevation, nested=True)) - len(block)
        summary = ", ".join(f"{n} {kind}" for kind, n in sorted(by_type.items()))
        print(f"objects elev {elevation}  {len(block)} ({summary}); {nested} in inventories")

    used = collections.Counter(obj.pid for obj in m.all_objects(nested=True))
    print(f"\n{len(used)} distinct PIDs:")
    for pid, count in sorted(used.items()):
        name = gf.protos.name(pid) if gf.protos.exists(pid) else "<missing proto>"
        print(f"  {_hex(pid)} {ids.TYPE_NAMES[ids.pid_type(pid)]:<8} x{count:<5} {name or ''}")

    if args.objects:
        print()
        for elevation in range(ELEVATION_COUNT):
            for obj in m.objects[elevation]:
                extra = " ".join(f"{n}={v}" for n, v in zip(obj.data_names, obj.data) if v not in (0, -1))
                print(f"  e{elevation} tile {obj.tile:5d} id {obj.id:5d} {_hex(obj.pid)} fid {_hex(obj.fid)} "
                      f"flags {_hex(obj.flags)} rot {obj.rotation} sid {obj.sid} "
                      f"{gf.protos.name(obj.pid) if gf.protos.exists(obj.pid) else '?'} {extra}")
                for quantity, item in obj.inventory:
                    print(f"       {quantity} x {_hex(item.pid)} {gf.protos.name(item.pid)}")

    if args.validate:
        problems = m.validate()
        print(f"\nvalidate: {len(problems)} problem(s)")
        for problem in problems:
            print("  " + problem)
        return 1 if any(p.startswith("error") for p in problems) else 0
    return 0


# ---------------------------------------------------------------------- proto
def _print_proto(gf, pid):
    proto = gf.protos.get(pid)
    kind = proto.kind + (f" / {proto.subtype_name}" if proto.subtype_name else "")
    print(f"{_hex(pid)}  {kind}  {gf.protos.path(pid)}")
    print(f"  name         {gf.protos.name(pid)}")
    print(f"  description  {gf.protos.description(pid)}")
    art = gf.art.path(proto.fid)
    print(f"  art          {art}{'' if art and gf.exists(art) else '  (missing)'}")
    for field in proto.fields():
        value = getattr(proto, field)
        if isinstance(value, list):
            print(f"  {field:<18} {value}")
        elif field in ("pid", "fid", "flags", "flags_ext", "inv_fid", "head_fid", "open_flags") or abs(value) > 0xFFFF:
            print(f"  {field:<18} {_hex(value)}  ({value})")
        else:
            print(f"  {field:<18} {value}")


def cmd_proto(args):
    gf = _tree(args)
    obj_type = ids.TYPE_NAMES.index(args.type) if args.type else None
    try:
        pid = _int(args.query)
    except ValueError:
        pid = None
    if pid is not None:
        if not gf.protos.exists(pid):
            print(f"no prototype {_hex(pid)}", file=sys.stderr)
            return 1
        _print_proto(gf, pid)
        return 0
    found = gf.protos.search(args.query, obj_type)
    for pid, name in found:
        proto = gf.protos.get(pid)
        kind = proto.kind + (f"/{proto.subtype_name}" if proto.subtype_name else "")
        print(f"{_hex(pid)} {kind:<18} {name}")
    print(f"# {len(found)} match(es)", file=sys.stderr)
    return 0 if found else 1


# ------------------------------------------------------------------------ lst
def cmd_lst(args):
    gf = _tree(args)
    if args.kind == "scripts":
        query = args.type_or_query if args.query is None else args.query
        scripts = gf.scripts
        if query is None:
            for i, entry in enumerate(scripts.entries):
                print(f"{i:5d} {entry.name}.int  local_vars={entry.local_vars}")
            return 0
        try:
            index = _int(query)
        except ValueError:
            index = scripts.find(query)
            if index is None:
                print(f"{query} is not in scripts.lst", file=sys.stderr)
                return 1
        entry = scripts.entries[index]
        print(f"{entry.name}.int  index {index} (0-based: Script.index, proto sid)  "
              f"{index + 1} (1-based: map header, script source)  local_vars={entry.local_vars}")
        return 0

    if args.type_or_query not in ids.TYPE_DIRS and args.type_or_query not in ids.TYPE_NAMES:
        print(f"unknown type {args.type_or_query!r}; one of {', '.join(ids.TYPE_DIRS)}", file=sys.stderr)
        return 2
    names = ids.TYPE_DIRS if args.type_or_query in ids.TYPE_DIRS else ids.TYPE_NAMES
    obj_type = names.index(args.type_or_query)
    listing = gf.art_list(obj_type) if args.kind == "art" else gf.proto_list(obj_type)
    make = ids.make_fid if args.kind == "art" else ids.make_pid
    label = "FID" if args.kind == "art" else "PID"
    if args.query is None:
        for index in listing.indices():
            print(f"{index:5d} {_hex(make(obj_type, index))} {listing.name(index)}")
        return 0
    try:
        index = _int(args.query)
        name = listing.name(index)
        if name is None:
            print(f"index {index} is outside the list ({listing.base}..{listing.next_index - 1})", file=sys.stderr)
            return 1
    except ValueError:
        index = listing.find(args.query)
        if index is None:
            print(f"{args.query} is not in the list", file=sys.stderr)
            return 1
        name = listing.name(index)
    print(f"{name}  index {index} ({listing.base}-based)  {label} {_hex(make(obj_type, index))}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="python3 -m f2lib", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="extracted game tree")
    parser.add_argument("--game", help="your Fallout 2 installation or extracted tree")
    parser.add_argument("--overlay", action="append", help="mod directory searched first (repeatable)")
    commands = parser.add_subparsers(dest="command", required=True)

    dat = commands.add_parser("dat2", help="DAT2 archives").add_subparsers(dest="action", required=True)
    p = dat.add_parser("list", help="list members")
    p.add_argument("archive")
    p.set_defaults(run=cmd_dat2_list)
    p = dat.add_parser("extract", help="extract members (lower-cased paths)")
    p.add_argument("archive")
    p.add_argument("outdir")
    p.add_argument("globs", nargs="*", help="lower-case globs such as 'maps/*.map'")
    p.add_argument("--keep-case", action="store_true", help="keep the stored path case")
    p.set_defaults(run=cmd_dat2_extract)
    p = dat.add_parser("pack", help="pack a directory into an archive")
    p.add_argument("directory")
    p.add_argument("archive")
    p.add_argument("--store", action="store_true", help="do not compress")
    p.set_defaults(run=cmd_dat2_pack)

    maps = commands.add_parser("map", help="map files").add_subparsers(dest="action", required=True)
    p = maps.add_parser("info", help="header, counts and used prototypes")
    p.add_argument("map", help="map name in the game tree (arvillag) or a file path")
    p.add_argument("--objects", action="store_true", help="list every object")
    p.add_argument("--validate", action="store_true", help="run MapFile.validate()")
    p.set_defaults(run=cmd_map_info)

    p = commands.add_parser("proto", help="prototype by PID, or search by name")
    p.add_argument("query", help="PID (0x02000002) or part of a name")
    p.add_argument("--type", choices=ids.TYPE_NAMES[:ids.PROTO_TYPE_COUNT], help="limit a name search")
    p.set_defaults(run=cmd_proto)

    p = commands.add_parser("lst", help="list lookups: art <type> | proto <type> | scripts")
    p.add_argument("kind", choices=("art", "proto", "scripts"))
    p.add_argument("type_or_query", nargs="?", help="object type (tiles, scenery, ...) for art/proto; query for scripts")
    p.add_argument("query", nargs="?", help="index or name; omit to print the whole list")
    p.set_defaults(run=cmd_lst)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "lst" and args.kind != "scripts" and args.type_or_query is None:
        build_parser().error("lst art/proto needs an object type")
    try:
        return args.run(args) or 0
    except GamePathError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
