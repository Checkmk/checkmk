#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.gui.plugins.userdb.utils import (
    UserConnector, user_connector_registry, CheckCredentialsResult)

@user_connector_registry.register
class TestConnector(UserConnector):
    @classmethod
    def type(cls):
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def short_title(cls):
        return "test"

    def is_enabled(self) -> bool:
        return False

    def check_credentials(self, user_id, password) -> CheckCredentialsResult:
        return None
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/check_mk/gui/plugins/userdb"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_userdb_plugin(site: Site) -> None:
    assert site.python_helper("helper_test_load_userdb_plugin.py").check_output().rstrip() == "True"


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/userdb"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_userdb_plugin(site: Site) -> None:
    assert site.python_helper("helper_test_load_userdb_plugin.py").check_output().rstrip() == "True"
