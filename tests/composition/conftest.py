#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from typing import Any, Literal

import pytest
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from tests.composition.utils import get_cre_agent_path

from tests.testlib.agent import (
    agent_controller_daemon,
    bake_agents,
    download_and_install_agent_package,
    install_agent_package,
)
from tests.testlib.site import (
    get_site_factory,
    Site,
    tracing_config_from_env,
)
from tests.testlib.utils import is_containerized, run

from cmk.base.automation_helper._config import (  # pylint: disable=cmk-module-layer-violation
    Config,
    default_config,
    RELATIVE_CONFIG_PATH_FOR_TESTING,
    ReloaderConfig,
    ServerConfig,
)

site_factory = get_site_factory(prefix="comp_")

logger = logging.getLogger(__name__)


_TEST_SITES_LOGGING_LEVELS: Mapping[str, int] = {
    "cmk.web.background-job": 10,
    "cmk.web": 10,
}


@pytest.fixture(scope="session", autouse=True)
def instrument_requests() -> None:
    RequestsInstrumentor().instrument()


def _write_global_settings(site: Site, file_path: str, settings: dict[str, Any]) -> None:
    new_global_settings = "".join(f"{key} = {repr(val)}\n" for key, val in settings.items())
    site.write_text_file(file_path, new_global_settings)


def _get_global_settings(site: Site, file_path: str) -> dict[str, Any]:
    global_settings_text = site.read_file(file_path)
    global_settings: dict[str, Any] = {}
    exec(global_settings_text, {}, global_settings)
    return global_settings


@contextmanager
def _increased_logging_level(site: Site) -> Iterator[None]:
    global_settings_rel_path = "etc/check_mk/multisite.d/wato/global.mk"
    global_setting = _get_global_settings(site, global_settings_rel_path)
    ori_global_setting = copy.deepcopy(global_setting)
    try:
        global_setting["log_levels"] = _TEST_SITES_LOGGING_LEVELS
        _write_global_settings(site, global_settings_rel_path, global_setting)
        yield
    finally:
        _write_global_settings(site, global_settings_rel_path, ori_global_setting)


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    with site_factory.get_test_site_ctx(
        "central",
        description=request.node.name,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as central_site:
        with _increased_logging_level(central_site):
            yield central_site


@pytest.fixture(name="remote_site", scope="session")
def _remote_site(
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
) -> Iterator[Site]:
    yield from _make_connected_remote_site("remote", central_site, request.node.name)


@pytest.fixture(name="remote_site_2", scope="session")
def _remote_site_2(
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
) -> Iterator[Site]:
    yield from _make_connected_remote_site("remote2", central_site, request.node.name)


def _make_connected_remote_site(
    site_name: Literal["remote", "remote2"],  # just to track what we're doing...
    central_site: Site,
    site_description: str,
) -> Iterator[Site]:
    with site_factory.get_test_site_ctx(
        site_name,
        description=site_description,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as remote_site:
        with _connection(central_site=central_site, remote_site=remote_site):
            yield remote_site


@contextmanager
def _connection(
    *,
    central_site: Site,
    remote_site: Site,
) -> Iterator[None]:
    if central_site.version.is_managed_edition():
        basic_settings = {
            "alias": "Remote Testsite",
            "site_id": remote_site.id,
            "customer": "provider",
        }
    else:
        basic_settings = {
            "alias": "Remote Testsite",
            "site_id": remote_site.id,
        }

    central_site.openapi.sites.create(
        {
            "basic_settings": basic_settings,
            "status_connection": {
                "connection": {
                    "socket_type": "tcp",
                    "host": remote_site.http_address,
                    "port": remote_site.livestatus_port,
                    "encrypted": False,
                    "verify": False,
                },
                "proxy": {
                    "use_livestatus_daemon": "direct",
                },
                "connect_timeout": 2,
                "persistent_connection": False,
                "url_prefix": f"/{remote_site.id}/",
                "status_host": {"status_host_set": "disabled"},
                "disable_in_status_gui": False,
            },
            "configuration_connection": {
                "enable_replication": True,
                "url_of_remote_site": remote_site.internal_url,
                "disable_remote_configuration": True,
                "ignore_tls_errors": True,
                "direct_login_to_web_gui_allowed": True,
                "user_sync": {"sync_with_ldap_connections": "all"},
                "replicate_event_console": True,
                "replicate_extensions": True,
                "message_broker_port": remote_site.message_broker_port,
            },
        }
    )
    central_site.openapi.sites.login(remote_site.id)
    central_site.openapi.changes.activate_and_wait_for_completion(
        # this seems to be necessary to avoid sporadic CI failures
        force_foreign_changes=True,
    )
    try:
        yield
    finally:
        logger.warning("Hosts left: %s", central_site.openapi.hosts.get_all_names())
        central_site.openapi.sites.delete(remote_site.id)
        central_site.openapi.changes.activate_and_wait_for_completion(
            # this seems to be necessary to avoid sporadic CI failures
            force_foreign_changes=True,
        )


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(central_site: Site, tmp_path: Path) -> Path:
    if central_site.version.is_raw_edition():
        return install_agent_package(get_cre_agent_path(central_site))
    bake_agents(central_site)
    return download_and_install_agent_package(central_site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with agent_controller_daemon(installed_agent_ctl_in_unknown_state):
        yield installed_agent_ctl_in_unknown_state


@pytest.fixture(scope="session", name="ensure_cron")
def _run_cron() -> None:
    """Run cron for background jobs"""
    if not is_containerized():
        return

    logger.info("Ensure system cron is running")

    # cron  - Ubuntu, Debian, ...
    # crond - RHEL (AlmaLinux)
    cron_cmd = "crond" if Path("/etc/redhat-release").exists() else "cron"

    if not which(cron_cmd):
        raise RuntimeError(f"No cron executable found (tried {cron_cmd})")

    if run(["pgrep", cron_cmd], check=False, capture_output=True).returncode == 0:
        return

    # Start cron daemon. It forks an will keep running in the background
    run([cron_cmd], check=True, sudo=True)


# this is a temporary measure until we find a more robust implementation for the reloader
@pytest.fixture(scope="session", autouse=True)
def deactivate_automation_helper_reloader(
    central_site: Site,
    remote_site: Site,
    remote_site_2: Site,
) -> None:
    for site in (central_site, remote_site, remote_site_2):
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
