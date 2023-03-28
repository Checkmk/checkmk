#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/check_mk/gui/plugins/dashboard"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(
        path,
        """
# Initialize the UI environment to make loading of the dashlet possible.
from cmk.gui import main_modules
main_modules.load_plugins()

from cmk.gui.plugins.dashboard.utils import Dashlet, dashlet_registry

@dashlet_registry.register
class TestDashlet(Dashlet):
    @classmethod
    def type_name(cls):
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def description(cls):
        return "test"

    @classmethod
    def sort_index(cls) -> int:
        return 0

    @classmethod
    def is_selectable(cls) -> bool:
        return False

    def show(self):
        pass
""",
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_dashboard_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_dashboard_plugin.py").check_output().rstrip() == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/dashboard"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(
        path,
        """
# Initialize the UI environment to make loading of the dashlet possible.
from cmk.gui import main_modules
main_modules.load_plugins()

from cmk.gui.plugins.dashboard import Dashlet, dashlet_registry

@dashlet_registry.register
class TestDashlet(Dashlet):
    @classmethod
    def type_name(cls):
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def description(cls):
        return "test"

    @classmethod
    def sort_index(cls) -> int:
        return 0

    @classmethod
    def is_selectable(cls) -> bool:
        return False

    def show(self):
        pass
""",
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_dashboard_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_dashboard_plugin.py").check_output().rstrip() == "True"
    )
