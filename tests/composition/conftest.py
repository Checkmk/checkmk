#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.agent import agent_controller_daemon, install_agent_package
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import is_containerized, run

from tests.composition.constants import TEST_HOST_1
from tests.composition.utils import bake_agent, get_cre_agent_path

site_factory = get_site_factory(prefix="comp_")


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    yield from site_factory.get_test_site(
        "central", description=request.node.name, auto_restart_httpd=True
    )


@pytest.fixture(name="remote_site", scope="session")
def _remote_site(central_site: Site, request: pytest.FixtureRequest) -> Iterator[Site]:
    remote_site_generator = site_factory.get_test_site(
        "remote", description=request.node.name, auto_restart_httpd=True
    )
    try:  # make pylint happy
        remote_site = next(remote_site_generator)
    except StopIteration as e:
        raise RuntimeError("I should have received a remote site...") from e
    _add_remote_site_to_central_site(central_site=central_site, remote_site=remote_site)

    try:
        yield remote_site
    finally:
        # Teardown of remote site. We first stop the central site to avoid crashes due to
        # interruptions in the remote-central communication caused by the teardown.
        central_site.stop()
        yield from remote_site_generator


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


@pytest.fixture(scope="session", autouse=True)
def _run_cron() -> Iterator[None]:
    """Run cron for background jobs"""
    if not is_containerized():
        yield
        return
    for cron_cmd in (
        cron_cmds := (
            "cron",  # Ubuntu, Debian, ...
            "crond",  # RHEL (CentOS, AlmaLinux)
        )
    ):
        try:
            run(
                [cron_cmd],
                # calling cron spawns a background process, which fails if cron is already running
                check=False,
                sudo=True,
            )
        except FileNotFoundError:
            continue
        break
    else:
        raise RuntimeError(f"No cron executable found (tried {','.join(cron_cmds)})")
    yield
