#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from tests.testlib.agent import wait_until_host_has_services, wait_until_host_receives_data
from tests.testlib.site import Site
from tests.testlib.utils import run

from cmk.ccc.hostaddress import HostName

logger = logging.getLogger(__name__)


@pytest.mark.skip_if_not_containerized
def test_proxy_register_import_workflow(
    *,
    central_site: Site,
    agent_ctl: Path,
) -> None:
    hostname = HostName("proxy-host")
    central_site.openapi.hosts.create(hostname=hostname, attributes={"ipaddress": "127.0.0.1"})
    central_site.openapi.changes.activate_and_wait_for_completion()

    try:
        proxy_registration_proc = run(
            [
                agent_ctl.as_posix(),
                "proxy-register",
                "--server",
                central_site.http_address,
                "--site",
                central_site.id,
                "--hostname",
                hostname,
                "--user",
                "cmkadmin",
                "--password",
                central_site.admin_password,
                "--trust-cert",
            ],
            sudo=True,
        )
        run(
            [agent_ctl.as_posix(), "import"],
            sudo=True,
            text=True,
            input_=proxy_registration_proc.stdout,
        )

        logger.info("Waiting for controller to open TCP socket or push data")
        wait_until_host_receives_data(central_site, hostname)

        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname)
        central_site.openapi.changes.activate_and_wait_for_completion()

        wait_until_host_has_services(
            central_site,
            hostname,
            timeout=30,
            interval=10,
        )
    finally:
        central_site.openapi.hosts.delete(hostname=hostname)
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
