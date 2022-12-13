#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

from tests.testlib.site import Site

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


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

    LOGGER.info("Sleeping 65s to wait for hosts to be removed")
    time.sleep(65)

    assert not central_site.openapi.get("domain-types/host_config/collections/all").json()["value"]
