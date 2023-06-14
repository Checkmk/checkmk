#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.testlib.agent import (
    register_controller,
    wait_until_host_has_services,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site

from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.type_defs import HostName

from ..utils import LOGGER


def _test_register_workflow(
    *,
    site: Site,
    agent_ctl: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> None:
    site.openapi.create_host(hostname=hostname, attributes=dict(host_attributes))
    site.openapi.activate_changes_and_wait_for_completion()

    register_controller(agent_ctl, site, hostname)

    LOGGER.info("Waiting for controller to open TCP socket or push data")
    wait_until_host_receives_data(site, hostname)

    site.openapi.discover_services_and_wait_for_completion(hostname)
    site.openapi.activate_changes_and_wait_for_completion()

    wait_until_host_has_services(
        site,
        hostname,
        timeout=30,
        interval=10,
    )


def test_register_workflow_pull(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_register_workflow(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("pull-host"),
        host_attributes={"ipaddress": "127.0.0.1"},
    )


@pytest.mark.usefixtures("skip_if_not_cloud_edition")
def test_register_workflow_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_register_workflow(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={
            "cmk_agent_connection": HostAgentConnectionMode.PUSH.value,
            "tag_address_family": "no-ip",
        },
    )
