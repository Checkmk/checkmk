#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os

import pytest

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site
from tests.testlib.utils import wait_until

logger = logging.getLogger(__name__)


@skip_if_saas_edition
@pytest.mark.xfail(
    condition=os.getenv("DISTRO") in ("almalinux-9", "centos-8"),
    reason="May fail on EL* systems, investigating.",
)
def test_automatic_host_removal(
    central_site: Site,
    remote_site: Site,
) -> None:
    rule_id = central_site.openapi.create_rule(
        ruleset_name="automatic_host_removal",
        value=("enabled", {"checkmk_service_crit": 1}),
    )
    try:
        central_site.openapi.create_host(
            hostname=(unresolvable_host_central := "not-dns-resovable-central"),
            attributes={"site": central_site.id},
        )
        central_site.openapi.create_host(
            hostname=(unresolvable_host_remote := "not-dns-resovable-remote"),
            attributes={"site": remote_site.id},
        )
        central_site.openapi.activate_changes_and_wait_for_completion()

        def _host_removal_done() -> bool:
            hostnames = {
                _["id"]
                for _ in central_site.openapi.get(
                    "domain-types/host_config/collections/all", params={"include_links": False}
                ).json()["value"]
            }
            return not hostnames.intersection({unresolvable_host_central, unresolvable_host_remote})

        logger.info("Waiting for hosts to be removed")
        wait_until(
            _host_removal_done,
            timeout=150,
            interval=20,
        )

    finally:
        central_site.openapi.delete_rule(rule_id=rule_id)
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)
