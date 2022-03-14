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
    path = "local/lib/check_mk/gui/plugins/wato/test_plugin.py"
    site.write_text_file(
        path,
        """
from cmk.gui.plugins.wato.utils import rulespec_registry, HostRulespec
from cmk.gui.plugins.wato.check_mk_configuration import RulespecGroupHostsMonitoringRulesVarious
from cmk.gui.valuespec import Dictionary

def _valuespec_host_groups():
    return Dictionary()


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupHostsMonitoringRulesVarious,
        match_type="dict",
        name="test",
        valuespec=_valuespec_host_groups,
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
from cmk.gui.plugins.wato.utils import rulespec_registry
print("test" in rulespec_registry)
    """,
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_wato_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    path = "local/share/check_mk/web/plugins/wato/test_plugin.py"
    site.write_text_file(
        path,
        """
from cmk.gui.plugins.wato import rulespec_registry, HostRulespec
from cmk.gui.plugins.wato.check_mk_configuration import RulespecGroupHostsMonitoringRulesVarious
from cmk.gui.valuespec import Dictionary

def _valuespec_host_groups():
    return Dictionary()


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupHostsMonitoringRulesVarious,
        match_type="dict",
        name="test",
        valuespec=_valuespec_host_groups,
    )
)
""",
    )
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_wato_plugin(site: Site, test_script: str) -> None:
    assert (
        subprocess.check_output(["python3", site.path(test_script)], encoding="utf-8").rstrip()
        == "True"
    )
