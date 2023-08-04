#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.cron import register_job
from cmk.gui.pages import PageRegistry
from cmk.gui.wato.mode import ModeRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry

from . import _modes
from ._manager import execute_housekeeping_job


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
) -> None:
    register_job(execute_housekeeping_job)
    _modes.register(page_registry, mode_registry, main_module_registry)
