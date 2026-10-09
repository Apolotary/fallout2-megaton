# Notices

## Fallout 2 Community Edition

This project contains modified code derived from
[Fallout 2 Community Edition](https://github.com/alexbatalov/fallout2-ce), read at
commit `e97087b9582f37075db347a89898887320753f8b`. That author's Sustainable Use
License 1.0 is reproduced unchanged in [LICENSE-fallout2-ce.md](LICENSE-fallout2-ce.md).
The derived portions remain licensed by their upstream author under those terms;
the project does not relicense them.

The derived portions were modified: routines were ported from C++ to Python,
shortened and rearranged. Knowledge of formats and game rules throughout `tools/`
and `mod/` comes from reading the engine source. Examples include hex geometry in
`tools/f2lib/geometry.py`, palette behavior in `tools/f2lib/pal.py`, and map, sprite
and prototype formats in `tools/f2lib/map.py`, `frm.py` and `pro.py`. This is not a
complete inventory of derived portions. Existing source citations are retained
outside the specifically audited Blender boundary.

`mod/scripts_src/headers/fo2.h`: values and behaviour are taken from fallout2-ce's
source. Identifier names follow the conventional names of Fallout 2 script headers,
so that scripts stay portable.

## Project code and the Blender boundary

Copyright (c) 2026 Apolotary. The project's own code is offered under the
[Sustainable Use License 1.0](LICENSE), except for the owned Blender-executed
components marked with `SPDX-License-Identifier: MIT` and identified by the
exact list in [docs/blender-boundary.json](docs/blender-boundary.json). Those
components use [LICENSE-MIT](LICENSE-MIT).

The audited set contains 52 files: the 12 modules in `mod/megaton-art/kit/`, the 28
manifest-selected piece modules in `pieces/`, the 5 selected sheet modules in
`sheets/`, and exactly these 7 `pipeline/` modules: `__init__.py`, `blender_piece.py`,
`blender_sheet.py`, `bscene.py`, `calibrate_scene.py`, `proj.py`, `tilegeo.py`.
`pieces/gate/gate_door.py`, the ordinary Python builder/placement code and every
other pipeline module are outside this MIT set. The exact list takes precedence
over broad folder descriptions.

Blender's Python API and combined-work terms remain Blender's own terms. MIT is
a GPL-compatible license for the independently owned components; it does not
relicense Blender or copied third-party code. The renderer boundary and geometric
derivation are documented in [docs/blender-boundary.md](docs/blender-boundary.md).
The art/writing terms are separately stated in [LICENSE-CONTENT.md](LICENSE-CONTENT.md).

## Compiler provenance

The [sslc compiler](https://github.com/sfall-team/sslc), sfall-team revision
`3991207639c133bd14948fae6c18df59310b5287`, is not included. Opcode and function
names in `tools/intfile.py` follow sslc's headers and fallout2-ce's interpreter
sources. The existing comments identify those tables.

No compiler-wide license grant was found in the inspected pinned source. Its
MCPP component has its own two-clause notice; that does not license the rest of
the compiler. Emscripten package metadata marked `UNLICENSED` is not the
public-domain Unlicense. These findings do not assert that no permission could
exist elsewhere. The project neither vendors that compiler nor assigns it the
project's license.

## Fonts, artwork and game rights

Scenery was rendered with Blender. Sign lettering requests locally installed
macOS fonts: Impact, Arial Black, DIN Condensed, Rockwell, Brush Script MT,
Marker Felt, Arial Rounded MT Bold and Georgia Bold. The loader can fall back to
Blender's built-in font; source requests alone do not establish every historical
render's resolved face. No font software is included or licensed by this project.

The applicable macOS font clause permits display and printing while using the
licensed system and treats font embedding separately. It does not expressly name
redistributed game sprites. These notices record the rendering dependencies;
they do not claim an unlimited font redistribution permission or that every
third-party right has been cleared. Primary-source readings are summarized in
[docs/licence-reading-notes.md](docs/licence-reading-notes.md).

Fallout game archives, stock asset files, saves and music are excluded. The two
README screenshots depict Fallout 2 game UI and artwork; that third-party material
is not covered by the project's code or content licenses. This is an unofficial
fan project, unaffiliated with the rights holders. Fallout, Fallout 2, Fallout 3
and their characters, places, marks and other protected material remain their owners'.
