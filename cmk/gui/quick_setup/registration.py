#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry

from . import _modes
from .config_setups import register as register_config_setups
from .handlers.setup import QuickSetupActionBackgroundJob
from .handlers.stage import AutomationQuickSetupStageAction, QuickSetupStageActionBackgroundJob
from .v0_unstable._registry import QuickSetupRegistry


def register(
    automation_command_registry: AutomationCommandRegistry,
    main_module_registry: MainModuleRegistry,
    mode_registry: ModeRegistry,
    quick_setup_registry: QuickSetupRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    _modes.register(main_module_registry, mode_registry)
    automation_command_registry.register(AutomationQuickSetupStageAction)
    register_config_setups(quick_setup_registry)
    job_registry.register(QuickSetupStageActionBackgroundJob)
    job_registry.register(QuickSetupActionBackgroundJob)
