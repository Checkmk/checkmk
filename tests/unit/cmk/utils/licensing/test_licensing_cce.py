#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

import cmk.utils.version as cmk_version
from cmk.utils.licensing import _CCE_SERVICES

from cmk.base.api.agent_based.checking_classes import CheckPlugin


@pytest.mark.skipif(
    not cmk_version.is_cloud_edition(), reason="CCE plugins only available in cloud edition"
)
def test_cce_services_in_list(fix_register: FixRegister) -> None:
    """Make sure cmk.utils.licensing._CCE_SERVICES reflects the registered checks in cce folder"""

    def is_cce_plugin(plugin: CheckPlugin) -> bool:
        if plugin.module and len(module_parts := plugin.module.split(".")) > 0:
            return cmk_version.Edition.CCE.short == module_parts[0]
        return False

    all_cce_checks = {str(p.name) for p in fix_register.check_plugins.values() if is_cce_plugin(p)}
    assert _CCE_SERVICES == all_cce_checks
