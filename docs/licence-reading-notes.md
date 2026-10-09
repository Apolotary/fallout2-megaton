# Primary-source reading notes

Read 2026-10-09. These notes record the pages inspected and limits of the findings.

- [Blender license page](https://www.blender.org/about/license/) distinguishes
  Python API script terms from output artwork. Its official indexed copy was
  available; direct retrieval was not. The current [FAQ](https://www.blender.org/support/faq/)
  uses GPL language for distributed API scripts. The [FSF Expat entry](https://www.gnu.org/licenses/license-list.html#Expat)
  identifies the common MIT form as GPL-compatible. Licensing owned component
  source under MIT does not relicense Blender or establish the provenance of
  copied code.
- The pinned[sslc source](https://github.com/sfall-team/sslc/tree/3991207639c133bd14948fae6c18df59310b5287)
  has no inspected repository-wide LICENSE/COPYING/NOTICE grant. Its MCPP notice
  covers that component. Its CMake-generated package license field is not an
  Unlicense grant. The exact pinned evidence was read from existing Git objects;
  current official GitHub pages corroborated the passages. No compiler is bundled.
- [Apple's macOS Golden Gate SLA](https://www.apple.com/legal/sla/docs/macOSGoldenGate.pdf),
  English section 2E, permits included-font display/printing while running the
  licensed system and conditions embedding separately. The installed accompanying
  agreement had the same clause. The [Apple font inventory](https://support.apple.com/en-la/127491)
  lists the eight requested families. No font software is distributed. The clause
  does not expressly enumerate redistributed game sprites, so no unlimited
  redistribution assurance is inferred.
- [Microsoft's font FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
  expressly discusses static images in apps/games but limits its coverage to
  Windows-supplied fonts. It is useful context, not the granting agreement for
  fonts supplied through macOS.

No separate font agreement, every historical font fallback, compiler-wide grant,
or full combined-work license assessment was verified by these readings. The
project's own art/code licenses cannot grant third-party rights.
