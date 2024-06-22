#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cmk.utils.paths
from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException

import cmk.gui.pages
from cmk.gui import utils
from cmk.gui.http import response
from cmk.gui.log import logger
from cmk.gui.pages import PageRegistry
from cmk.gui.session import SuperUserContext

multisite_cronjobs = []


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page_handler("noauth:run_cron", page_run_cron)


def register_job(cron_job: Callable[[], Any]) -> None:
    # the callable should really return None, but some jobs return something (which is then ignored)
    multisite_cronjobs.append(cron_job)


def _lock_file() -> Path:
    return cmk.utils.paths.tmp_dir / "cron.lastrun"


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


def page_run_cron() -> None:
    """Page called by some external trigger (usually cron job in OMD site)

    Note: this URL is being called *without* any login. We have no
    user. Everyone can call this! We must not read any URL variables.

    There is no output written to the user in regular cases. Exceptions
    are written to the web log.
    """
    lock_file = _lock_file()

    # Prevent cron jobs from being run too often, also we need
    # locking in order to prevent overlapping runs
    if lock_file.exists():
        last_run = lock_file.stat().st_mtime
        if time.time() - last_run < 59:
            raise MKGeneralException("Cron called too early. Skipping.")

    with lock_file.open("wb"):
        pass  # touches the file

    # The cron page is accessed unauthenticated. After leaving the page_run_cron area
    # into the job functions we always want to have a user context initialized to keep
    # the code free from special cases (if no user logged in, then...).
    # The jobs need to be run in privileged mode in general. Some jobs, like the network
    # scan, switch the user context to a specific other user during execution.
    with store.locked(lock_file), SuperUserContext():
        logger.debug("Starting cron jobs")

        for cron_job in multisite_cronjobs:
            try:
                job_name = cron_job.__name__

                logger.debug("Starting [%s]", job_name)
                cron_job()
                logger.debug("Finished [%s]", job_name)
            except Exception:
                response.set_data("An exception occured. Take a look at the web.log.\n")
                logger.exception("Exception in cron job [%s]", job_name)

        logger.debug("Finished all cron jobs")
        response.set_data("OK\n")
