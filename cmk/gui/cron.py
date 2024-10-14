#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from functools import partial
from typing import Any

from cmk.gui import utils

multisite_cronjobs: list[Callable[[], Any] | partial] = []


def register_job(cron_job: Callable[[], Any]) -> None:
    # the callable should really return None, but some jobs return something (which is then ignored)
    multisite_cronjobs.append(cron_job)


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("cron", globals())


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plug-in API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from main module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plug-in loading order
    import cmk.gui.plugins.cron as api_module  # pylint: disable=cmk-module-layer-violation

    api_module.__dict__.update(
        {
            "multisite_cronjobs": multisite_cronjobs,
            "register_job": register_job,
        }
    )
