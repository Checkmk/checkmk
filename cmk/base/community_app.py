#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.base import notify
from cmk.ccc.version import Edition
from cmk.fetchers import PlainFetcherTrigger
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.utils.labels import get_builtin_host_labels
from cmk.utils.paths import omd_root

from . import diagnostics, localize
from .automations.automations import Automations
from .base_app import CheckmkBaseApp
from .core.nagios.factory import create_core
from .modes.check_mk import general_options, modes_common
from .modes.modes import Mode, Modes


def make_app() -> CheckmkBaseApp:
    modes = _modes(
        [
            *modes_common(),
            diagnostics.mode_create_diagnostics_dump(lambda x: {}),
            localize.mode_localize(),
            notify.mode_notify(),
        ]
    )
    automations = Automations()
    automations.discover()

    return CheckmkBaseApp(
        edition=Edition.COMMUNITY,
        modes=modes,
        automations=automations,
        make_bake_on_restart=lambda *args: lambda: None,
        create_core=create_core,
        licensing_handler_type=CommunityLicensingHandler,
        make_fetcher_trigger=lambda *a, **kw: PlainFetcherTrigger(omd_root=omd_root),
        make_metric_backend_fetcher=lambda *args: None,
        get_builtin_host_labels=get_builtin_host_labels,
        core_performance_settings=lambda _: {},
    )


def _modes(reg_modes: Sequence[Mode]) -> Modes:
    modes = Modes()

    for option in general_options():
        modes.register_general_option(option)

    for mode in reg_modes:
        modes.register(mode)

    return modes
