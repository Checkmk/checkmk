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
    condition=os.getenv("DISTRO") == "almalinux-9",
    reason="May fail on EL* systems, investigating.",
)
def test_automatic_host_removal(
    central_site: Site,
    remote_site: Site,
) -> None:
    unresolvable_host_central = "not-dns-resolvable-central"
    unresolvable_host_remote = "not-dns-resolvable-remote"

    rule_id = central_site.openapi.create_rule(
        ruleset_name="automatic_host_removal",
        value=("enabled", {"checkmk_service_crit": 1}),
        conditions={
            "host_name": {
                "match_on": [unresolvable_host_remote, unresolvable_host_central],
                "operator": "one_of",
            }
        },
    )

    try:
        central_site.openapi.create_host(
            hostname=unresolvable_host_central,
            attributes={"site": central_site.id},
        )
        central_site.openapi.create_host(
            hostname=unresolvable_host_remote,
            attributes={"site": remote_site.id},
        )
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)

        def _host_removal_done() -> bool:
            hostnames = {_["id"] for _ in central_site.openapi.get_hosts()}
            return not hostnames.intersection({unresolvable_host_central, unresolvable_host_remote})

        logger.info("Waiting for hosts to be removed")
        wait_until(
            _host_removal_done,
            timeout=180,
            interval=20,
        )

        logger.info("Waiting for changes to be activated")
        wait_until(
            lambda: not central_site.openapi.pending_changes(),
            timeout=180,
            interval=20,
        )

    except Exception as exc:
        if not central_site.file_exists("var/check_mk/background_jobs/host_removal"):
            raise RuntimeError("Host removal background job was not even started") from exc
        raise
    finally:
        central_site.openapi.delete_rule(rule_id=rule_id)
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)
