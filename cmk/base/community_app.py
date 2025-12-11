#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition
from cmk.fetchers import PlainFetcherTrigger
from cmk.utils.licensing.community_handler import CRELicensingHandler

from . import diagnostics, localize
from .automations.automations import Automations
from .automations.check_mk import register_common_automations
from .base_app import CheckmkBaseApp
from .core.factory import create_core
from .modes.check_mk import common_modes, general_options
from .modes.modes import Modes


def make_app() -> CheckmkBaseApp:
    modes = _modes()
    automations = _automations()

    diagnostics.register(modes, automations, core_performance_settings=lambda x: {})
    localize.register(modes)

    return CheckmkBaseApp(
        edition=Edition.COMMUNITY,
        modes=modes,
        automations=automations,
        make_bake_on_restart=lambda *args: lambda: None,
        create_core=create_core,
        licensing_handler_type=CRELicensingHandler,
        make_fetcher_trigger=lambda x: PlainFetcherTrigger(),
        make_metric_backend_fetcher=lambda *args: None,
    )


def _modes() -> Modes:
    modes = Modes()

    for option in general_options():
        modes.register_general_option(option)

    for mode in common_modes():
        modes.register(mode)

    return modes


def _automations() -> Automations:
    automations = Automations()
    register_common_automations(automations)
    return automations
