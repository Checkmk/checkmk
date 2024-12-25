#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import os
import signal
from contextlib import nullcontext

from setproctitle import setproctitle

from cmk.ccc.daemon import daemonize

from cmk.utils.paths import omd_root
from cmk.utils.redis import get_redis_client

from cmk.base.automations import automations

from ._app import get_application, reload_automation_config
from ._cache import Cache
from ._config import config_from_disk_or_default_config
from ._log import configure_logger, LOGGER
from ._reloader import run as run_reloader
from ._server import run as run_server
from ._tracer import configure_tracer
from ._watcher import run as run_watcher


def main() -> int:
    try:
        setproctitle("cmk-automation-helper")
        os.unsetenv("LANG")

        configure_tracer(omd_root)

        run_directory = omd_root / "tmp" / "run"
        log_directory = omd_root / "var" / "log" / "automation-helper"

        run_directory.mkdir(exist_ok=True, parents=True)
        log_directory.mkdir(exist_ok=True, parents=True)

        configure_logger(log_directory)

        cache = Cache.setup(client=get_redis_client())
        config = config_from_disk_or_default_config(
            omd_root=omd_root,
            run_directory=run_directory,
            log_directory=log_directory,
        )
        app = get_application(
            engine=automations,
            cache=cache,
            reload_config=reload_automation_config,
        )

        daemonize()

        current_pid = os.getpid()

        with (
            run_watcher(
                config.watcher_config,
                cache,
            ),
            (
                run_reloader(
                    config.reloader_config,
                    cache,
                    lambda: os.kill(current_pid, signal.SIGHUP),
                )
                if config.reloader_config.active
                else nullcontext()
            ),
        ):
            try:
                run_server(
                    config.server_config,
                    app,
                )
            except SystemExit:
                LOGGER.info("Received termination signal, shutting down")

    except Exception:
        return 1

    return 0
