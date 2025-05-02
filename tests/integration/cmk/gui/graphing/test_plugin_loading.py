#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_load_metrics_plugin(site: Site) -> None:
    site.makedirs("local/lib/python3/cmk/plugins/collection/graphing")
    with site.copy_file(
        "graphing_plugin.py",
        "local/lib/python3/cmk/plugins/collection/graphing/test_plugin.py",
    ):
        assert site.python_helper("helper_test_plugin_loading.py").check_output().rstrip() == "True"
