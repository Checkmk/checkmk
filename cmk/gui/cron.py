#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
import time
from typing import Union

import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.utils as utils
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException

# Things imported here are used by pre legacy (pre 1.6) cron plugins
from cmk.gui.plugins.cron import (  # noqa: F401 # pylint: disable=unused-import
    multisite_cronjobs, register_job,
)

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.cron  # pylint: disable=no-name-in-module

loaded_with_language: Union[bool, None, str] = False


def _lock_file() -> Path:
    return Path(cmk.utils.paths.tmp_dir) / "cron.lastrun"


# Load all view plugins
def load_plugins(force: bool) -> None:
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    utils.load_web_plugins("cron", globals())

    loaded_with_language = cmk.gui.i18n.get_current_language()


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

    with store.locked(lock_file):
        # The cron page is accessed unauthenticated. After leaving the page_run_cron area
        # into the job functions we always want to have a user context initialized to keep
        # the code free from special cases (if no user logged in, then...).
        # The jobs need to be run in privileged mode in general. Some jobs, like the network
        # scan, switch the user context to a specific other user during execution.
        config.set_super_user()

        logger.debug("Starting cron jobs")

        for cron_job in multisite_cronjobs:
            try:
                job_name = cron_job.__name__

                logger.debug("Starting [%s]", job_name)
                cron_job()
                logger.debug("Finished [%s]", job_name)
            except Exception:
                html.write("An exception occured. Take a look at the web.log.\n")
                logger.exception("Exception in cron job [%s]", job_name)

        logger.debug("Finished all cron jobs")
        html.write("OK\n")
