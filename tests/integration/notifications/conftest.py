#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib import wait_until
from tests.testlib.site import Site


@pytest.fixture(name="disable_checks", scope="module")
def fixture_disable_checks(site: Site) -> Iterator[None]:
    site.live.command("STOP_EXECUTING_HOST_CHECKS")
    wait_until(lambda: site.is_global_flag_disabled("execute_host_checks"), timeout=60, interval=1)

    site.live.command("STOP_EXECUTING_SVC_CHECKS")
    wait_until(
        lambda: site.is_global_flag_disabled("execute_service_checks"), timeout=60, interval=1
    )

    try:
        yield
    finally:
        site.live.command("START_EXECUTING_HOST_CHECKS")
        wait_until(
            lambda: site.is_global_flag_enabled("execute_host_checks"), timeout=60, interval=1
        )
        site.live.command("START_EXECUTING_SVC_CHECKS")
        wait_until(
            lambda: site.is_global_flag_enabled("execute_service_checks"), timeout=60, interval=1
        )


@pytest.fixture(name="disable_flap_detection", scope="module")
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
