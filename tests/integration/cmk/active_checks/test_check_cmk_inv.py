#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.site import Site


def test_inventory_as_check_unknown_host(site: Site) -> None:
    p = site.run(["lib/python3/cmk/plugins/checkmk/libexec/check_cmk_inv", "xyz."], check=False)
    assert p.returncode == 2, f"Command failed ({p.stdout!r}, {p.stderr!r})"
    assert p.stdout.startswith("Failed to lookup IPv4 address of")
    assert p.stderr == ""


def test_inventory_as_check(site: Site, request: pytest.FixtureRequest) -> None:
    create_linux_test_host(request, site, "inv-test-host")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("inv-test-host")
    site.activate_changes_and_wait_for_core_reload()

    p = site.run(["lib/python3/cmk/plugins/checkmk/libexec/check_cmk_inv", "inv-test-host"])
    assert re.match(r"Found \d+ inventory entries", p.stdout)
    assert p.stderr == ""
