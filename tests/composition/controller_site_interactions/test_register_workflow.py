#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.testlib.agent import (
    register_controller,
    wait_until_host_has_services,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostName

from cmk.utils.agent_registration import HostAgentConnectionMode

logger = logging.getLogger(__name__)


def _test_register_workflow(
    *,
    site: Site,
    ctl_path: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> None:
    try:
        site.openapi.hosts.create(hostname=hostname, attributes=dict(host_attributes))
        site.openapi.changes.activate_and_wait_for_completion()

        register_controller(ctl_path, site, hostname)

        logger.info("Waiting for controller to open TCP socket or push data")
        wait_until_host_receives_data(site, hostname)

        site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname)
        site.openapi.changes.activate_and_wait_for_completion()

        wait_until_host_has_services(
            site,
            hostname,
            timeout=30,
            interval=10,
        )
    finally:
        site.openapi.hosts.delete(hostname=hostname)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@pytest.mark.skip_if_not_containerized
def test_register_workflow_pull(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_register_workflow(
        site=central_site,
        ctl_path=agent_ctl,
        hostname=HostName("pull-host"),
        host_attributes={"ipaddress": "127.0.0.1"},
    )


@pytest.mark.skip_if_not_containerized
@pytest.mark.skip_if_not_edition("cloud", "managed")
def test_register_workflow_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_register_workflow(
        site=central_site,
        ctl_path=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={
            "cmk_agent_connection": HostAgentConnectionMode.PUSH.value,
            "tag_address_family": "no-ip",
        },
    )
