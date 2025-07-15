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
    download_and_install_agent_package,
    register_controller,
    wait_for_agent_cache_omd_status,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site
from tests.testlib.utils import ServiceInfo
from tests.testlib.version import edition_from_env

from cmk.ccc.hostaddress import HostName

from cmk.utils.rulesets.definition import RuleGroup

logger = logging.getLogger(__name__)


_RESCHEDULES_LIMIT = 2


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="module")
def _installed_agent_ctl_in_unknown_state(
    site: Site, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    return download_and_install_agent_package(site, tmp_path_factory.mktemp("agent"))


@pytest.fixture(name="agent_ctl", scope="module")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with agent_controller_daemon(installed_agent_ctl_in_unknown_state):
        yield installed_agent_ctl_in_unknown_state


@pytest.fixture(
    name="host_services", scope="function", params=[False, True], ids=["passive", "active"]
)
def _host_services(
    site: Site, agent_ctl: Path, request: pytest.FixtureRequest
) -> Iterator[dict[str, ServiceInfo]]:
    active_mode = request.param
    if active_mode and edition_from_env().is_saas_edition():
        pytest.skip("Active mode requires pull agent, which is not available in CSE")
    rule_id = None
    hostname = HostName(f"host-{request.node.callspec.id}")
    site.openapi.hosts.create(
        hostname, attributes={"ipaddress": site.http_address, "site": site.id}
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        register_controller(agent_ctl, site, hostname, site_address="127.0.0.1")
        wait_until_host_receives_data(site, hostname)
        wait_for_agent_cache_omd_status(site)

        site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion([str(hostname)])
        site.openapi.changes.activate_and_wait_for_completion()
        # discover again, this time taking the new host labels into account
        site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion([str(hostname)])
        site.openapi.changes.activate_and_wait_for_completion()

        if active_mode:
            site.reschedule_services(hostname)
        else:
            if not edition_from_env().is_saas_edition():
                # Reduce check interval to 3 seconds
                rule_id = site.openapi.rules.create(
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
            site.wait_for_services_state_update(
                hostname,
                "Check_MK",
                expected_state=0,
                wait_timeout=65,
                max_count=_RESCHEDULES_LIMIT,
            )

        host_services = site.get_host_services(hostname)

        yield host_services
    except Exception as e:
        logger.error("Failed to retrieve services from the host. Reason: %s", str(e))
        raise e
    finally:
        if rule_id:
            site.openapi.rules.delete(rule_id)
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


def test_checks_sanity(host_services: dict[str, ServiceInfo]) -> None:
    """Assert sanity of the discovered checks.

    Depending on the parameter the test will be executed in two modes:
    - active - the Check_MK service is rescheduled to update the state of the services
    - passive - the check interval is minimized and the state of the services is
    updated without any additional actions

    Sanity here means that
     * there are services
     * all services leave their pending state after the number of reschedules provided in
       the fixture (ideal would be 1, but some poorly written checks might need more
       iterations to initialize all their counters)

    """
    assert host_services


def _runs_cmc(site: Site) -> bool:
    return site.omd("config", "show", "CORE", check=True).stdout.strip() == "cmc"


def test_shipped_ps_disocvery(host_services: dict[str, ServiceInfo], site: Site) -> None:
    expected_ps_services = {  # compare cmk.gui.watolib.sample_config
        f"Process {site.id} agent receiver",
        f"Process {site.id} apache",
        f"Process {site.id} automation helpers",
        f"Process {site.id} event console",
        # jaeger and piggyback-hub are not enabled in this test
        # f"Process {site.id} jaeger",
        # f"Process {site.id} piggyback hub",
        # f"Process {site.id} rabbitmq",
        f"Process {site.id} redis-server",
        f"Process {site.id} rrdcached",
    }

    if _runs_cmc(site):
        expected_ps_services |= {
            f"Process {site.id} active check helpers",
            f"Process {site.id} alert helper",
            f"Process {site.id} checker helpers",
            f"Process {site.id} cmc",
            f"Process {site.id} fetcher helpers",
            f"Process {site.id} livestatus proxy",
            f"Process {site.id} notification spooler",
            f"Process {site.id} notify helper",
            # f"Process {site.id} real-time helper",  # not enabled
            f"Process {site.id} rrd helper",
        }
    if not site.edition.is_raw_edition():
        expected_ps_services |= {
            f"Process {site.id} dcd",
        }

    assert {k for k in host_services if k.startswith("Process")} == expected_ps_services
