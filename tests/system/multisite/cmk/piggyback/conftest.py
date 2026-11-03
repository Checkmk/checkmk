#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    HOSTNAME_SOURCE_CENTRAL,
    HOSTNAME_SOURCE_REMOTE,
    piggyback_hub_log_level,
    set_omd_config_piggyback_hub,
    setup_source_host,
)
from tests.system.multisite.utils import await_broker_ready
from tests.testlib.system.site import Site


@pytest.fixture(name="piggyback_env_two_site_setup", scope="package")
def _piggyback_env_two_site_setup(
    central_site: Site,
    remote_site: Site,
) -> Iterator[tuple[Site, Site]]:
    try:
        with (
            setup_source_host(central_site, central_site.id, HOSTNAME_SOURCE_CENTRAL),
            setup_source_host(central_site, remote_site.id, HOSTNAME_SOURCE_REMOTE),
            set_omd_config_piggyback_hub(central_site, "on"),
            set_omd_config_piggyback_hub(remote_site, "on"),
            piggyback_hub_log_level(central_site, remote_site),
        ):
            central_site.openapi.changes.activate_and_wait_for_completion()
            await_broker_ready(central_site, remote_site)
            yield central_site, remote_site
    finally:
        central_site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="piggyback_env_three_site_setup", scope="package")
def _piggyback_env_three_site_setup(
    piggyback_env_two_site_setup: tuple[Site, Site], remote_site_2: Site
) -> Iterator[tuple[Site, Site, Site]]:
    central_site, remote_site = piggyback_env_two_site_setup
    try:
        with set_omd_config_piggyback_hub(remote_site_2, "on"):
            central_site.openapi.changes.activate_and_wait_for_completion()
            await_broker_ready(remote_site_2)
            yield central_site, remote_site, remote_site_2
    finally:
        central_site.openapi.changes.activate_and_wait_for_completion()
