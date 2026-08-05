#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.mark.skip_if_edition("saas")
@pytest.mark.xfail(
    condition=os.getenv("DISTRO") == "almalinux-9",
    reason="May fail on EL* systems, investigating.",
)
def test_automatic_host_removal(
    central_site: Site,
    remote_site: Site,
) -> None:
    assert not central_site.openapi.changes.get_pending()

    hostname_central = "auto-remove-central"
    hostname_remote = "auto-remove-remote"

    with disable_core_check_scheduling(central_site), disable_core_check_scheduling(remote_site):
        central_site.openapi.hosts.create(
            hostname=hostname_central,
            attributes={
                "ipaddress": "127.0.0.1",
                "site": central_site.id,
            },
        )
        central_site.openapi.hosts.create(
            hostname=hostname_remote,
            attributes={
                "ipaddress": "127.0.0.1",
                "site": remote_site.id,
            },
        )

        rule_id = central_site.openapi.rules.create(
            ruleset_name="automatic_host_removal",
            value=("enabled", {"checkmk_service_crit": 1}),
            conditions={
                "host_name": {
                    "match_on": [hostname_remote, hostname_central],
                    "operator": "one_of",
                }
            },
        )

        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)

        central_site.send_service_check_result(hostname_central, "Check_MK", 2, "FAKE CRIT")
        remote_site.send_service_check_result(hostname_remote, "Check_MK", 2, "FAKE CRIT")

        try:

            def _host_removal_done() -> bool:
                hostnames = set(central_site.openapi.hosts.get_all_names())
                return not hostnames.intersection({hostname_central, hostname_remote})

            logger.info("Waiting for hosts to be removed")
            wait_until(
                _host_removal_done,
                timeout=180,
                interval=20,
            )

            logger.info("Waiting for changes to be activated")
            wait_until(
                lambda: not central_site.openapi.changes.get_pending(),
                timeout=180,
                interval=20,
            )

        finally:
            central_site.openapi.rules.delete(rule_id=rule_id)
            if hostname_central in central_site.openapi.hosts.get_all_names():
                central_site.openapi.hosts.delete(hostname_central)
            if hostname_remote in central_site.openapi.hosts.get_all_names():
                central_site.openapi.hosts.delete(hostname_remote)
            central_site.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=True
            )


@contextmanager
def disable_core_check_scheduling(site: Site) -> Iterator[None]:
    site.stop_host_checks()
    site.stop_active_services()
    try:
        yield
    finally:
        site.start_host_checks()
        site.start_active_services()
