#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launches automation helper application for processing automation commands."""

import os

from setproctitle import setproctitle

from cmk.ccc.daemon import daemonize

from cmk.utils.caching import cache_manager
from cmk.utils.paths import omd_root
from cmk.utils.redis import get_redis_client
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from cmk.base import config
from cmk.base.api.agent_based.register import (
    AgentBasedPlugins,
    extract_known_discovery_rulesets,
)
from cmk.base.automations import automations

from ._app import make_application
from ._cache import Cache
from ._config import config_from_disk_or_default_config
from ._log import configure_logger, LOGGER
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

        daemonize()

        with run_watcher(
            config.watcher_config,
            cache,
        ):
            try:
                run_server(
                    config.server_config,
                    make_application(
                        engine=automations,
                        cache=cache,
                        reloader_config=config.reloader_config,
                        reload_config=_reload_automation_config,
                        clear_caches_before_each_call=_clear_caches_before_each_call,
                    ),
                )
            except SystemExit:
                LOGGER.info("Received termination signal, shutting down")

    except Exception:
        return 1

    return 0


def _reload_automation_config(plugins: AgentBasedPlugins) -> config.LoadedConfigFragment:
    cache_manager.clear()
    discovery_rulesets = extract_known_discovery_rulesets(plugins)
    return config.load(discovery_rulesets, validate_hosts=False)


def _clear_caches_before_each_call(ruleset_matcher: RulesetMatcher) -> None:
    ruleset_matcher.ruleset_optimizer.clear_caches()
    ruleset_matcher.ruleset_optimizer.clear_ruleset_caches()
