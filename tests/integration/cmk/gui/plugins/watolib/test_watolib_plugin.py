#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

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
    base_dir = "local/lib/check_mk/gui/plugins/watolib"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_watolib_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_watolib_plugin.py").check_output().rstrip() == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/watolib"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_text_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_watolib_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_watolib_plugin.py").check_output().rstrip() == "True"
    )
