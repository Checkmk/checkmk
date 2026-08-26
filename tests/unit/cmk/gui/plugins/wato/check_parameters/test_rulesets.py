#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Tests in this file exercise the legacy rulesets API (Rule.from_config,
# Ruleset.replace_folder_config, ordering helpers) using rulesets that are
# registered as side effects of importing cmk.gui.plugins.wato.check_parameters.*
# (e.g. inventory_processes_rules, CheckgroupParameters("local")). They live in
# this directory so the test target's :check_parameters dep is the carrier of
# those registrations.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

from collections.abc import Iterator, Mapping

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config, get_default_config, make_config_object
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib import rulesets
from cmk.gui.watolib import rulesets as gui_rulesets_module
from cmk.gui.watolib.configuration_bundle_store import BundleId
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, make_folder_tree
from cmk.gui.watolib.pending_changes import (
    NoopPendingChangesStore,
    PendingChanges,
)
from cmk.gui.watolib.rulesets import Rule, RuleOptions, Ruleset
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.ruleset_matcher.matcher import RuleOptionsSpec, RulesetName, RuleSpec
from cmk.ruleset_matcher.tags import get_effective_tag_config
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.redis import disable_redis


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.fixture(name="config")
def fixture_config() -> Config:
    raw_config = get_default_config()
    raw_config["tags"] = get_effective_tag_config(raw_config["wato_tags"])
    return make_config_object(raw_config)


@pytest.fixture(name="tree")
def fixture_tree(patch_omd_site: None, config: Config) -> Iterator[FolderTree]:
    with disable_redis():
        yield make_folder_tree(config)


def _ruleset(ruleset_name: RulesetName) -> rulesets.Ruleset:
    return rulesets.Ruleset(ruleset_name)


GEN_ID_COUNT = {"c": 0}


@pytest.fixture(autouse=True)
def fixture_gen_id(monkeypatch: pytest.MonkeyPatch, request_context: None) -> None:
    GEN_ID_COUNT["c"] = 0

    def _gen_id():
        GEN_ID_COUNT["c"] += 1
        return str(GEN_ID_COUNT["c"])

    monkeypatch.setattr(gui_rulesets_module, "gen_id", _gen_id)


def test_rule_from_config_unhandled_format(tree: FolderTree):
    ruleset = _ruleset(RuleGroup.DiscoveryParameters("inventory_processes_rules"))

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            tree.root_folder(),
            ruleset,
            [],
        )

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            tree.root_folder(),
            ruleset,
            (None,),
        )


