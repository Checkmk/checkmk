#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.watolib.rulespecs import rulespec_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_every_special_agent_quick_setup_configures_a_registered_ruleset() -> None:
    special_agent_quick_setups = {
        ident for ident in quick_setup_registry if ident.startswith("special_agents:")
    }
    assert special_agent_quick_setups
    assert special_agent_quick_setups - set(rulespec_registry) == set()
