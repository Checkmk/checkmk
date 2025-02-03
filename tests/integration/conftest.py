#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site
from tests.testlib.web_session import CMKWebSession

from cmk.base.automation_helper._config import (  # pylint: disable=cmk-module-layer-violation
    Config,
    default_config,
    RELATIVE_CONFIG_PATH_FOR_TESTING,
    ReloaderConfig,
    ServerConfig,
)

from .event_console import CMKEventConsole

logger = logging.getLogger(__name__)


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(name="site", scope="session")
def get_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from get_site_factory(prefix="int_").get_test_site(
            name="test",
            auto_restart_httpd=True,
        )


@pytest.fixture(scope="session", name="web")
def fixture_web(site: Site) -> CMKWebSession:
    web = CMKWebSession(site)

    if not site.version.is_saas_edition():
        web.login()
    site.enforce_non_localized_gui(web)
    return web


@pytest.fixture(scope="session")
def ec(site: Site) -> CMKEventConsole:
    return CMKEventConsole(site)


# this is a temporary measure until we find a more robust implementation for the reloader
@pytest.fixture(scope="session", autouse=True)
def deactivate_automation_helper_reloader(site: Site) -> None:
    default_configuration = default_config(
        omd_root=site.root,
        run_directory=site.root / "tmp" / "run",
        log_directory=site.root / "var" / "log" / "automation-helper",
    )
    site.write_text_file(
        RELATIVE_CONFIG_PATH_FOR_TESTING,
        Config(
            server_config=ServerConfig(
                unix_socket=default_configuration.server_config.unix_socket,
                pid_file=default_configuration.server_config.pid_file,
                access_log=default_configuration.server_config.access_log,
                error_log=default_configuration.server_config.error_log,
                num_workers=1,
            ),
            watcher_config=default_configuration.watcher_config,
            reloader_config=ReloaderConfig(
                active=False,
                poll_interval=default_configuration.reloader_config.poll_interval,
                cooldown_interval=default_configuration.reloader_config.cooldown_interval,
            ),
        ).model_dump_json(),
    )
    site.run(["omd", "restart", "automation-helper"])
