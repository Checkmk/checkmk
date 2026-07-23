#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Iterator

import pytest
import requests

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site


@pytest.fixture(name="plugin_path")
def fixture_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/python3/cmk/gui/plugins/dashboard"
    site.makedirs(base_dir)
    plugin_path = f"{base_dir}/test_plugin.py"

    site.write_file(
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
@pytest.mark.skip_if_edition("cloud")
def test_load_dashboard_plugin_omd_restart(request: pytest.FixtureRequest, site: Site) -> None:
    # Restart apache so new WSGI workers pick up the plugin.
    # A reload is not sufficient because old workers may still serve requests
    # without loading the new plugin.
    site.omd("restart", "apache")

    def file_created():
        # Each request may be the one that hits a freshly started WSGI worker
        # which loads the plugin at startup and writes the marker file.
        requests.get(site.url_for_path("login.py"))
        return site.file_exists("tmp/dashboard_test")

    # We need to wait some time for apache to initialize our application
    wait_until(file_created, timeout=60, interval=1)
