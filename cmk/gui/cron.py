#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import response
from cmk.gui.log import logger

# Things imported here are used by pre legacy (pre 1.6) cron plugins
from cmk.gui.plugins.cron import (  # noqa: F401 # pylint: disable=unused-import
    multisite_cronjobs,
    register_job,
)
from cmk.gui.utils.logged_in import SuperUserContext


def _lock_file() -> Path:
    return Path(cmk.utils.paths.tmp_dir) / "cron.lastrun"


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.modules.call_load_plugins_hooks())"""
    utils.load_web_plugins("cron", globals())


# Page called by some external trigger (usually cron job in OMD site)
# Note: this URL is being called *without* any login. We have no
# user. Everyone can call this! We must not read any URL variables.
#
# There is no output written to the user in regular cases. Exceptions
# are written to the web log.
@cmk.gui.pages.register("noauth:run_cron")
def page_run_cron() -> None:

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
