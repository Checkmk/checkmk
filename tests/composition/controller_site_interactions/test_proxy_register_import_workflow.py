#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from pathlib import Path

from tests.testlib.agent import wait_until_host_receives_data
from tests.testlib.site import Site
from tests.testlib.utils import execute

from cmk.utils.type_defs import HostName

from ..utils import LOGGER
from .common import wait_until_host_has_services


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

    LOGGER.info("Waiting for controller to open TCP socket or push data")
    wait_until_host_receives_data(central_site, hostname)

    central_site.openapi.discover_services_and_wait_for_completion(hostname)
    central_site.openapi.activate_changes_and_wait_for_completion()

    wait_until_host_has_services(
        central_site,
        hostname,
        timeout=30,
        interval=10,
    )
