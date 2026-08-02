#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.sample_config import (
    init_wato_datastructures,
    sample_config_generator_registry,
    SampleConfigGeneratorGroups,
)
from cmk.utils.paths import omd_root


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


def test_init_wato_data_structures(request_context: None) -> None:
    init_wato_datastructures(folder_tree())
    assert Path(omd_root, "etc/check_mk/conf.d/wato/rules.mk").exists()
    assert Path(omd_root, "etc/check_mk/multisite.d/wato/tags.mk").exists()
    assert Path(omd_root, "etc/check_mk/conf.d/wato/global.mk").exists()
    assert not Path(omd_root, "var/check_mk/web/automation").exists()
    assert Path(omd_root, "var/check_mk/web/agent_registration").exists()
    assert Path(omd_root, "var/check_mk/web/agent_registration/automation.secret").exists()
    # the classic backend is the shipped default, no need to configure it
    assert "snmp_backend_default" not in load_configuration_settings()


@pytest.mark.usefixtures("request_context")
def test_sample_config_gen_groups() -> None:
    SampleConfigGeneratorGroups().generate(folder_tree())
    assert load_contact_group_information() == {
        "all": {
            "alias": "Everything",
        },
    }
