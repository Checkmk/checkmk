#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import wait_until
from tests.testlib.site import Site

from .utils import LOGGER


def test_automatic_host_removal(
    central_site: Site,
    remote_site: Site,
) -> None:
    central_site.openapi.create_host(
        hostname="not-dns-resovable-central",
        attributes={
            "site": central_site.id,
            # CMK-12425: without an IP address, the Check_MK service will not go CRIT, even if the
            # hostname is not DNS-resolvable. Once this is fixed, we can remove the IP address.
            "ipaddress": "1.2.3.4",
        },
    )
    central_site.openapi.create_host(
        hostname="not-dns-resovable-remote",
        attributes={
            "site": remote_site.id,
            "ipaddress": "1.2.3.5",
        },
    )
    central_site.openapi.create_rule(
        ruleset_name="automatic_host_removal",
        value=("enabled", {"checkmk_service_crit": 1}),
    )
    central_site.openapi.activate_changes_and_wait_for_completion()

    def _no_hosts_exist() -> bool:
        return not central_site.openapi.get("domain-types/host_config/collections/all").json()[
            "value"
        ]

    LOGGER.info("Waiting for hosts to be removed")
    wait_until(
        _no_hosts_exist,
        timeout=120,
        interval=20,
    )
