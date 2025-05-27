#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version

from cmk.utils import paths

import cmk.gui.watolib.config_domain_name as utils


def test_registered_generators() -> None:
    expected_generators = [
        "acknowledge_initial_werks",
        "contact_groups",
        "basic_wato_config",
        "create_local_site_connection",
        "create_registration_automation_user",
        "ec_sample_rule_pack",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected_generators += [
            "cee_agent_bakery",
            "cee_rrd_config",
        ]

    assert sorted(utils.sample_config_generator_registry.keys()) == sorted(expected_generators)


def test_get_sorted_generators() -> None:
    expected = [
        "contact_groups",
        "basic_wato_config",
        "create_local_site_connection",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected += [
            "cee_rrd_config",
            "cee_agent_bakery",
        ]

    expected += [
        "acknowledge_initial_werks",
        "ec_sample_rule_pack",
        "create_registration_automation_user",
    ]

    assert [g.ident() for g in utils.sample_config_generator_registry.get_generators()] == expected
