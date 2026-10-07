#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import override

import pytest

from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.hosts_and_folders import folder_tree, FolderTree
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.watolib.sample_config import (
    init_wato_datastructures,
    sample_config_generator_registry,
    SampleConfigGenerator,
    SampleConfigGeneratorGroups,
    SampleConfigGeneratorRegistry,
)
from cmk.utils.paths import omd_root


@pytest.mark.usefixtures("request_context")
def test_init_wato_data_structures() -> None:
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
def test_sample_config_ships_no_rules_of_deprecated_rule_sets() -> None:
    tree = folder_tree()
    sample_config_generator_registry["basic_wato_config"]().generate(tree)

    deprecated_with_rules = [
        ruleset.name
        for ruleset in AllRulesets.load_all_rulesets(tree).get_rulesets().values()
        if ruleset.is_deprecated() and ruleset.num_rules()
    ]

    assert deprecated_with_rules == []


@pytest.mark.usefixtures("request_context")
def test_sample_config_gen_groups() -> None:
    SampleConfigGeneratorGroups().generate(folder_tree())
    assert load_contact_group_information() == {
        "all": {
            "alias": "Everything",
        },
    }


def _make_generator(name: str, index: int) -> type[SampleConfigGenerator]:
    class _Generator(SampleConfigGenerator):
        @classmethod
        @override
        def ident(cls) -> str:
            return name

        @classmethod
        @override
        def sort_index(cls) -> int:
            return index

        @override
        def generate(self, tree: FolderTree) -> None:
            pass

    return _Generator


def test_generators_are_executed_by_sort_index() -> None:
    registry = SampleConfigGeneratorRegistry()
    registry.register(_make_generator("last", 30))
    registry.register(_make_generator("first", 10))
    registry.register(_make_generator("middle", 20))

    assert [g.ident() for g in registry.get_generators()] == ["first", "middle", "last"]
