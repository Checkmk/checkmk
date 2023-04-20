#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.bi.lib import ABCBISearch, ABCBISearcher, SearchKind, bi_search_registry
from cmk.bi.schema import Schema
from cmk.utils.macros import MacroMapping

@bi_search_registry.register
class TestBISearch(ABCBISearch):
    @classmethod
    def kind(cls) -> SearchKind:
        return "test"

    @classmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    def serialize(self):
        return {
            "type": self.kind(),
            "conditions": {},
        }

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        return []
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    path = "local/lib/check_mk/gui/plugins/bi/test_plugin.py"
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
from cmk.gui.plugins.bi.utils import bi_search_registry
print("test" in bi_search_registry)
    """,
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_bi_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )
