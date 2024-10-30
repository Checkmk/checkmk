#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from pathlib import Path
from shutil import which
from typing import Literal

import pytest

from tests.testlib.agent import agent_controller_daemon, install_agent_package
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import is_containerized, run

from tests.composition.constants import TEST_HOST_1
from tests.composition.utils import bake_agent, get_cre_agent_path

site_factory = get_site_factory(prefix="comp_")

logger = logging.getLogger(__name__)


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    yield from site_factory.get_test_site(
        "central", description=request.node.name, auto_restart_httpd=True
    )


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
        site_name, description=site_description, auto_restart_httpd=True
    ) as remote_site:
        try:
            _add_remote_site_to_central_site(central_site=central_site, remote_site=remote_site)
            yield remote_site
        finally:
            # Stop the central site to avoid crashes due to interruptions in the remote-central communication caused by the teardown.
            central_site.stop()


def _add_remote_site_to_central_site(
    *,
    central_site: Site,
    remote_site: Site,
) -> None:
    central_site.openapi.create_site(
        {
            "basic_settings": {
                "alias": "Remote Testsite",
                "site_id": remote_site.id,
            },
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
    central_site.openapi.login_to_site(remote_site.id)
    central_site.openapi.activate_changes_and_wait_for_completion(
        # this seems to be necessary to avoid sporadic CI failures
        force_foreign_changes=True,
    )


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(central_site: Site) -> Path:
    return install_agent_package(_agent_package_path(central_site))


def _agent_package_path(site: Site) -> Path:
    if site.version.is_raw_edition():
        return get_cre_agent_path(site)
    return bake_agent(site, TEST_HOST_1)[1]


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
