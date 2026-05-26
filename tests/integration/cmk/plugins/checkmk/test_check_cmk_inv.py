#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

import cmk.base.check_cmk_inv
from tests.integration.linux_test_host import create_linux_test_host
from tests.testlib.site import Site


def test_inventory_as_check(site: Site, request: pytest.FixtureRequest) -> None:
    create_linux_test_host(request, site, "inv-test-host")
    site.activate_changes_and_wait_for_core_reload()

    # NOTE: What we *actually* want to do here is running the active check via the core.
    # The code below is relying on implementation details.
    p = site.run(["python3", "-m", cmk.base.check_cmk_inv.__name__, "inv-test-host"])

    assert re.match(r"Found \d+ inventory entries", p.stdout)
    assert p.stderr == ""
