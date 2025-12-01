#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.mode import ModeRegistry

from .wato import register_modes, register_pages


def register(
    mode_registry: ModeRegistry,
    page_registry: PageRegistry,
) -> None:
    register_modes(mode_registry)
    register_pages(page_registry)
