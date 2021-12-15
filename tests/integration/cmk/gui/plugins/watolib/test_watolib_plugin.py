#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.gui.plugins.watolib.utils import ABCConfigDomain, config_domain_registry

@config_domain_registry.register
class ConfigDomainTest(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    def ident(cls):
        return "test"

    def config_dir(self):
        return cmk.utils.paths.default_config_dir + "/test.d/wato/"

    def activate(self):
        pass

    def default_globals(self):
        return {}
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    path = "local/lib/check_mk/gui/plugins/watolib/test_plugin.py"
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
from cmk.gui.plugins.watolib.utils import config_domain_registry
print("test" in config_domain_registry)
    """,
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_watolib_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    path = "local/share/check_mk/web/plugins/watolib/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_watolib_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )
