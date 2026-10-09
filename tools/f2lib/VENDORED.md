# File-format library provenance

This is a vendored snapshot of the project's shared `tools/f2lib` library,
exported on 2026-10-09 for the first-person viewer. It is maintained as source in
this repository; no installed package or network fetch is required to use it.

The library reads Fallout 2 archives, maps, prototypes, sprite frames, palettes,
message tables, and grid coordinates. Release preparation adds portable selection
and local extraction of the user's game data. The library contains no game data.

Its file-format knowledge and several routines derive from fallout2-ce at commit
`e97087b9582f37075db347a89898887320753f8b`; the upstream project is
<https://github.com/alexbatalov/fallout2-ce>.
The Python routines are modified ports, not copies of an upstream Python package.
See the repository's `NOTICE.md` and `LICENSE-fallout2-ce.md` for attribution,
the modification notice, and the Sustainable Use License 1.0.

The library originated in the shared Megaton development tooling. The planned
Megaton release must use the same Python modules as this viewer release. Future
synchronization should compare source files and carry fixes into both copies. Export provenance hashes are retained in the
release records outside the repositories.
