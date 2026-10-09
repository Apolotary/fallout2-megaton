# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""New item prototypes of the Megaton mod (build step `protos`).

build_protos(out_dir) creates every item of registry.ITEMS as a real proto:

    proto/items/00000NNN.pro          cloned from the vanilla proto the registry names
    proto/items/items.lst             the full vanilla list + one line per new item
    text/english/game/pro_item.msg    the full vanilla file + name ({NNN00}) and description ({NNN01})

A PID is the 1-based line of items.lst (vanilla has 531 lines, ours start at 532)
and is stored in maps and saves, so registry.ITEMS is append-only. The message
id follows the vanilla rule pid * 100. No new art is shipped: each item borrows
an inventory picture and a ground picture that already exist (ART below; chosen
by eye from the inventory art of all 531 vanilla items).

What the engine does with these items (checked in the running game, see
tests/foundation/items.txt):
  - Keys are real KEY items (obj_item_subtype == ITEM_TYPE_KEY) with the
    "use on" action, so a key can be used on a door from the hand slot and the
    door's use_obj_on_p_proc sees it. The engine itself never opens anything
    with a key: door scripts test obj_pid(obj_being_used_with) or
    has_item(dude_obj, PID_MG_HOUSE_KEY).
  - The pulse charge also has "use on" (the bomb's use_obj_on_p_proc).
  - The inventory's action menu shows Look / Drop for the papers and Look / Use /
    Drop for the charge and the keys (the engine adds Use for every "use on"
    item). That Use applies the item to the player: "That does nothing." for
    the charge, no reaction at all for a key.
  - Nothing prevents the player from dropping, selling or losing an item, exactly
    as with quest items of the stock game. Scripts must therefore keep the
    STATE in GVARs / MG_F_* flags and treat the item as a token: the house door
    opens for MG_F_HOUSE_OWNED whether or not the key is in the pocket, and a
    dialogue that needs the charge offers a way to get another one. All six
    cost $0, so no merchant pays for them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import registry  # noqa: E402
from f2lib import GameFiles, ids, lst, msg  # noqa: E402

# Action bits of an item proto's flags_ext (proto_types.h): what the interface offers.
USE = 0x0800          # "use" in the inventory menu / hand slot
USE_ON = 0x1000       # hand slot gives a target cursor; the target's use_obj_on_p_proc runs
LOOK = 0x2000
PICK_UP = 0x8000

# Per item: art (inventory picture in art/inven, ground picture in art/items) and the
# fields that differ from the cloned proto. Field names are f2lib.pro's.
ART = {
    #                        inventory        ground          other proto fields
    # A dark sphere with a green read-out: the pulse grenade's picture, fist-sized and pre-War.
    "PID_MG_PULSE_CHARGE": ("grenadeq.frm", "gernade.frm", dict(weight=3, cost=0, size=1, flags_ext=LOOK | PICK_UP | USE_ON,
                                                               power_type_pid=-1, power_type=0, charges=0)),
    # A brass key on a chain.
    "PID_MG_HOUSE_KEY": ("key3.frm", "smalbox2.frm", dict(weight=0, cost=0, size=0, flags_ext=LOOK | PICK_UP | USE_ON)),
    # A folded, much-handled letter.
    "PID_MG_LUCY_LETTER": ("paper2.frm", "smalbox2.frm", dict(weight=0, cost=0, size=0, flags_ext=LOOK | PICK_UP,
                                                              power_type_pid=-1, power_type=0, charges=0)),
    # A sheaf of closely written pages.
    "PID_MG_MOIRA_NOTES": ("docpaper.frm", "smalbox2.frm", dict(weight=0, cost=0, size=0, flags_ext=LOOK | PICK_UP,
                                                                power_type_pid=-1, power_type=0, charges=0)),
    # A small folded note.
    "PID_MG_CONTRACT": ("pwpaper.frm", "smalbox2.frm", dict(weight=0, cost=0, size=0, flags_ext=LOOK | PICK_UP,
                                                            power_type_pid=-1, power_type=0, charges=0)),
    # A heavy steel key on a ring.
    "PID_MG_OFFICE_KEY": ("key.frm", "smalbox2.frm", dict(weight=0, cost=0, size=0, flags_ext=LOOK | PICK_UP | USE_ON)),
}

ITEM_TYPE = ids.OBJ_TYPE_ITEM
INVEN_ART_TYPE = 7      # art/inven
ITEM_SUBTYPE_KEY = 6


def _write(out_dir, rel, data):
    path = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def build_protos(out_dir):
    """Stage the new item protos, items.lst and pro_item.msg under out_dir (game paths)."""
    gf = GameFiles()                                    # vanilla only: the lists are rebuilt from scratch
    names = lst.proto_names(gf.read("proto/items/items.lst"))
    first_pid = len(names) + 1
    new_lines = []
    texts = {}
    for position, (define, pid, title, description, clone) in enumerate(registry.ITEMS):
        if pid != first_pid + position:
            raise SystemExit(f"protos: {define} has PID {pid}, but its place in registry.ITEMS makes it "
                             f"line {first_pid + position} of items.lst (entries are append-only)")
        if define not in ART:
            raise SystemExit(f"protos: {define} has no entry in protos.ART (pictures, weight, cost)")
        inventory_art, ground_art, fields = ART[define]
        proto = gf.protos.get(ids.make_pid(ITEM_TYPE, clone)).copy(
            pid=ids.make_pid(ITEM_TYPE, pid),
            message_id=pid * 100,
            fid=gf.art.fid(ITEM_TYPE, ground_art),
            inv_fid=gf.art.fid(INVEN_ART_TYPE, inventory_art),
            sid=-1,
            **fields)
        if "KEY" in define and proto.sub_type != ITEM_SUBTYPE_KEY:
            raise SystemExit(f"protos: {define} must be cloned from a KEY item (proto {clone} is {proto.subtype_name})")
        file_name = f"{pid:08d}.pro"
        _write(out_dir, f"proto/items/{file_name}", proto.to_bytes())
        new_lines.append(file_name)
        texts[pid * 100] = title
        texts[pid * 100 + 1] = description

    _write(out_dir, "proto/items/items.lst", lst.append_lines(gf.read("proto/items/items.lst"), new_lines))
    _write(out_dir, "text/english/game/pro_item.msg",
           msg.append_entries(gf.read("text/english/game/pro_item.msg"), texts))

    # Read everything back through the overlay, the way the engine will see it.
    check = GameFiles(overlay=out_dir)
    for define, pid, title, description, _ in registry.ITEMS:
        full = ids.make_pid(ITEM_TYPE, pid)
        proto = check.protos.get(full)
        if proto.pid != full or check.protos.name(full) != title or check.protos.description(full) != description:
            raise SystemExit(f"protos: {define} does not read back correctly")
        for fid in (proto.fid, proto.inv_fid):
            if not check.art.exists(fid):
                raise SystemExit(f"protos: {define} uses art 0x{fid:08X}, which does not exist")
    print(f"protos: {len(new_lines)} new items, PIDs {first_pid}..{first_pid + len(new_lines) - 1}")


def item_pids():
    """{define name: PID} of the mod's items, for map builders and cast files."""
    return {define: pid for define, pid, _, _, _ in registry.ITEMS}


if __name__ == "__main__":
    build_protos(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out"))
