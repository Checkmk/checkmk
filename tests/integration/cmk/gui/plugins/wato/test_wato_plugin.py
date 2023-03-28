#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/check_mk/gui/plugins/wato"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
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


@pytest.mark.usefixtures("plugin_path")
def test_load_wato_plugin(site: Site) -> None:
    assert site.python_helper("helper_test_load_wato_plugin.py").check_output().rstrip() == "True"


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/wato"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
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
def test_load_legacy_wato_plugin(site: Site) -> None:
    assert site.python_helper("helper_test_load_wato_plugin.py").check_output().rstrip() == "True"
