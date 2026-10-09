# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""The town WITHOUT the custom art (the stock dressing the art plan replaces), every script.

    python3 mod/megaton/test.py --group art-stock --stage tests/art/stage_stock.py --steps tests/art/clicks.txt --res 1280x960

For before / after comparisons only: what a click or a view did before the art stood there.
The bomb is still the custom sprite (the cast places it), without its blockers.
"""
import layout


def build_maps(out_dir):
    layout.build_maps(out_dir, strict=True, art=False)
