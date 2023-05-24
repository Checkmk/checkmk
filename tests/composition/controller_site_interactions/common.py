#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tests.testlib import wait_until
from tests.testlib.site import Site
from tests.testlib.utils import execute

from cmk.utils.type_defs import HostName


def register_controller(
    contoller_path: Path,
    site: Site,
    hostname: HostName,
) -> None:
    execute(
        [
            "sudo",
            contoller_path.as_posix(),
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


def controller_status_json(contoller_path: Path) -> Mapping[str, Any]:
    return json.loads(
        execute(
            [
                "sudo",
                contoller_path.as_posix(),
                "status",
                "--json",
            ]
        ).stdout
    )


def wait_until_host_receives_data(
    site: Site,
    hostname: HostName,
    *,
    timeout: int = 120,
    interval: int = 20,
) -> None:
    wait_until(
        lambda: not site.execute(["cmk", "-d", hostname]).wait(),
        timeout=timeout,
        interval=interval,
    )


def wait_until_host_has_services(
    site: Site,
    hostname: HostName,
    *,
    n_services_min: int = 5,
    timeout: int = 120,
    interval: int = 20,
) -> None:
    wait_until(
        lambda: _query_hosts_service_count(site, hostname) > n_services_min,
        timeout=timeout,
        interval=interval,
    )


def _query_hosts_service_count(site: Site, hostname: HostName) -> int:
    return (
        len(services_response.json()["value"])
        # the host might not yet exist at the point where we start waiting
        if (
            services_response := site.openapi.get(f"objects/host/{hostname}/collections/services")
        ).ok
        else 0
    )
