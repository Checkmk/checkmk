#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib import wait_until
from tests.testlib.site import Site


def test_load_dashboard_plugin(request, site: Site) -> None:
    plugin_path = "local/lib/check_mk/gui/plugins/dashboard/test_plugin.py"

    def cleanup():
        site.delete_file(plugin_path)

    request.addfinalizer(cleanup)

    assert not site.file_exists("tmp/dashboard_test")

    site.write_text_file(
        plugin_path,
        """
with open("%s", "w") as f:
    f.write("ding")
"""
        % site.path("tmp/dashboard_test"),
    )

    # Reload site apache to trigger the reload of our plugin
    site.omd("reload", "apache")

    def file_created():
        return site.file_exists("tmp/dashboard_test")

    # We need to wait some time for apache to initialize our application
    wait_until(file_created, timeout=60, interval=1)
