# Blender execution boundary and projection provenance

The exact Python import closure is listed in `blender-boundary.json`. It includes
scripts dynamically loaded from the art manifest as well as their local imports;
a search for `import bpy` alone is insufficient. `kit/town.py` reads locally
prepared geometry data and does not import the town/game builder. Game-derived
snapshot folders are excluded from the source distribution.

The integer hex projection in `pipeline/proj.py` is expressed from its documented
step table. Two horizontal steps total(-48,+12)pixels; an odd leftover step is
(-32,0); a vertical step contributes(+16,+12). For a signed horizontal offset,
`pairs, odd = divmod(dhx, 2)` preserves parity correctly in both directions. The
result is `(-48*pairs-32*odd+16*dhy,12*(pairs+dhy))`.

The prior expression was compared in memory against this form for all 14,641 pairs
in the range -60..60 on both axes and large signed offsets. The transformation
checks exact equality; it does not claim a new Blender render or calibration run.
Cached-render calibration remains a separate release check.

Three earlier implementation comments referenced engine source locations:
`object.cc` redraw bounds, `map.cc` roof paint order, and `tile.cc` tile geometry
and roof height. Those describe the technical behavior that the renderer matches.
The source audit did not identify copied executable routines for the reach
budgets, paint-order note or measured tile mask. This provenance remains recorded
here after the MIT script comments are phrased as geometric/observed facts. The
integer hex routine above was replaced through the separate step-table derivation.
Removing a citation alone is not treated as a license conversion.

`tilegeo.STOCK_ROWS` is a measured technical tile mask, not colored game pixels
presented as original art. Stock-backed rendered composites remain excluded by
the separate sprite export audit. Ordinary Python engine-format/geometry ports
and their original citations remain outside the MIT boundary.
