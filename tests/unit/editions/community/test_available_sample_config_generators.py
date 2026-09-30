#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.sample_config import sample_config_generator_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_generators() -> None:
    expected_generators = [
        "acknowledge_initial_werks",
        "contact_groups",
        "basic_wato_config",
        "create_initial_admin_user",
        "create_local_site_connection",
        "create_registration_automation_user",
        "builtin_host_labels",
        "ec_sample_rule_pack",
    ]

    assert sorted(sample_config_generator_registry.keys()) == sorted(expected_generators)


@pytest.mark.usefixtures("load_gui_plugins")
def test_get_sorted_generators() -> None:
    expected = [
        "contact_groups",
        "basic_wato_config",
        "create_local_site_connection",
        "acknowledge_initial_werks",
        "ec_sample_rule_pack",
        "create_initial_admin_user",
        "create_registration_automation_user",
        "builtin_host_labels",
    ]

    assert {g.ident() for g in sample_config_generator_registry.get_generators()} == set(expected)
