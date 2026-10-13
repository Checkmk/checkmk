#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup
from cmk.gui.quick_setup.v0_unstable.type_defs import QuickSetupId
from cmk.gui.watolib.configuration_bundles import BundleReferences, valid_special_agent_bundle
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, Host, make_folder_tree
from cmk.gui.watolib.rulesets import FolderRulesets, Rule
from cmk.utils.agent_registration import HostAgentConnectionMode


def test_push_agent_bundles_require_explicit_opt_in() -> None:
    assert not QuickSetup(
        title="Test", id=QuickSetupId("test"), stages=[], actions=[]
    ).allow_push_agent


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "push,allow_push,rule_count,host_count,expected",
    [
        pytest.param(False, False, 1, 1, True, id="existing-pull-bundle"),
        pytest.param(True, False, 0, 1, False, id="push-not-enabled"),
        pytest.param(True, True, 0, 1, True, id="push-enabled"),
        pytest.param(False, True, 0, 1, False, id="missing-pull-rule-still-invalid"),
        pytest.param(True, True, 0, 0, False, id="missing-source-host"),
        pytest.param(True, True, 0, 2, False, id="multiple-source-hosts"),
        pytest.param(True, True, 2, 1, False, id="multiple-rules"),
        pytest.param(False, True, 1, 1, True, id="pull-in-mixed-quick-setup"),
    ],
)
def test_only_supported_source_combinations_are_valid(
    push: bool, allow_push: bool, rule_count: int, host_count: int, expected: bool
) -> None:
    folder = make_folder_tree(Config()).root_folder()
    host = Host(
        folder,
        HostName("source"),
        {
            "tag_agent": "cmk-agent" if push else "special-agents",
            "cmk_agent_connection": (
                HostAgentConnectionMode.PUSH if push else HostAgentConnectionMode.PULL
            ).value,
        },
        None,
    )
    ruleset = FolderRulesets.load_folder_rulesets(folder).get("special_agents:aws")
    bundle = BundleReferences(
        hosts=[host] * host_count,
        rules=[Rule.from_ruleset(folder, ruleset, {}) for _ in range(rule_count)] or None,
    )

    assert valid_special_agent_bundle(bundle, allow_push_agent=allow_push) is expected


@pytest.fixture
def push_folder() -> Folder:
    tree = make_folder_tree(Config())
    return Folder.new(
        tree=tree,
        name="push",
        parent_folder=tree.root_folder(),
        attributes={
            "tag_agent": "cmk-agent",
            "cmk_agent_connection": HostAgentConnectionMode.PUSH.value,
        },
    )


@pytest.mark.usefixtures("load_config")
def test_inherited_push_settings_allow_a_ruleless_bundle(push_folder: Folder) -> None:
    host = Host(push_folder, HostName("source"), {}, None)

    assert valid_special_agent_bundle(BundleReferences(hosts=[host]), allow_push_agent=True)


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "host_attributes",
    [
        pytest.param({"cmk_agent_connection": HostAgentConnectionMode.PULL.value}, id="pull"),
        pytest.param({"tag_agent": "special-agents"}, id="special-agent-only"),
    ],
)
def test_host_overrides_can_disqualify_an_inherited_push_bundle(
    push_folder: Folder, host_attributes: HostAttributes
) -> None:
    host = Host(push_folder, HostName("source"), host_attributes, None)

    assert not valid_special_agent_bundle(BundleReferences(hosts=[host]), allow_push_agent=True)
