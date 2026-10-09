# Development and testing

Run commands from the repository root with the README's Python environment
activated. The commands below use `python` from that environment. Stop after a
failure and keep its evidence. Run one suite at a time with **one engine
process**; the explicit `--jobs 1` options override higher runner defaults. Keep
any separately managed work within two engine processes in total.

On Unix, `nice -n 15` keeps long jobs at low priority. The verification table
distinguishes completed exported-copy checks from the remaining engine checks.

## Verification status

The following evidence was completed on 2026-10-09 UTC with the tested English
GOG profile on macOS 27.0.1, arm64. Clean exported-copy checks and development
engine gameplay checks are recorded separately. The final committed-repository
clone remains a separate publication check.

| Release check | Current evidence |
| --- | --- |
| Clean exported-copy README setup, build, install and uninstall | PASS: 22 controller steps, including ownership and refusal checks; original game inputs and shipped copy files unchanged |
| Synthetic helper tests | PASS: 103 tests |
| Game-format tests | PASS: 38 tests, 0 failures, 0 skips |
| Dialogue and wording checks | PASS: 1,738 message entries across 40 scripts; 171 source files checked for retired wording |
| Offline layout checks | PASS: all 14 checks, including reachability, doors, clickable objects and reserved walk-under cells |
| Production script write and independent verification | PASS: all 40 scripts freshly compiled from the final 49-file input closure and byte-compared with the accepted production outputs |
| Player and compiler-backed build comparison | PASS: each reproduces the accepted 3,671-member archive byte for byte |
| Final merged-town gameplay and geometry | PASS: 182 cases across eight suite families; 131 retained cases with byte-identical fixture archives and 51 fresh map-dependent cases, including the whole 36-case integration run |
| Final merged-town visual review | PASS: all 96 desktop/phone tour images and ten showcase images opened and reviewed |
| Optional minimal test-engine patch | PASS: fresh compile, native menu smoke and compact core smoke; all 15 arrival/Weld dialogue screenshots reviewed |
| Optional test engine: complete core suite | PASS: 44/44 scenarios, 401/401 assertions, zero debug errors; actual runner exit 0 |
| Unpatched native engine at `e97087b9582f37075db347a89898887320753f8b` | PARTIAL: ordinary new game, direct Megaton gate/sign rendering and save/load passed; manual travel, dialogue and trade unverified |
| Official fallout2-ce v1.3.0 | PASS, STARTUP ONLY: direct Megaton new game, gate/actors/own art rendering and normal UI quit with exit 0 |
| Windows, Linux and case-sensitive filesystem installation | Unverified |

The accepted archive SHA-256 is
`e49fd5e0f8dba757f4fd755644a80f12a7d2c888736067f44189f0ed08347657`.
The archive is generated locally and is not distributed in this repository.

Clean player acceptance used Python 3.14.6, NumPy 2.5.3 and Pillow 12.3.0, without
running Node, Blender or a script compiler. The compiler-backed check used the
exact SSL compiler pin below. The optional test engine used Apple Clang 21.0.0,
CMake 4.1.1 and SDL2 2.32.10 with the pinned engine and fpattern sources described
in [engine/README.md](../engine/README.md). These are observed test versions;
the requirements files do not pin an identical environment on every machine.

The merged-town suite evidence came from the development engine. The separate
optional-engine run used the exported minimal patch and compact core fixtures;
all 401 original assertions were also checked against retained logs, and its
186 checked test/source files matched the staged sources. Its 217 expected
screenshots were present; the 15 arrival/Weld images were individually reviewed.
This is distinct from the merged-town tour review.

Unpatched native checks have narrower coverage. The current-base build reached
the ordinary new-game starting map, rendered a direct Megaton start and sign,
and saved and loaded at the gate. The automation environment could not reliably
control the game's relative cursor, leaving manual world-map travel, walking
through the gate, NPC dialogue and trade unverified. After UI quit in the direct
session, that build's isolated process required termination; clean UI shutdown
for that session was not verified. The official v1.3.0 executable passed direct
Megaton startup/rendering and normal UI shutdown, but was not tested for
save/load, manual travel, dialogue or trade.

