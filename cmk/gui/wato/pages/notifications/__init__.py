#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.search import MatchItemGeneratorRegistry

from . import modes, quick_setup


def register(
    mode_registry: ModeRegistry,
    quick_setup_registry: QuickSetupRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    automation_command_registry: AutomationCommandRegistry,
) -> None:
    modes.register(
        mode_registry,
        match_item_generator_registry,
        automation_command_registry,
    )
    quick_setup.register(quick_setup_registry)
