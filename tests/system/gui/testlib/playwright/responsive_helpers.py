#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared helpers for responsive (multi-viewport) GUI E2E tests.

KEEP IN SYNC WITH:
  - cmk/gui/dashboard/api/model/constants.py (RESPONSIVE_GRID_BREAKPOINTS)
  - packages/cmk-frontend-vue/src/assets/breakpoints.scss
  - packages/cmk-frontend-vue/src/assets/breakpoints.css
"""

from dataclasses import dataclass

from playwright.sync_api import ViewportSize


@dataclass(frozen=True)
class Breakpoint:
    """A canonical responsive breakpoint, mirrored from RESPONSIVE_GRID_BREAKPOINTS."""

    name: str
    min_width: int
    columns: int

    @property
    def viewport(self) -> ViewportSize:
        """Return a viewport size that's *inside* this breakpoint band.

        Uses min_width directly for XS/S/M/L/XL — that pixel maps to this
        breakpoint (>= min_width). Height is fixed at 900 (tall enough to
        not push content off-screen while still being a realistic mobile
        landscape height for XS).
        """
        return ViewportSize(width=self.min_width, height=900)


CANONICAL_BREAKPOINTS: tuple[Breakpoint, ...] = (
    Breakpoint(name="XS", min_width=280, columns=4),
    Breakpoint(name="S", min_width=535, columns=8),
    Breakpoint(name="M", min_width=705, columns=12),
    Breakpoint(name="L", min_width=961, columns=12),
    Breakpoint(name="XL", min_width=1217, columns=24),
)
