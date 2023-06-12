#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Generator

import pytest

from tests.testlib import CMKVersion
from tests.testlib.agent import (
    agent_controller_daemon,
    clean_agent_controller,
    install_agent_package,
)
from tests.testlib.site import get_site_factory, Site

from tests.composition.utils import bake_agent, get_cre_agent_path, is_containerized

site_number = -1


# The scope of the site fixtures is "module" to avoid that changing the site properties in a module
# may result in a test failing in another one
@pytest.fixture(name="central_site", scope="module")
def _central_site(request: pytest.FixtureRequest) -> Generator[Site, None, None]:
    # Using a different site for every module to avoid having issues when saving the results for the
    # tests: if you call SiteFactory.save_results() twice with the same site_id, it will crash
    # because the results are already there.
    global site_number
    site_number += 1

    yield from get_site_factory(prefix="comp_").get_test_site(
        f"{site_number}_central",
        description=request.node.name,
        auto_restart_httpd=True,
    )


@pytest.fixture(name="remote_site", scope="module")
def _remote_site(central_site: Site, request: pytest.FixtureRequest) -> Generator[Site, None, None]:
    for remote_site in get_site_factory(prefix="comp_").get_test_site(
        f"{site_number}_remote",
        description=request.node.name,
        auto_restart_httpd=True,
    ):
        central_site.open_livestatus_tcp(encrypted=False)
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
        yield remote_site


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="module")
def _installed_agent_ctl_in_unknown_state(central_site: Site) -> Path:
    return install_agent_package(_agent_package_path(central_site))


def _agent_package_path(site: Site) -> Path:
    if site.version.is_raw_edition():
        return get_cre_agent_path(site)
    return bake_agent(site)[1]


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
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
            subprocess.run(
                [cron_cmd],
                # calling cron spawns a background process, which fails if cron is already running
                check=False,
            )
        except FileNotFoundError:
            continue
        break
    else:
        raise RuntimeError(f"No cron executable found (tried {','.join(cron_cmds)})")
    yield


@pytest.fixture(name="skip_if_saas_edition")
def _skip_if_saas_edition(version: CMKVersion) -> None:
    if version.is_saas_edition():
        pytest.skip("Skipping test for SaaS edition")
