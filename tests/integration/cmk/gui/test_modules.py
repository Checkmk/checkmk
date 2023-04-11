#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib import wait_until
from tests.testlib.site import Site


@pytest.fixture(name="plugin_path")
def fixture_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/check_mk/gui/plugins/dashboard"
    site.makedirs(base_dir)
    plugin_path = f"{base_dir}/test_plugin.py"

    site.write_text_file(
        plugin_path,
        """
with open("%s", "w") as f:
    f.write("ding")
"""
        % site.path("tmp/dashboard_test"),
    )

    try:
        yield plugin_path
    finally:
        site.delete_file(plugin_path)


@pytest.fixture(name="result_file")
def fixture_result_file(site: Site) -> Iterator[None]:
    assert not site.file_exists("tmp/dashboard_test")
    try:
        yield
    finally:
        if site.file_exists("tmp/dashboard_test"):
            site.delete_file("tmp/dashboard_test")


@pytest.mark.usefixtures("plugin_path", "result_file")
def test_load_dashboard_plugin(request: pytest.FixtureRequest, site: Site) -> None:
    # Reload site apache to trigger the reload of our plugin
    site.omd("reload", "apache")

    def file_created():
        return site.file_exists("tmp/dashboard_test")

    # We need to wait some time for apache to initialize our application
    wait_until(file_created, timeout=60, interval=1)
