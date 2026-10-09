"""``data/maps.txt``: the map table (index -> file name, music, save rules).

Parsed by wmMapInit (worldmap.cc:2595-2757) through the engine's generic
config reader: ``[Map NNN]`` sections numbered without gaps from 000 (the
list ends at the first section without `lookup_name`), ``key=value`` lines,
``;`` starts a comment anywhere on a line. A `.map` file finds its index by
matching its header name against `map_name`. Indices above 159 overflow the
automap tables; vanilla uses 0..150.

The file lives in patch000.dat, so a changed copy only takes effect from a
higher-numbered patch archive, never as a loose file (research/07 section 2).
"""

AUTOMAP_MAP_COUNT = 160
LINE_MAX = 255


def parse_config(data):
    """Engine-style config parse -> {section: {key: value}} with lower-cased section and key names."""
    config = {}
    section = "unknown"
    for raw in data.decode("latin-1").split("\n"):
        line = raw.split(";", 1)[0].strip()
        if line.startswith("["):
            end = line.find("]", 1)
            if end >= 0:
                section = line[1:end].strip().lower()
                continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        config.setdefault(section, {})[key.strip().lower()] = value.strip()
    return config


def maps(data):
    """[{key: value}] for Map 000, 001, ... up to the first gap."""
    config = parse_config(data)
    table = []
    while True:
        section = config.get("map %03d" % len(table))
        if section is None or "lookup_name" not in section:
            return table
        table.append(section)


def map_names(data):
    """Lower-cased `map_name` of every map, by index."""
    return [section.get("map_name", "").lower() for section in maps(data)]


def _format(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ",".join(_format(v) for v in value)
    return str(value)


def append_map(data, lookup_name, map_name, **options):
    """Return (new file bytes, index) with one more ``[Map NNN]`` section.

    lookup_name  name city.txt / worldmap.txt refer to (max 39 characters, no commas)
    map_name     file base name (max 8 characters)
    options      further keys in order, e.g. music="07desert", saved=True,
                 dead_bodies_age=True, can_rest_here=(True, False, False),
                 automap=True, ambient_sfx="gustwind:20, rattle:15".
                 Booleans become Yes/No; any other yes/no token makes the
                 engine refuse to start.
    """
    index = len(maps(data))
    if index >= AUTOMAP_MAP_COUNT:
        raise ValueError(f"maps.txt already has {index} maps; the automap tables hold {AUTOMAP_MAP_COUNT}")
    if not lookup_name or len(lookup_name) > 39 or "," in lookup_name or ";" in lookup_name:
        raise ValueError("lookup_name must be 1..39 characters without ',' or ';'")
    if not map_name or len(map_name) > 8 or "." in map_name:
        raise ValueError("map_name must be 1..8 characters without extension")
    if map_name.lower() in map_names(data):
        raise ValueError(f"map_name {map_name!r} is already registered")
    lines = ["[Map %03d]" % index, f"lookup_name={lookup_name}", f"map_name={map_name.lower()}"]
    lines += [f"{key}={_format(value)}" for key, value in options.items()]
    for line in lines:
        if len(line) > LINE_MAX:
            raise ValueError(f"maps.txt line longer than {LINE_MAX} characters: {line[:40]}...")
    out = bytearray(data)
    if out and not out.endswith(b"\n"):
        out += b"\r\n"
    out += b"\r\n" + "\r\n".join(lines).encode("latin-1") + b"\r\n"
    return bytes(out), index
