#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)

_HOST_NAME = "builtin-labels-test-host"


@pytest.fixture(name="monitored_host", scope="module")
def monitored_host_fixture(site: Site) -> Iterator[str]:
    site.ensure_running()
    site.openapi.hosts.create(_HOST_NAME, attributes={"ipaddress": "127.0.0.1"})
    try:
        site.activate_changes_and_wait_for_core_reload()
        yield _HOST_NAME
    finally:
        site.openapi.hosts.delete(_HOST_NAME)
        site.activate_changes_and_wait_for_core_reload()


def test_host_has_builtin_site_label(site: Site, monitored_host: str) -> None:
    """A monitored host carries the builtin ``cmk/site`` label.

    Read via the monitoring REST host domain, which is livestatus-backed: this exercises the
    whole chain (config-generation writes the per-site builtin host labels file, core-config
    creation embeds ``labels_of_host()``, livestatus exposes it via the ``labels`` column).
    """
    response = site.openapi.get(f"/objects/host/{monitored_host}", params={"columns": ["labels"]})
    response.raise_for_status()
    labels = response.json()["extensions"]["labels"]
    assert labels["cmk/site"] == site.id
