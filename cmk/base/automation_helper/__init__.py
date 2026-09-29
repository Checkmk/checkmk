#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Launches automation helper application for processing automation commands."""

import os
import signal
import sys
from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI
from setproctitle import setproctitle

from cmk.automations.logging import LoggingManager
from cmk.base import config
from cmk.base.automations.automations import Automations, discover_automations
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.utils.paths import omd_root
from cmk.utils.redis import get_redis_client

from ._app import make_application
from ._cache import Cache
from ._config import config_from_disk_or_default_config
from ._server import run as run_server
from ._tracer import configure_tracer
from ._watcher import run as run_watcher

_RELATIVE_RUN_DIRECTORY = Path("tmp", "run")
_RELATIVE_LOG_DIRECTORY = Path("var", "log", "automation-helper")


def main() -> int:
    try:
        return _main()
    except Exception:
        return 1


def _main() -> int:
    exit_code = 0
    setproctitle("cmk-automation-helper[master]")
    os.unsetenv("LANG")

    daemonize()

    run_directory = omd_root / _RELATIVE_RUN_DIRECTORY
    log_directory = omd_root / _RELATIVE_LOG_DIRECTORY
    run_directory.mkdir(exist_ok=True, parents=True)

    config = config_from_disk_or_default_config(
        omd_root=omd_root,
        run_directory=run_directory,
        log_directory=log_directory,
    )
    if config.server_config.num_workers == 1:
        # In single-worker mode, uvicorn re-raises captured signals after shutting down the server.
        # We need to catch the re-raised SIGTERM signal to exit cleanly.
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))  # noqa: ARG005

    log_manager = LoggingManager()
    with (
        pid_file_lock(config.server_config.pid_file),
        log_manager.file_logging(path=config.server_config.worker_log),
    ):
        logger = log_manager.get_logger("automation.server")
        configure_tracer(omd_root)

        with run_watcher(
            config.watcher_config,
            Cache.setup(client=get_redis_client()),
        ):
            try:
                run_server(
                    config.server_config,
                    f"cmk.base.automation_helper:{_application.__name__}",
                )
                raise SystemExit(0)
            # in case of multiple workers: raised by us in the line above
            # in case of a single worker: re-raised by uvicorn when shutting down
            except SystemExit as system_exit:
                if isinstance(system_exit.code, int):
                    exit_code = system_exit.code

            logger.info("Received termination signal, shutting down")

    return exit_code


def _application() -> FastAPI:
    config = config_from_disk_or_default_config(
        omd_root=omd_root,
        run_directory=omd_root / _RELATIVE_RUN_DIRECTORY,
        log_directory=omd_root / _RELATIVE_LOG_DIRECTORY,
    )
    if config.server_config.num_workers > 1:
        # uvicorn will spawn subprocesses in this case, so we need to re-initialize
        setproctitle("cmk-automation-helper[worker]")
        os.unsetenv("LANG")
        configure_tracer(omd_root)

    return make_application(
        omd_root=omd_root,
        engine=Automations(discover_automations()),
        cache=Cache.setup(client=get_redis_client()),
        config=config,
        reload_config=_reload_automation_config,
    )


def _reload_automation_config() -> Mapping[str, object]:
    return config.load_raw_config(with_conf_d=True)