A successful command exit alone is insufficient for visual or gameplay acceptance.

## Helper tests

These four suites use synthetic fixtures and do not launch a real game or
compiler. They cover installation ownership and recovery, bytecode provenance,
own-art reconstruction, and the native test runner. Temporary diagnostic fixtures
are retained outside the checkout.

```sh
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

The game-format checks below read your selected game data. Run README setup first.
They are separate from the synthetic helper tests. Archive-specific checks can
skip when setup used only an extracted data tree; record skips rather than
counting them as passes.

```sh
python -B tools/tests/run_all.py
python -B mod/megaton/tests/integration/check_text.py
python -B mod/megaton/tests/foundation/check_wording.py
python -B mod/megaton/tests/layout/run_all.py --offline
```

## Script compiler

Ordinary unchanged player builds can use the 40 committed production scripts.
The prebuilt manifest binds their complete script/header dependency closure,
registry, compile profile and `tools/ssl.py` wrapper. A changed input fails that
check; it does not silently select stale bytecode. Test stages, replacement
scripts, preprocessor defines and partial builds require a compiler.

The external compiler is [sfall-team/sslc](https://github.com/sfall-team/sslc),
tag `2026-09-17-13-26-18`, commit
`3991207639c133bd14948fae6c18df59310b5287`. The project does not distribute it;
see [NOTICE.md](../NOTICE.md#compiler-provenance) for the source-licence findings.
Install Git, Node.js, CMake, make and an activated Emscripten toolchain separately.
`node`, `cmake`, `make`, `emcmake` and `emmake` must be on `PATH`.
All 40 production scripts passed fresh compilation with this pinned compiler in
a separate exported copy on the tested macOS host. Installing and rebuilding the
external compiler toolchain on a fresh machine remains unverified.

Use a clean compiler directory. Preserve an existing `tools/sslc` checkout
elsewhere before following these commands; do not replace local compiler work.
The clone command downloads source when you choose to run it.

```sh
git clone --branch 2026-09-17-13-26-18 --depth 1 https://github.com/sfall-team/sslc.git tools/sslc
git -C tools/sslc checkout --detach 3991207639c133bd14948fae6c18df59310b5287
node --version
python tools/ssl.py setup
python mod/megaton/prebuilt.py verify
```

`tools/ssl.py setup` builds the existing checkout with `emcmake cmake` and
`emmake make`. It does not fetch the compiler. The expected local outputs are
`tools/sslc/build/bin/sslc.mjs` and `sslc.wasm`. Verification checks the exact
checkout and tag, rejects tracked source changes, compiles all 40 scripts freshly
and compares every output byte. It preserves compilation evidence under ignored
`build/` and does not rewrite the committed bundle.

When both compiler files and Node are available, a normal build compiles scripts
and enforces that compiler identity. With no usable compiler, a production build
may copy the verified bundle. A half-installed pair of compiler files is an error;
it is not a way to select the fallback. There is no `setup --compiler` option.

After intentionally changing script sources, a maintainer can regenerate all
prebuilts and build with:

```sh
python megaton.py build --write-prebuilt
```

This preserves the old bundle under ignored `build/prebuilt-history/`. Review the
source and bytecode changes and rerun the relevant gameplay tests before committing.
`python megaton.py build --verify-prebuilt` instead requires the existing bundle
to match a fresh compile before building. The player CLI preserves its prior
build under ignored `game/build-history/` before beginning either operation.

## Native test engine

Playing the mod uses a normal fallout2-ce installation. Automated scenarios also
need the optional test hooks described in [engine/README.md](../engine/README.md).
The minimal patch targets exactly
`e97087b9582f37075db347a89898887320753f8b`; a development engine with additional
features is not evidence that this patch builds. This exact patch has now passed
a separate fresh build, menu smoke and all 44 compact core scenarios on macOS,
with 401 assertions and zero debug errors. No engine executable or game data is
included here.

Build the optional engine in a separate checkout by following that document.
Set `F2_ENGINE` to its actual executable, not an application bundle or an empty
variable. For example, replace this relative path with your own built executable:

```sh
export F2_ENGINE="../fallout2-ce-build/fallout2-ce"
```

Use the complete original archive installation selected during setup. The native
runner also needs `fallout2.cfg`; an extracted-only data tree cannot start the
game. An invalid explicit engine path fails without selecting another engine.
The runner prepares its own local run directory and retains previous runs and
logs. Treat step files and stage Python as trusted local test programs.

After the engine smoke check passes, a focused core scenario is:

```sh
nice -n 15 python -B mod/megaton/test.py --group core --stage tests/core/stage.py --steps tests/core/smoke.txt
```

For a complete regression pass, run these sequentially:

```sh
nice -n 15 python -B mod/megaton/tests/foundation/run_all.py
nice -n 15 python -B mod/megaton/tests/layout/run_all.py
nice -n 15 python -B mod/megaton/tests/core/run_all.py --jobs 1
nice -n 15 python -B mod/megaton/tests/merchants/run_all.py
nice -n 15 python -B mod/megaton/tests/sidequests/run_all.py
nice -n 15 python -B mod/megaton/tests/flavour/run_all.py --jobs 1
nice -n 15 python -B mod/megaton/tests/integration/run_all.py --jobs 1
nice -n 15 python -B mod/megaton/tests/art/run_all.py
```

Do not run two scenarios or suites that share a staging group concurrently.
The runner currently uses one translated step file per group; startup delays do
not make concurrent writes safe. Preserve old
`mod/megaton/out-*` staging directories before rebuilding when their exact bytes
are needed for comparison. Use `--no-build` only when deliberately testing a
previously identified archive; it is not a substitute for testing changed source.

Check each scenario's assertions and final verdict, debug log, and screenshots.
Open scenery views and dialogue shots; inspect doors, roof hiding, navigation,
text and night lighting. Investigate timeouts, script errors and art-cache warnings.
A scenario without assertions supplies crash/screenshot evidence, not proof that
the intended interaction occurred. Test archives, logs and captures remain local.

## Art authoring

The player operation is **restore**, not render:

```sh
python megaton.py setup
```

Setup invokes `mod/megaton-art/build.py clone-data`. It validates and restores
1,862 reviewed own FRMs (including 50 transparent decal cells), then reconstructs
153 mixed floor tiles from those cells and the selected player's ground tiles.
It retains the frozen IDs and preserves the previous art output. No stock ground
pixels or palettes are shipped as standalone sprite sources.

For an art-source preview, install the optional conversion dependency and provide
Blender 5.x, whose Python API the source targets:

```sh
python -m pip install -r requirements-art.txt
nice -n 15 env MG_ART_DEVICE=CPU python mod/megaton-art/build.py preview pieces/gate.py
```

`blender` must be on `PATH`, or set `BLENDER` to the executable. The builder caps
Blender at four threads. `MG_ART_DEVICE=CPU` avoids GPU variation at palette
thresholds, but byte-for-byte reproduction with a fresh toolchain has not yet
been verified. Blender has its own Python environment; do not install `bpy` into
the player's virtual environment. OpenCV runs in the ordinary Python environment
for render-pass conversion and sprite slicing, not during a player restore.

Restore does not produce indexed sheet PNGs or Blender render passes. Author
commands such as `piece`, `add` and `tiles` render those inputs and can change the
manifest or claimed slots. They belong in a separate author checkout with old
outputs preserved. Changed art invalidates the committed `sprites/manifest.json`;
there is currently no public one-command inventory refresh. A maintainer must
review the own sprite set, update its hashes and manifest binding, keep tile IDs
consistent and rerun map/engine/visual checks before publishing it. Do not copy
mixed floor composites or generated palettes into `sprites/` to repair a mismatch.
Running setup restores the committed art; it does not approve new author outputs.

Signs request locally installed fonts listed in [NOTICE.md](../NOTICE.md#fonts-artwork-and-game-rights).
Missing fonts can fall back and change spacing. No font software is included.
The exact 52-file Blender code boundary is documented separately in
[blender-boundary.md](blender-boundary.md); other pipeline code retains its own
licence terms.
