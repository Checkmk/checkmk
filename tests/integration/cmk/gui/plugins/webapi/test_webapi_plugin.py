#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.gui.plugins.webapi.utils import APICallCollection, api_call_collection_registry

@api_call_collection_registry.register
class TestCollection(APICallCollection):
    def get_api_calls(self):
        return {}
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    path = "local/lib/check_mk/gui/plugins/webapi/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
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
from cmk.gui.plugins.webapi.utils import api_call_collection_registry
print("TestCollection" in api_call_collection_registry)
    """,
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_webapi_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    path = "local/share/check_mk/web/plugins/webapi/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_webapi_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )
