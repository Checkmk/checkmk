#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Launches automation helper application for processing automation commands."""

import multiprocessing
import os
import signal
import sys
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from setproctitle import setproctitle

import cmk.ccc.version as cmk_version
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.config import ConfigCache
from cmk.ccc.daemon import daemonize, pid_file_lock
from cmk.ccc.site import SiteId
from cmk.checkengine.plugin_backend import (
    extract_known_discovery_rulesets,
)
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.utils.caching import cache_manager
from cmk.utils.labels import Labels
from cmk.utils.paths import omd_root
from cmk.utils.redis import get_redis_client

from ._app import make_application
from ._cache import Cache
from ._config import config_from_disk_or_default_config
from ._log import configure_logger, LOGGER
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
    log_directory.mkdir(exist_ok=True, parents=True)

    config = config_from_disk_or_default_config(
        omd_root=omd_root,
        run_directory=run_directory,
        log_directory=log_directory,
    )
    if config.server_config.num_workers == 1:
        # In single-worker mode, uvicorn re-raises captured signals after shutting down the server.
        # We need to catch the re-raised SIGTERM signal to exit cleanly.
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    with pid_file_lock(config.server_config.pid_file):
        configure_tracer(omd_root)
        configure_logger(log_directory)

        config = config_from_disk_or_default_config(
            omd_root=omd_root,
            run_directory=run_directory,
            log_directory=log_directory,
        )

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

            LOGGER.info("Received termination signal, shutting down")

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
        # When running in a uvicorn worker launched via multiprocessing (n_workers > 1), the global
        # multiprocessing start method is set to "spawn" by the uvicorn multiprocessing code (could be
        # unintentional). We have automation calls that rely on "fork" as the start method.
        _reset_global_multiprocessing_start_method_to_platform_default()
        configure_tracer(omd_root)
        configure_logger(omd_root / _RELATIVE_LOG_DIRECTORY)

    return make_application(
        engine=make_app(cmk_version.edition(omd_root)).automations,
        cache=Cache.setup(client=get_redis_client()),
        reloader_config=config.reloader_config,
        reload_config=_reload_automation_config,
        clear_caches_before_each_call=_clear_caches_before_each_call,
    )


def _reset_global_multiprocessing_start_method_to_platform_default() -> None:
    multiprocessing.set_start_method(None, force=True)
    multiprocessing.get_start_method(allow_none=False)


def _reload_automation_config(
    plugins: AgentBasedPlugins, get_builtin_host_labels: Callable[[SiteId], Labels]
) -> config.LoadingResult:
    cache_manager.clear()
    discovery_rulesets = extract_known_discovery_rulesets(plugins)
    return config.load(discovery_rulesets, get_builtin_host_labels, validate_hosts=False)


def _clear_caches_before_each_call(config_cache: ConfigCache) -> None:
    config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(
        {
            hn
            for hn in set(config_cache.hosts_config.hosts).union(config_cache.hosts_config.clusters)
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        }
    )
    config_cache.ruleset_matcher.ruleset_optimizer.clear_caches()
    config_cache.ruleset_matcher.ruleset_optimizer.clear_ruleset_caches()
