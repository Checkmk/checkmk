#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    path = "local/lib/check_mk/gui/plugins/visuals/test_plugin.py"
    site.write_text_file(
        path,
        """
from cmk.gui.plugins.visuals.utils import filter_registry
from cmk.gui.plugins.visuals.filters import InputTextFilter
import cmk.gui.query_filters as query_filters

filter_registry.register(
    InputTextFilter(
        title="test",
        sort_index=102,
        info="host",
        query_filter=query_filters.TextQuery(
            ident="test", op="~~", negateable=False, request_var="test", column="host_test"
        ),
        description="",
        is_show_more=True,
    )
)
""",
    )
    yield path
    site.delete_file(path)


@pytest.fixture(name="test_script")
def fixture_test_script(site: Site) -> Iterator[str]:
    path = "test_script"
    site.write_text_file(
        path,
        """
from cmk.gui import main_modules
main_modules.load_plugins()
from cmk.gui.plugins.visuals.utils import filter_registry
print("test" in filter_registry)
    """,
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_visuals_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    path = "local/share/check_mk/web/plugins/visuals/test_plugin.py"
    site.write_text_file(
        path,
        """
from cmk.gui.plugins.visuals import filter_registry
from cmk.gui.plugins.visuals.filters import InputTextFilter
import cmk.gui.query_filters as query_filters

filter_registry.register(
    InputTextFilter(
        title="test",
        sort_index=102,
        info="host",
        query_filter=query_filters.TextQuery(
            ident="test", op="~~", negateable=False, request_var="test", column="host_test"
        ),
        description="",
        is_show_more=True,
    )
)
""",
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_visuals_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )
