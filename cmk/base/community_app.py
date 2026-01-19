#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.base import notify
from cmk.ccc.version import Edition
from cmk.fetchers import PlainFetcherTrigger
from cmk.utils.labels import get_builtin_host_labels
from cmk.utils.licensing.community_handler import CRELicensingHandler

from . import diagnostics, localize
from .automations.automations import Automation, Automations
from .automations.check_mk import automations_common
from .base_app import CheckmkBaseApp
from .core.factory import create_core
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
    automations = _automations(
        [
            *automations_common(),
            diagnostics.automation_create_diagnostics_dump(lambda x: {}),
            *notify.automations_notify(),
        ]
    )

    return CheckmkBaseApp(
        edition=Edition.COMMUNITY,
        modes=modes,
        automations=automations,
        make_bake_on_restart=lambda *args: lambda: None,
        create_core=create_core,
        licensing_handler_type=CRELicensingHandler,
        make_fetcher_trigger=lambda *a, **kw: PlainFetcherTrigger(),
        make_metric_backend_fetcher=lambda *args: None,
        get_builtin_host_labels=get_builtin_host_labels,
    )


def _modes(reg_modes: Sequence[Mode]) -> Modes:
    modes = Modes()

    for option in general_options():
        modes.register_general_option(option)

    for mode in reg_modes:
        modes.register(mode)

    return modes


def _automations(reg_automations: Sequence[Automation]) -> Automations:
    automations = Automations()
    for automation in reg_automations:
        automations.register(automation)
    return automations
