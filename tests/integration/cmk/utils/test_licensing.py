#!/usr/bin/env python3
#  #!/usr/bin/env python3
#  Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils import version as cmk_version
from cmk.utils.licensing import _CCE_SERVICES
from cmk.utils.type_defs import CheckPluginName
from cmk.utils.version import Edition

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.checking_classes import CheckPlugin


@pytest.mark.skipif(not cmk_version.is_cloud_edition(), reason="Only relevant on cloud edition")
def test_cce_service_list_on_cce_overfilled() -> None:
    """Check whether the list used to determine if a service is exclusive to CCE contains services
    not available on CCE. Remove them from _CCE_SERVICES list in cmk.utils.licensing if so."""
    agent_based_register.load_all_plugins()
    all_checks: set[str] = {str(p.name) for p in agent_based_register.iter_all_check_plugins()}
    assert _CCE_SERVICES.issubset(all_checks), f"{all_checks}"


@pytest.mark.skipif(not cmk_version.is_cloud_edition(), reason="Only relevant on cloud edition")
def test_cce_service_list_on_cce_incomplete() -> None:
    """Check whether the list used to determine if a service is exclusive to CCE contains all CCE
    services. Add missing ones to _CCE_SERVICES list in cmk.utils.licensing"""

    def is_cce_plugin(plugin: CheckPlugin) -> bool:
        if plugin.module and len(module_parts := plugin.module.split(".")) > 0:
            return Edition.CCE.short == module_parts[0]
        return False

    agent_based_register.load_all_plugins()
    all_cce_checks: set[str] = {
        str(p.name) for p in agent_based_register.iter_all_check_plugins() if is_cce_plugin(p)
    }
    assert _CCE_SERVICES == all_cce_checks


@pytest.mark.skipif(cmk_version.is_cloud_edition(), reason="Not relevant on cloud edition")
def test_cce_service_list_on_cee() -> None:
    """Check whether services on the list used to determine if a service is exclusive to CCE are
    available on CEE. Mark them as CCE or remove them from the _CCE_SERVICES list in
    cmk.utils.licensing"""
    agent_based_register.load_all_plugins()
    all_checks: set[CheckPluginName | str] = {
        p.service_name for p in agent_based_register.iter_all_check_plugins()
    }
    assert _CCE_SERVICES.isdisjoint(all_checks)
