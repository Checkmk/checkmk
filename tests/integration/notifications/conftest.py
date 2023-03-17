#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture(name="disable_checks", scope="module")
def fixture_disable_checks(site: Site) -> Iterator[None]:
    site.live.command("[%d] STOP_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] STOP_EXECUTING_SVC_CHECKS" % time.time())
    try:
        yield
    finally:
        site.live.command("[%d] START_EXECUTING_HOST_CHECKS" % time.time())
        site.live.command("[%d] START_EXECUTING_SVC_CHECKS" % time.time())


@pytest.fixture(name="disable_flap_detection", scope="module")
def fixture_disable_flap_detection(site: Site) -> Iterator[None]:
    site.live.command("[%d] DISABLE_FLAP_DETECTION" % time.time())
    try:
        yield
    finally:
        site.live.command("[%d] ENABLE_FLAP_DETECTION" % time.time())
