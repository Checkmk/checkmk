#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
import time
from pathlib import Path

import pytest

from tests.testlib.site import Site

from tests.composition.controller_site_interactions.common import query_hosts_service_count
from tests.composition.utils import execute

from cmk.utils.type_defs import HostName

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


@pytest.mark.skip(
    "Controller / receiver architecture is being reworked, will be re-activated afterwards"
)
def test_proxy_register_import_workflow(
    *,
    central_site: Site,
    agent_ctl: Path,
) -> None:
    hostname = HostName("proxy-host")
    central_site.openapi.create_host(hostname=hostname, attributes={"ipaddress": "127.0.0.1"})
    central_site.openapi.activate_changes_and_wait_for_completion()

    proxy_registration_proc = execute(
        [
            "sudo",
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
        ]
    )
    subprocess.run(
        ["sudo", agent_ctl.as_posix(), "import"],
        text=True,
        input=proxy_registration_proc.stdout,
        capture_output=True,
        close_fds=True,
        check=True,
    )

    LOGGER.info("Sleeping 60s to give controller time to open TCP socket")
    time.sleep(60)

    # TODO (jh): Remove once we figured out how to handle live data fetching during discovery
    assert not central_site.execute(["cmk", "-d", hostname]).wait()

    central_site.openapi.discover_services_and_wait_for_completion(hostname)
    central_site.openapi.activate_changes_and_wait_for_completion()

    # Without this sleep, the test is flaky. Should probably be investigated.
    time.sleep(1)
    assert query_hosts_service_count(central_site, hostname) > 5
