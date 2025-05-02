#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_load_userdb_plugin(site: Site) -> None:
    with site.copy_file(
        "userdb_plugin.py", "local/lib/python3/cmk/gui/plugins/userdb/test_plugin.py"
    ):
        assert (
            site.python_helper("helper_test_load_userdb_plugin.py").check_output().rstrip()
            == "True"
        )


def test_load_legacy_userdb_plugin(site: Site) -> None:
    with site.copy_file(
        "userdb_plugin.py", "local/share/check_mk/web/plugins/userdb/test_plugin.py"
    ):
        assert (
            site.python_helper("helper_test_load_userdb_plugin.py").check_output().rstrip()
            == "True"
        )
