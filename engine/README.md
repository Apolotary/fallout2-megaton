# Optional native test engine

This patch modifies [fallout2-ce](https://github.com/alexbatalov/fallout2-ce) at **e97087b9582f37075db347a89898887320753f8b** for automated native tests. It adds scripted input, state diagnostics, single screenshots and SDL headless support. It does not include the development browser or movie-recording changes. The upstream license is reproduced unchanged in [LICENSE.md](LICENSE.md); engine-derived files are outside the art-source MIT license boundary.

The patch passed a clean apply check and a fresh arm64 build against that exact base on macOS 27.0.1, using Apple Clang 21.0.0, CMake 4.1.1 and SDL2 2.32.10. Native menu and compact core smoke checks passed, and all 15 arrival/Weld dialogue screenshots were opened and reviewed. The complete core suite with this extracted patch passed 44/44 scenarios and 401/401 assertions, with zero debug errors and actual runner exit 0. These results are separate from earlier development-engine checks and do not establish other-platform support.

## Build in a separate engine checkout

Install a C++17 toolchain, CMake, SDL2 and zlib appropriate to your platform. Obtain a clean checkout of the linked upstream project separately. Set `ENGINE_SOURCE` to that checkout, `ENGINE_BUILD` to a new build directory and `FPATTERN_SOURCE` to a clean local checkout of fpattern at **8523173ec252c3b796fcdfca0fcc6329642fbbe3**. Use absolute paths for these variables. From this mod repository:

```sh
PATCH_FILE="$PWD/engine/fallout2-ce-autotest.patch"
git -C "$ENGINE_SOURCE" checkout --detach e97087b9582f37075db347a89898887320753f8b
git -C "$ENGINE_SOURCE" apply --check "$PATCH_FILE"
git -C "$ENGINE_SOURCE" apply "$PATCH_FILE"
cmake -S "$ENGINE_SOURCE" -B "$ENGINE_BUILD" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DFALLOUT_VENDORED=OFF \
  -DFETCHCONTENT_SOURCE_DIR_FPATTERN="$FPATTERN_SOURCE" \
  -DFETCHCONTENT_FULLY_DISCONNECTED=ON
cmake --build "$ENGINE_BUILD" --parallel 4
```

Confirm the engine checkout is clean before applying the patch; preserve an existing checkout with changes. CMake otherwise uses FetchContent for fpattern even when vendored SDL2/zlib are disabled. The explicit local source above avoids that implicit download. On macOS, select an architecture compatible with your SDL2 installation, for example `-DCMAKE_OSX_ARCHITECTURES=arm64` for an arm64 installation. Dependency installation and builds on a fresh host have not been verified here.

Set `F2_ENGINE` to the new executable. On macOS it is normally `Fallout II Community Edition.app/Contents/MacOS/Fallout II Community Edition` inside the build folder; Linux normally uses `fallout2-ce`. The runner requires an existing executable and never silently falls back to another build. It copies that executable into each isolated run because the engine selects its working directory from its executable location.

## Smoke and scenario checks

Use a separate copy of the mod repository for engine verification. Suite runners own named output/run directories, so do not share them with another active test suite. Follow the main README's setup first. Set `FALLOUT2_DIR` to the original installation folder containing `master.dat`, `critter.dat`, `patch000.dat` and `fallout2.cfg`, or keep the archive-folder selection remembered by setup. An extracted-only tree is enough for mod setup but cannot start this native runner. Archive/config/sound names are matched without letter-case assumptions; ambiguous duplicates are rejected. Loose extra game patches are not imported.

The runner creates run-local configuration and data paths, and normalizes a run-local sound mirror. Original game files are never the output target. `--fresh` moves the entire prior run folder aside. Existing logs, screenshots and replaced run files are retained rather than deleted. Commands supplied through `--steps`, `--overlay`, and `--ddraw` are trusted local test inputs.

First, create a small local command file under the isolated copy's ignored `run/` folder:

```text
wait 3000
log native-menu-smoke
shot shots/menu.ppm
quit 0
```

Then run it without the new-game prologue:

```sh
python3 -B tools/f2test.py --name native-menu-smoke --raw \
  --steps run/native-menu-smoke.txt --fresh --timeout 60
```

Require a zero engine exit, the `native-menu-smoke` log marker, and a nonempty 640×480 screenshot that actually shows the menu. Open the image. Reject unknown-command, cannot-open and cannot-write diagnostics even if the process exits zero.

For the compact Megaton core fixture, the concrete command includes the required steps file:

```sh
nice -n 15 python3 -B mod/megaton/test.py --group core \
  --stage tests/core/stage.py --steps tests/core/smoke.txt
nice -n 15 python3 -B mod/megaton/test.py --group core \
  --stage tests/core/stage.py --steps tests/core/arrival.txt --no-build
nice -n 15 python3 -B mod/megaton/test.py --group core \
  --stage tests/core/stage.py --steps tests/core/weld.txt --no-build
```

These fixture builds require the explicitly provided SSL compiler described in the main README; production prebuilts are not valid for stage/source overrides. The project does not download or ship that compiler. The smoke checks the map and objects and captures two images; arrival and weld exercise movement, input and nested dialogue. Require every assertion, zero debug errors, no art-cache warning and nonempty expected screenshots. For full acceptance, run `python3 -B mod/megaton/tests/core/run_all.py --jobs 1` and record the actual scenario count.

The command parser remains intentionally small: unknown commands produce a warning, some malformed operands default to zero, screenshot failure does not force a failed exit, and reaching the end of a file does not quit. The runner appends a quit command and supplies a timeout. This patch is for trusted local scripts. Headless fallback is selected by SDL's `dummy`/`offscreen` driver, independently of whether `F2_AUTOTEST` is set. Native gameplay and other platforms need their own validation.
