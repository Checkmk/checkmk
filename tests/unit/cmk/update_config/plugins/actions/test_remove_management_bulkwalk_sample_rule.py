#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.site_config import all_activation_sites
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.update_config.plugins.actions.remove_management_bulkwalk_sample_rule import (
    remove_management_bulkwalk_sample_rule,
    RULESET_NAME,
    SAMPLE_RULE_ID,
)

LOGGER = logging.getLogger("test")


def _make_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=all_activation_sites(active_config.sites),
        local_site=omd_site(),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


def _make_rulesets(folder: Folder, value: bool, condition: dict[str, object]) -> RulesetCollection:
    ruleset = Ruleset(RULESET_NAME)
    ruleset.append_rule(
        folder,
        Rule.from_config(
            folder,
            ruleset,
            {
                "id": SAMPLE_RULE_ID,
                "value": value,
                "condition": condition,
                "options": {"description": "All management boards use SNMPv2 and bulk walk"},
            },
        ),
    )
    return RulesetCollection({RULESET_NAME: ruleset})


def _remove(tree: FolderTree, all_rulesets: RulesetCollection) -> bool:
    return remove_management_bulkwalk_sample_rule(
        tree, all_rulesets, _make_pending_changes(), LOGGER
    )


def _create_host(tree: FolderTree, attributes: HostAttributes) -> None:
    tree.root_folder().create_hosts(
        [(HostName("host"), attributes, None)],
        pprint_value=False,
        pending_changes=_make_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )


def _create_subfolder(tree: FolderTree, attributes: HostAttributes) -> Folder:
    return tree.root_folder().create_subfolder(
        "sub",
        "sub",
        attributes,
        pprint_value=False,
        pending_changes=_make_pending_changes(),
        acting_user=LoggedInSuperUser(),
    )


@pytest.mark.usefixtures("request_context")
def test_removes_unchanged_sample_rule(tree: FolderTree) -> None:
    all_rulesets = _make_rulesets(tree.root_folder(), True, {})

    assert _remove(tree, all_rulesets)

    assert not all_rulesets.get(RULESET_NAME).num_rules()


@pytest.mark.usefixtures("request_context")
def test_removes_sample_rule_with_no_management_board_set_explicitly(tree: FolderTree) -> None:
    _create_host(tree, {"management_protocol": None})
    all_rulesets = _make_rulesets(tree.root_folder(), True, {})

    assert _remove(tree, all_rulesets)

    assert not all_rulesets.get(RULESET_NAME).num_rules()


@pytest.mark.parametrize("protocol", ["snmp", "ipmi"])
@pytest.mark.usefixtures("request_context")
def test_keeps_sample_rule_with_management_board_on_host(
    tree: FolderTree, protocol: Literal["snmp", "ipmi"]
) -> None:
    _create_host(tree, {"management_protocol": protocol})
    all_rulesets = _make_rulesets(tree.root_folder(), True, {})

    assert not _remove(tree, all_rulesets)

    assert all_rulesets.get(RULESET_NAME).num_rules() == 1


@pytest.mark.usefixtures("request_context")
def test_keeps_sample_rule_with_management_board_on_folder(tree: FolderTree) -> None:
    _create_subfolder(tree, {"management_protocol": "snmp"})
    all_rulesets = _make_rulesets(tree.root_folder(), True, {})

    assert not _remove(tree, all_rulesets)

    assert all_rulesets.get(RULESET_NAME).num_rules() == 1


@pytest.mark.parametrize(
    "value, condition",
    [
        pytest.param(False, {}, id="changed value"),
        pytest.param(True, {"host_name": ["host"]}, id="changed condition"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_keeps_changed_sample_rule(
    tree: FolderTree, value: bool, condition: dict[str, object]
) -> None:
    all_rulesets = _make_rulesets(tree.root_folder(), value, condition)

    assert not _remove(tree, all_rulesets)

    assert all_rulesets.get(RULESET_NAME).num_rules() == 1


@pytest.mark.usefixtures("request_context")
def test_keeps_sample_rule_moved_to_subfolder(tree: FolderTree) -> None:
    all_rulesets = _make_rulesets(_create_subfolder(tree, {}), True, {})

    assert not _remove(tree, all_rulesets)

    assert all_rulesets.get(RULESET_NAME).num_rules() == 1
