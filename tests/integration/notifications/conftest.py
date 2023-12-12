#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import wait_until


@pytest.fixture(name="disable_checks")
def fixture_disable_checks(site: Site) -> Iterator[None]:
    site.stop_host_checks()
    site.stop_active_services()
    try:
        yield
    finally:
        site.start_host_checks()
        site.start_active_services()


@pytest.fixture(name="disable_flap_detection")
def fixture_disable_flap_detection(site: Site) -> Iterator[None]:
    site.live.command("DISABLE_FLAP_DETECTION")
    wait_until(
        lambda: site.is_global_flag_disabled("enable_flap_detection"), timeout=60, interval=1
    )
    try:
        yield
    finally:
        site.live.command("ENABLE_FLAP_DETECTION")
        wait_until(
            lambda: site.is_global_flag_enabled("enable_flap_detection"), timeout=60, interval=1
        )
