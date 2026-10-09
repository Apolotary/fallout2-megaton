# Known issues and compatibility

Clean exported-copy setup, build, installation and removal passed on macOS with
the English GOG profile. The resulting archive matches the accepted merged town
byte for byte. All 182 development-suite cases have passing evidence, including
51 fresh map-dependent cases after the final geometry correction. The optional
test-engine patch compiled and passed all 44 core scenarios. Unpatched native
checks covered startup, direct-gate rendering and save/load on the tested current
base. Official fallout2-ce v1.3.0 passed direct Megaton startup and normal UI
shutdown. These checks have the narrower coverage described below and do not
establish support for other platforms or game editions.

- **Game edition.** Setup checks an English GOG input profile. Steam, other
  editions, translations and modified input tables are unverified and may fail
  the profile check. Do not weaken those checks to force an unsupported install.
- **Platform.** Windows and Linux installation and case-sensitive filesystem
  behavior are unverified. The author/test commands in `testing.md` use a Unix
  shell. The original 1998 Fallout 2 executable is unsupported.
- **Native validation coverage.** Manual world-map travel, walking through the
  gate, NPC dialogue and trade remain unverified on the unpatched engines. The
  automation environment could not reliably control the relative game cursor.
  Save/load passed on the unpatched `e97087b` build, but was not tested on official
  v1.3.0. The current-base direct session required terminating its isolated
  process after UI quit, so its clean UI shutdown was not verified; official
  v1.3.0 did quit normally. These limits are separate from the automated gameplay
  assertions that passed with the test engine.
- **Other mods.** Megaton replaces complete tables. Additional patch archives,
  loose gameplay overrides and community-patch combinations have not been tested.
  Use a separate game installation and keep any previous mod archive safe.
- **Saves.** Start a new game. Existing saves can retain old map objects or quest
  state, and save compatibility across mod builds is unverified. Keep saves that
  depend on Megaton separate and retain the corresponding mod build.
- **Arrival.** The world-map circle south-east of Arroyo can initially read
  `Unknown`. It is small; entering it reveals the town.
- **Interactions.** Stand close to beds and examine them for the rest menu.
  Walter's pipes require the relevant skill or item rather than a general use
  action. Read the in-game guidance before assuming an object is inactive.
- **Artwork.** Set `art_cache_size=24` in `[system]` in the game's `fallout2.cfg`.
  The installer does not edit that file. Art source requests local macOS fonts;
  another system's fallback can change lettering. Full art-author inventory
  refresh remains a reviewed maintainer operation.
- **Install ownership.** A foreign or changed `patch001.dat` is deliberately
  refused. Keep the ignored `game/` state directory if you want this checkout to
  recognize and uninstall its archive. If a previous operation was interrupted,
  inspect `python megaton.py status` and follow the error rather than deleting
  ownership state or overwriting the patch manually.
- **Direct start.** If you set `StartingMap=megaton.map` in `ddraw.ini`, remove it
  before starting an unmodified game after uninstalling. The installer leaves
  configuration and saves alone.
- **Scope.** Browser hosting, touch controls and video recording are not included
  in this native release. The optional engine patch is for local test automation;
  its macOS build, smoke checks and complete 44-case core run passed.

See [testing.md](testing.md#verification-status) for the current verification
record. When reporting a problem, include the mod revision, game edition, engine
version, the action and expected behavior. Review any excerpts for personal
information. Do not upload game files, saves, generated archives or full local logs.
