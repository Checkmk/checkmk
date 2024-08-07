#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.agent import (
    agent_controller_daemon,
    clean_agent_controller,
    download_and_install_agent_package,
    register_controller,
    wait_for_agent_cache_omd_status,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status, ServiceInfo
from tests.testlib.version import version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets.definition import RuleGroup

logger = logging.getLogger(__name__)


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(site: Site, tmp_path: Path) -> Path:
    return download_and_install_agent_package(site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state


@pytest.fixture(
    name="host_services", scope="function", params=[False, True], ids=["passive", "active"]
)
def _host_services(
    site: Site, agent_ctl: Path, request: pytest.FixtureRequest
) -> Iterator[dict[str, ServiceInfo]]:
    active_mode = request.param
    if active_mode and version_from_env().is_saas_edition():
        pytest.skip("Active mode requires pull agent, which is not available in CSE")
    rule_id = None
    hostname = HostName(f"host-{request.node.callspec.id}")
    site.openapi.create_host(hostname, attributes={"ipaddress": site.http_address, "site": site.id})
    site.activate_changes_and_wait_for_core_reload()

    try:
        register_controller(agent_ctl, site, hostname, site_address="127.0.0.1")
        wait_until_host_receives_data(site, hostname)
        wait_for_agent_cache_omd_status(site)
        site.openapi.bulk_discover_services_and_wait_for_completion([str(hostname)])
        site.openapi.activate_changes_and_wait_for_completion()
        if active_mode:
            site.reschedule_services(hostname)
        else:
            if not version_from_env().is_saas_edition():
                # Reduce check interval to 3 seconds
                rule_id = site.openapi.create_rule(
                    ruleset_name=RuleGroup.ExtraServiceConf("check_interval"),
                    value=0.05,
                    conditions={
                        "service_description": {
                            "match_on": ["Check_MK$"],
                            "operator": "one_of",
                        },
                    },
                )
                site.activate_changes_and_wait_for_core_reload()
            wait_timeout = 5 if not version_from_env().is_saas_edition() else 65
            site.wait_for_services_state_update(hostname, "Check_MK", 0, wait_timeout, 10)

        host_services = site.get_host_services(hostname)

        yield host_services

    except Exception:
        logger.error("Failed to retrieve services from the host.")
        raise

    finally:
        if rule_id:
            site.openapi.delete_rule(rule_id)
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()


def test_checks_sanity(host_services: dict[str, ServiceInfo]) -> None:
    """Assert sanity of the discovered checks. Depending on the parameter the test
    will be executed in two modes:
        - active - the Check_MK service is rescheduled to update the state of the services
        - passive - the check interval is minimized and the state of the services is
        updated without any additional actions
    """
    ok_services = get_services_with_status(host_services, 0)
    not_ok_services = [service for service in host_services if service not in ok_services]
    err_msg = (
        f"The following services are not in state 0: {not_ok_services} "
        f"(Details: {[host_services[s] for s in not_ok_services]})"
    )

    assert len(host_services) == len(ok_services) > 0, err_msg
