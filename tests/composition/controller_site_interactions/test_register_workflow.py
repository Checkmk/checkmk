#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.testlib.site import Site

from tests.composition.controller_site_interactions.common import query_hosts_service_count
from tests.composition.utils import execute

from cmk.utils.type_defs import HostName

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _test_register_workflow(
    *,
    site: Site,
    agent_ctl: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> None:
    site.openapi.create_host(hostname=hostname, attributes=dict(host_attributes))
    site.openapi.activate_changes_and_wait_for_completion()

    execute(
        [
            "sudo",
            agent_ctl.as_posix(),
            "register",
            "--server",
            site.http_address,
            "--site",
            site.id,
            "--hostname",
            hostname,
            "--user",
            "cmkadmin",
            "--password",
            site.admin_password,
            "--trust-cert",
        ]
    )

    LOGGER.info("Sleeping 60s to give controller time to open TCP socket or push data")
    time.sleep(60)

    # TODO (jh): Remove once we figured out how to handle live data fetching during discovery
    assert not site.execute(["cmk", "-d", hostname]).wait()

    site.openapi.discover_services_and_wait_for_completion(hostname)
    site.openapi.activate_changes_and_wait_for_completion()

    # Without this sleep, the test is flaky. Should probably be investigated.
    time.sleep(1)
    assert query_hosts_service_count(site, hostname) > 5


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


@pytest.mark.usefixtures("skip_if_not_plus_edition")
def test_register_workflow_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_register_workflow(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={
            "cmk_agent_connection": "push-agent",
            "tag_address_family": "no-ip",
        },
    )
