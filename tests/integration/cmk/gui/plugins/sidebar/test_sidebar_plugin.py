#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.gui.plugins.sidebar.utils import SidebarSnapin, snapin_registry

@snapin_registry.register
class CurrentTime(SidebarSnapin):
    @staticmethod
    def type_name():
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def description(cls):
        return "test"

    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        pass
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/check_mk/gui/plugins/sidebar"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_sidebar_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_sidebar_plugin.py").check_output().rstrip() == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/sidebar"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_sidebar_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_sidebar_plugin.py").check_output().rstrip() == "True"
    )