@pytest.mark.parametrize(
    "rule_options",
    [
        {"disabled": True},
        None,
    ],
)
@pytest.mark.parametrize(
    "ruleset_name,rule_spec,expected_attributes",
    [
        # non-binary host ruleset
        (
            RuleGroup.DiscoveryParameters("inventory_processes_rules"),
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": "VAL",
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            RuleGroup.DiscoveryParameters("inventory_processes_rules"),
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "host_tags": {
                        "specs": "specs",
                        "tag": "tag",
                    },
                },
            },
            {
                "id": "1",
                "value": "VAL",
                "conditions": {
                    "host_name": ["HOSTLIST"],
                    "host_tags": {
                        "specs": "specs",
                        "tag": "tag",
                    },
                },
            },
        ),
        # $or tags
        (
            RuleGroup.DiscoveryParameters("inventory_processes_rules"),
            {
                "id": "1",
                "value": "ORED_TAGS",
                "condition": {
                    "host_tags": {
                        "specs": {
                            "$or": [
                                "specs",
                                "tag",
                            ],
                        }
                    }
                },
            },
            {
                "id": "1",
                "value": "ORED_TAGS",
                "conditions": {
                    "host_tags": {
                        "specs": {
                            "$or": [
                                "specs",
                                "tag",
                            ],
                        }
                    }
                },
            },
        ),
        # $nor tags
        (
            RuleGroup.DiscoveryParameters("inventory_processes_rules"),
            {
                "id": "1",
                "value": "NORED_TAGS",
                "condition": {
                    "host_tags": {
                        "specs": {
                            "$nor": [
                                "specs",
                                "tag",
                            ],
                        }
                    }
                },
            },
            {
                "id": "1",
                "value": "NORED_TAGS",
                "conditions": {
                    "host_tags": {
                        "specs": {
                            "$nor": [
                                "specs",
                                "tag",
                            ],
                        }
                    }
                },
            },
        ),
        # binary host ruleset
        (
            "only_hosts",
            {
                "id": "1",
                "value": True,
                "condition": {
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": True,
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            "only_hosts",
            {
                "id": "1",
                "value": False,
                "condition": {
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": False,
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        # non-binary service ruleset
        (
            RuleGroup.CheckgroupParameters("local"),
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": "VAL",
                "conditions": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        # binary service ruleset
        (
            "clustered_services",
            {
                "id": "1",
                "value": True,
                "condition": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": True,
                "conditions": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            "clustered_services",
            {
                "id": "1",
                "value": False,
                "condition": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": False,
                "conditions": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        # No rule ID (pre 2.0)
        (
            "only_hosts",
            {
                "value": True,
                "condition": {
                    "host_name": ["HOSTLIST"],
                },
            },
            {
                "id": "1",
                "value": True,
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
    ],
)
def test_rule_from_config_dict(  # type: ignore[misc]
    tree: FolderTree,
    ruleset_name: str,
    rule_spec: RuleSpec,
    expected_attributes: Mapping[str, object],
    rule_options: RuleOptionsSpec,
) -> None:
    rule_spec = rule_spec.copy()
    if rule_options is not None:
        rule_spec["options"] = rule_options

    rule = rulesets.Rule.from_config(
        tree.root_folder(),
        _ruleset(ruleset_name),
        rule_spec,
    )

    for key, val in expected_attributes.items():
        if key == "conditions":
            assert rule.conditions.to_config(rulesets.UseHostFolder.NONE) == val
        else:
            assert getattr(rule, key) == val

    if rule_options is not None:
        assert rule.rule_options == RuleOptions.from_config(rule_options)
    else:
        assert rule.rule_options == RuleOptions.from_config({})

    # test for synchronous to_dict on the way. Except when rule_spec.id was not set, because the ID
    # is added dynamically when processing such rules.
    rule_spec_for_config = rule_spec.copy()
    new_rule_config = dict(rule.to_config())

    if "id" in rule_spec:
        assert new_rule_config == rule_spec_for_config
    else:
        assert new_rule_config["id"] == "1"
        del new_rule_config["id"]
        assert new_rule_config == rule_spec_for_config


@pytest.mark.parametrize(
    "wato_use_git,expected_result",
    [
        (
            True,
            """
checkgroup_parameters = locals().setdefault('checkgroup_parameters', {})

checkgroup_parameters.setdefault('local', [])

checkgroup_parameters['local'] = [
{'condition': {'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'id': '1',
 'value': 'VAL'},
{'condition': {'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'id': '2',
 'value': 'VAL2'},
] + checkgroup_parameters['local']

""",
        ),
        # TODO: Can currently not be tested because it's PYTHONHASHSEED specific. The pprint test above is enough for the moment.
        #    (False, """
        # checkgroup_parameters.setdefault('local', [])
        #
        # checkgroup_parameters['local'] = [
        # {'condition': {'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}], 'host_folder': '%#%FOLDER_PATH%#%', 'host_name': ['HOSTLIST']}, 'value': 'VAL'},
        # {'condition': {'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}], 'host_folder': '%#%FOLDER_PATH%#%', 'host_name': ['HOSTLIST']}, 'value': 'VAL2'},
        # ] + checkgroup_parameters['local']
        #
        # """),
    ],
)
def test_ruleset_to_config(
    tree: FolderTree,
    wato_use_git: bool,
    expected_result: str,
) -> None:
    ruleset = rulesets.Ruleset(RuleGroup.CheckgroupParameters("local"))
    ruleset.replace_folder_config(
        tree.root_folder(),
        [
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                },
            },
            {
                "id": "2",
                "value": "VAL2",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                },
            },
        ],
    )
    assert ruleset.to_config(tree.root_folder(), pprint_value=wato_use_git) == expected_result


@pytest.mark.parametrize(
    "wato_use_git,expected_result",
    [
        (
            True,
            """
checkgroup_parameters = locals().setdefault('checkgroup_parameters', {})

checkgroup_parameters.setdefault('local', [])

checkgroup_parameters['local'] = [
{'condition': {'host_folder': '%#%FOLDER_PATH%#%',
               'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'id': '1',
 'value': 'VAL'},
{'condition': {'host_folder': '%#%FOLDER_PATH%#%',
               'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'id': '2',
 'value': 'VAL2'},
] + checkgroup_parameters['local']

""",
        ),
    ],
)
def test_ruleset_to_config_sub_folder(
    tree: FolderTree,
    with_admin_login: UserId,
    wato_use_git: bool,
    expected_result: str,
) -> None:
    ruleset = rulesets.Ruleset(RuleGroup.CheckgroupParameters("local"))

    tree.create_missing_folders(
        "abc", pprint_value=False, pending_changes=_noop_pending_changes(), acting_user=user
    )
    folder = tree.folder("abc")

    ruleset.replace_folder_config(
        folder,
        [
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                },
            },
            {
                "id": "2",
                "value": "VAL2",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                },
            },
        ],
    )
    assert ruleset.to_config(folder, pprint_value=wato_use_git) == expected_result


def _setup_rules(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool
) -> tuple[Ruleset, Folder, Rule]:
    ruleset = _ruleset(RuleGroup.CheckgroupParameters("local"))
    bundle_id = BundleId("bundle_id")
    program_id = PROGRAM_ID_QUICK_SETUP
    create_config_bundle(
        tree,
        bundle_id=bundle_id,
        bundle={
            "title": "bundle_title",
            "comment": "bundle_comment",
            "owned_by": "user_id",
            "group": "bundle_group",
            "program_id": program_id,
        },
        entities=CreateBundleEntities(),
        acting_user=LoggedInSuperUser(),
        user_permissions=UserPermissions({}, {}, {}, []),
        pprint_value=False,
        debug=False,
        pending_changes=_noop_pending_changes(),
    )

    folder = tree.root_folder()
    ruleset.append_rule(
        folder,
        Rule.from_config(
            folder,
            ruleset,
            {
                "id": "1",
                "value": "VAL",
                "condition": {
                    "host_name": ["HOSTLIST"],
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                },
                "locked_by": (
                    {
                        "site_id": "heute",
                        "program_id": program_id,
                        "instance_id": bundle_id,
                    }
                    if rule_a_locked
                    else None
                ),
            },
        ),
    )
    rule = Rule.from_config(
        folder,
        ruleset,
        {
            "id": "2",
            "value": "VAL2",
            "condition": {
                "host_name": ["HOSTLIST"],
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
            },
            "locked_by": (
                {
                    "site_id": "heute",
                    "program_id": program_id,
                    "instance_id": bundle_id,
                }
                if rule_b_locked
                else None
            ),
        },
    )
    return ruleset, folder, rule


@pytest.mark.parametrize(
    "rule_a_locked, rule_b_locked, expected_index",
    [
        (False, False, 0),
        (True, False, 1),
        (False, True, 0),
        (True, True, 0),
    ],
)
def test_ruleset_get_index_for_move(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(tree, rule_a_locked, rule_b_locked)
    ruleset.append_rule(folder, rule)
    assert ruleset.get_index_for_move(folder, rule, 0) == expected_index


@pytest.mark.parametrize(
    "rule_a_locked, rule_b_locked, expected_index",
    [
        (False, False, 0),
        (True, False, 1),
        (False, True, 0),
        (True, True, 0),
    ],
)
def test_ruleset_ordering_prepend(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(tree, rule_a_locked, rule_b_locked)
    ruleset.prepend_rule(folder, rule)
    assert ruleset.get_folder_rules(folder)[expected_index] == rule


@pytest.mark.parametrize(
    "rule_a_locked, rule_b_locked, expected_index",
    [
        (False, False, 1),
        (True, False, 1),
        (False, True, 0),
        (True, True, 1),
    ],
)
def test_ruleset_ordering_append(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(tree, rule_a_locked, rule_b_locked)
    ruleset.append_rule(folder, rule)
    assert ruleset.get_folder_rules(folder)[expected_index] == rule


@pytest.mark.parametrize(
    "rule_a_locked, rule_b_locked, expected_index",
    [
        (False, False, 0),
        (True, False, 1),
        (False, True, 0),
        (True, True, 0),
    ],
)
def test_ruleset_ordering_move_to(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(tree, rule_a_locked, rule_b_locked)
    ruleset.append_rule(folder, rule)
    ruleset.move_rule_to(rule, index=0, pending_changes=_noop_pending_changes())
    assert ruleset.get_folder_rules(folder)[expected_index] == rule


@pytest.mark.parametrize(
    "rule_a_locked, rule_b_locked, expected_index",
    [
        (False, False, 1),
        (True, False, 1),
        (False, True, 0),
        (True, True, 1),
    ],
)
def test_ruleset_ordering_insert_after(
    tree: FolderTree, rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(tree, rule_a_locked, rule_b_locked)
    ruleset.insert_rule_after(rule, ruleset.get_folder_rules(folder)[0])
    assert ruleset.get_folder_rules(folder)[expected_index] == rule
