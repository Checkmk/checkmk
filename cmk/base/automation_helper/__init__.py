#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import os
import signal
from contextlib import nullcontext
from pathlib import Path

from setproctitle import setproctitle

from cmk.ccc.daemon import daemonize

from cmk.utils.redis import get_redis_client

from cmk.base.automations import automations

from ._app import get_application, reload_automation_config
from ._cache import Cache
from ._config import reloader_config, server_config, watcher_schedules
from ._log import configure_logger, LOGGER
from ._reloader import run as run_reloader
from ._server import run as run_server
from ._tracer import configure_tracer
from ._watcher import run as run_watcher

RELATIVE_PATH_FLAG_DISABLE_RELOADER = "disable-automation-helper-reloader"


def main() -> int:
    try:
        setproctitle("cmk-automation-helper")
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))

        configure_tracer(omd_root)

        run_directory = omd_root / "tmp" / "run"
        log_directory = omd_root / "var" / "log" / "automation-helper"

        run_directory.mkdir(exist_ok=True, parents=True)
        log_directory.mkdir(exist_ok=True, parents=True)

        configure_logger(log_directory)

        redis_client = get_redis_client()
        cache = Cache.setup(client=redis_client)
        server_configuration = server_config(
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
                watcher_schedules(omd_root),
                cache,
            ),
            (
                nullcontext()
                # it would be better to handle this via an environment variable, but the automation
                # helper is started via the omd command, which does not pass through environment
                # variables
                if (omd_root / RELATIVE_PATH_FLAG_DISABLE_RELOADER).exists()
                else run_reloader(
                    reloader_config(),
                    cache,
                    lambda: os.kill(current_pid, signal.SIGHUP),
                )
            ),
        ):
            try:
                run_server(
                    server_configuration,
                    app,
                )
            except SystemExit:
                LOGGER.info("Received termination signal, shutting down")

    except Exception:
        return 1

    return 0
