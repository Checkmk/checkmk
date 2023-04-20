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
        attributes={"site": central_site.id},
    )
    central_site.openapi.create_host(
        hostname="not-dns-resovable-remote",
        attributes={"site": remote_site.id},
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
