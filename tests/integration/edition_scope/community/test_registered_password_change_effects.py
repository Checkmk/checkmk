#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.passwords import password_change_effect_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_password_change_effects() -> None:
    assert (
        password_change_effect_registry.affected_domains_add,
        password_change_effect_registry.affected_domains_edit,
        password_change_effect_registry.affected_domains_delete,
    ) == (["check_mk"], ["check_mk"], ["check_mk"])
