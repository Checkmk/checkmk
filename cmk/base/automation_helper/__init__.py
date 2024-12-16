#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import os
from pathlib import Path
from typing import Final

from setproctitle import setproctitle

from cmk.ccc.daemon import daemonize

from cmk.utils.redis import get_redis_client

from cmk.base.automations import automations

from ._app import get_application, reload_automation_config
from ._cache import Cache
from ._config import watcher_schedules
from ._log import configure_logger
from ._reloader import Reloader
from ._server import ApplicationServerConfig, run
from ._tracer import configure_tracer
from ._watcher import Watcher

APPLICATION_PROCESS_TITLE: Final = "cmk-automation-helper"
APPLICATION_LOG_DIRECTORY: Final = "automation-helper"
APPLICATION_ACCESS_LOG: Final = "access.log"
APPLICATION_ERROR_LOG: Final = "error.log"
APPLICATION_PID_FILE: Final = "automation-helper.pid"


def main() -> int:
    try:
        setproctitle(APPLICATION_PROCESS_TITLE)
        os.unsetenv("LANG")

        omd_root = Path(os.environ.get("OMD_ROOT", ""))

        configure_tracer(omd_root)

        run_directory = omd_root / "tmp" / "run"
        log_directory = omd_root / "var" / "log" / APPLICATION_LOG_DIRECTORY

        run_directory.mkdir(exist_ok=True, parents=True)
        log_directory.mkdir(exist_ok=True, parents=True)

        configure_logger(log_directory)

        redis_client = get_redis_client()
        cache = Cache.setup(client=redis_client)

        reloader = Reloader(cache=cache)

        watcher = Watcher(watcher_schedules(omd_root), cache)

        app = get_application(
            engine=automations,
            cache=cache,
            reload_config=reload_automation_config,
        )

        server_config = ApplicationServerConfig(
            unix_socket=run_directory / "automation-helper.sock",
            pid_file=run_directory / APPLICATION_PID_FILE,
            access_log=log_directory / APPLICATION_ACCESS_LOG,
            error_log=log_directory / APPLICATION_ERROR_LOG,
        )

        daemonize()

        run(server_config, [watcher, reloader], app)

    except Exception:
        return 1

    return 0
