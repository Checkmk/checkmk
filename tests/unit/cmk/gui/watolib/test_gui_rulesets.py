#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from unittest.mock import patch

import pytest
from pytest import FixtureRequest

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc import version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId

from cmk.utils import paths
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.redis import disable_redis
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RuleOptionsSpec, RulesetName, RuleSpec
from cmk.utils.tags import get_tag_to_group_map, TagGroupID, TagID

from cmk.automations.results import AnalyzeHostRuleEffectivenessResult

from cmk.base.automations.check_mk import AutomationAnalyzeHostRuleEffectiveness
from cmk.base.config import LoadingResult

import cmk.gui.utils
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.plugins.wato.check_parameters.local import _parameter_valuespec_local
from cmk.gui.plugins.wato.check_parameters.ps import _valuespec_inventory_processes_rules
from cmk.gui.utils.rule_specs import legacy_converter
from cmk.gui.watolib import rulesets
from cmk.gui.watolib.configuration_bundle_store import BundleId
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import Rule, RuleOptions, Ruleset, RuleValue


def _ruleset(ruleset_name: RulesetName) -> rulesets.Ruleset:
    return rulesets.Ruleset(ruleset_name, get_tag_to_group_map(active_config.tags))


GEN_ID_COUNT = {"c": 0}


@pytest.fixture(autouse=True)
def fixture_gen_id(monkeypatch: pytest.MonkeyPatch, request_context: None) -> None:
    GEN_ID_COUNT["c"] = 0

    def _gen_id():
        GEN_ID_COUNT["c"] += 1
        return str(GEN_ID_COUNT["c"])

    monkeypatch.setattr(cmk.gui.utils, "gen_id", _gen_id)


@pytest.mark.parametrize(
    "ruleset_name,default_value,is_binary",
    [
        # non-binary host ruleset
        (
            "inventory_processes_rules",
            _valuespec_inventory_processes_rules().default_value(),
            False,
        ),
        # binary host ruleset
        ("only_hosts", True, True),
        # non-binary service ruleset
        (
            RuleGroup.CheckgroupParameters("local"),
            _parameter_valuespec_local().default_value(),
            False,
        ),
        # binary service ruleset
        ("clustered_services", True, True),
    ],
)
def test_rule_from_ruleset_defaults(
    ruleset_name: str, default_value: RuleValue, is_binary: bool
) -> None:
    ruleset = _ruleset(ruleset_name)
    rule = rulesets.Rule.from_ruleset_defaults(folder_tree().root_folder(), ruleset)
    assert isinstance(rule.conditions, rulesets.RuleConditions)
    assert rule.rule_options == RuleOptions(
        disabled=False,
        description="",
        comment="",
        docu_url="",
        predefined_condition_id=None,
    )
    assert rule.value == default_value
    assert rule.ruleset.rulespec.is_binary_ruleset == is_binary


def test_rule_from_config_unhandled_format():
    ruleset = _ruleset("inventory_processes_rules")

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            folder_tree().root_folder(),
            ruleset,
            [],
        )

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            folder_tree().root_folder(),
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
            "inventory_processes_rules",
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
            "inventory_processes_rules",
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
            "inventory_processes_rules",
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
            "inventory_processes_rules",
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
def test_rule_from_config_dict(
    ruleset_name: str,
    rule_spec: RuleSpec,
    expected_attributes: Mapping[str, object],
    rule_options: RuleOptionsSpec,
) -> None:
    rule_spec = rule_spec.copy()
    if rule_options is not None:
        rule_spec["options"] = rule_options

    rule = rulesets.Rule.from_config(
        folder_tree().root_folder(),
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
    wato_use_git: bool,
    expected_result: str,
) -> None:
    ruleset = rulesets.Ruleset(
        RuleGroup.CheckgroupParameters("local"),
        get_tag_to_group_map(active_config.tags),
    )
    ruleset.replace_folder_config(
        folder_tree().root_folder(),
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
    assert (
        ruleset.to_config(folder_tree().root_folder(), pprint_value=wato_use_git) == expected_result
    )


@pytest.mark.parametrize(
    "wato_use_git,expected_result",
    [
        (
            True,
            """
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
    with_admin_login: UserId,
    wato_use_git: bool,
    expected_result: str,
) -> None:
    ruleset = rulesets.Ruleset(
        RuleGroup.CheckgroupParameters("local"),
        get_tag_to_group_map(active_config.tags),
    )

    folder_tree().create_missing_folders("abc", pprint_value=False)
    folder = folder_tree().folder("abc")

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


def test_rule_clone() -> None:
    rule = rulesets.Rule.from_config(
        folder_tree().root_folder(),
        _ruleset("clustered_services"),
        {
            "id": "10",
            "value": True,
            "condition": {
                "host_name": ["HOSTLIST"],
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
            },
        },
    )

    cloned_rule = rule.clone()

    rule_config = dict(rule.to_config())
    del rule_config["id"]
    cloned_config = dict(cloned_rule.to_config())
    del cloned_config["id"]
    assert rule_config == cloned_config

    assert rule.folder == cloned_rule.folder
    assert rule.ruleset == cloned_rule.ruleset
    assert rule.id != cloned_rule.id


def test_rule_clone_locked() -> None:
    rule = rulesets.Rule.from_config(
        folder_tree().root_folder(),
        _ruleset("clustered_services"),
        {
            "id": "10",
            "value": True,
            "condition": {
                "host_name": ["HOSTLIST"],
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
            },
            "locked_by": {
                "site_id": "heute",
                "program_id": PROGRAM_ID_QUICK_SETUP,
                "instance_id": "...",
            },
        },
    )
    assert rule.locked_by is not None

    cloned_rule = rule.clone(preserve_id=True)
    assert rule.locked_by == cloned_rule.locked_by

    cloned_rule = rule.clone(preserve_id=False)
    assert cloned_rule.locked_by is None


def _setup_rules(rule_a_locked: bool, rule_b_locked: bool) -> tuple[Ruleset, Folder, Rule]:
    ruleset = _ruleset(RuleGroup.CheckgroupParameters("local"))
    bundle_id = BundleId("bundle_id")
    program_id = PROGRAM_ID_QUICK_SETUP
    create_config_bundle(
        bundle_id=bundle_id,
        bundle={
            "title": "bundle_title",
            "comment": "bundle_comment",
            "owned_by": "user_id",
            "group": "bundle_group",
            "program_id": program_id,
        },
        entities=CreateBundleEntities(),
        user_id=user.id,
        pprint_value=False,
        use_git=False,
        debug=False,
    )

    folder = folder_tree().root_folder()
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
    rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(rule_a_locked, rule_b_locked)
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
    rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(rule_a_locked, rule_b_locked)
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
    rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(rule_a_locked, rule_b_locked)
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
    rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(rule_a_locked, rule_b_locked)
    ruleset.append_rule(folder, rule)
    ruleset.move_rule_to(rule, 0)
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
    rule_a_locked: bool, rule_b_locked: bool, expected_index: int
) -> None:
    ruleset, folder, rule = _setup_rules(rule_a_locked, rule_b_locked)
    ruleset.insert_rule_after(rule, ruleset.get_folder_rules(folder)[0])
    assert ruleset.get_folder_rules(folder)[expected_index] == rule


@pytest.mark.parametrize(
    "search_options, rule_config, folder_name, expected_result",
    [
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": [{"$regex": ".*foo.*"}],
                },
                "options": {"disabled": False, "description": "foo"},
            },
            "regex_check",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "efd67dab-68f8-4d3c-a417-9f7e29ab48d5",
                "value": "all",
                "condition": {},
                "options": {"description": 'Put all hosts into the contact group "all"'},
            },
            "",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "59d84cde-ee3a-4f8d-8bec-fce35a2b0d15",
                "value": "all",
                "condition": {
                    "host_name": ["foobar123"],
                },
                "options": {"description": "foo"},
            },
            "regex_check",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": [{"$regex": ".*foo123.*"}],
                },
                "options": {"description": "foo"},
            },
            "regex_check",
            False,
        ),
    ],
)
def test_matches_search_with_rules(
    with_admin_login: UserId,
    search_options: rulesets.SearchOptions,
    rule_config: RuleSpec,
    folder_name: str,
    expected_result: bool,
) -> None:
    folder_tree().create_missing_folders(folder_name, pprint_value=False)
    folder = folder_tree().folder(folder_name)
    ruleset = _ruleset("host_contactgroups")
    rule = rulesets.Rule.from_config(folder, ruleset, rule_config)
    ruleset.append_rule(folder, rule)

    assert ruleset.matches_search_with_rules(search_options, debug=False) == expected_result


@pytest.fixture(name="inline_analyze_host_rule_effectiveness_automation")
def fixture_inline_analyze_host_rule_effectiveness_automation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inline rule matching automation call"""

    def analyze_host_rule_effectiveness(
        r: Sequence[Sequence[RuleSpec]], *, debug: bool
    ) -> AnalyzeHostRuleEffectivenessResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        config_cache = ts.apply(monkeypatch)
        loading_result = LoadingResult(
            loaded_config=config_cache._loaded_config,
            config_cache=config_cache,
        )

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr(r)))
            return AutomationAnalyzeHostRuleEffectiveness().execute([], None, loading_result)

    monkeypatch.setattr(
        rulesets, "analyze_host_rule_effectiveness", analyze_host_rule_effectiveness
    )


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_negate_is_ineffective_finds_matching(
    with_admin_login: UserId,
) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["ding"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": False}, debug=False) is True


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_is_ineffective_finds_matching(with_admin_login: UserId) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["ding"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": True}, debug=False) is False


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_is_ineffective_finds_not_matching(
    with_admin_login: UserId,
) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["dong"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": True}, debug=False) is True


@dataclass
class _RuleHelper:
    """Helps making and accessing rules"""

    rule: Callable[[], rulesets.Rule]
    secret_attr: str
    new_secret: object
    other_attr: str

    @staticmethod
    def _make_rule(ruleset: str, value: dict) -> rulesets.Rule:
        return rulesets.Rule.from_config(
            folder_tree().root_folder(),
            _ruleset(ruleset),
            {"id": "1", "value": value, "condition": {"host_name": ["HOSTLIST"]}},
        )

    @staticmethod
    def gcp_rule() -> rulesets.Rule:
        return _RuleHelper._make_rule(
            RuleGroup.SpecialAgents("gcp"),
            {
                "project": "old_value",
                "credentials": ("explicit_password", "uuid", "hunter2"),
                "services": ["gcs", "gce"],
            },
        )

    @staticmethod
    def ssh_rule() -> rulesets.Rule:
        return _RuleHelper._make_rule(
            RuleGroup.AgentConfig("lnx_remote_alert_handlers"),
            {"handlers": {}, "runas": "old_value", "sshkey": ("private_key", "public_key")},
        )


@pytest.fixture(
    params=[
        _RuleHelper(
            _RuleHelper.gcp_rule, "credentials", ("explicit_password", "uuid", "geheim"), "project"
        ),
        pytest.param(
            _RuleHelper(_RuleHelper.ssh_rule, "sshkey", ("new_priv", "public_key"), "runas"),
            marks=pytest.mark.skipif(
                version.edition(paths.omd_root) is version.Edition.CRE,
                reason="lnx_remote_alert_handlers is not available in raw edition",
            ),
        ),
    ]
)
def rule_helper(request: FixtureRequest) -> _RuleHelper:
    return request.param


def test_to_log_masks_secrets() -> None:
    log = str(_RuleHelper.gcp_rule().to_log())
    assert "'password'" in log, "password tuple is present"
    assert "hunter2" not in log, "password is masked"


def test_diff_rules_new_rule(rule_helper: _RuleHelper) -> None:
    new = rule_helper.rule()
    diff = new.ruleset.diff_rules(None, new)
    assert rule_helper.secret_attr in diff, "Attribute is added in new rule"
    assert "******" in diff, "Attribute is masked"


def test_diff_to_no_changes(rule_helper: _RuleHelper) -> None:
    rule = rule_helper.rule()
    # An uuid is created every time a rule is created/edited, so mock it here for the comparison.
    # The actual password should stay the same
    with patch.object(legacy_converter, "ad_hoc_password_id", return_value="test-uuid"):
        assert rule.diff_to(rule) == "Nothing was changed."


def test_diff_to_secret_changed(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    assert old.diff_to(new) == "Redacted secrets changed."


def test_diff_to_secret_unchanged(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.other_attr] = "new_value"
    # An uuid is created every time a rule is created/edited, so mock it here for the comparison.
    # The actual password should stay the same
    with patch.object(legacy_converter, "ad_hoc_password_id", return_value="test-uuid"):
        diff = old.diff_to(new)
    assert "Redacted secrets changed." not in diff
    assert 'changed from "old_value" to "new_value".' in diff


def test_diff_to_secret_and_other_attribute_changed(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    new.value[rule_helper.other_attr] = "new_value"
    diff = old.diff_to(new)
    assert "Redacted secrets changed." in diff
    assert 'changed from "old_value" to "new_value".' in diff


def test_rules_grouped_by_folder() -> None:
    """Test sort order of rules"""
    tree = folder_tree()
    expected_folder_order: list[str] = [
        "folder2/folder2/folder2",
        "folder2/folder2/folder1",
        "folder2/folder2",
        "folder2/folder1/folder2",
        "folder2/folder1/folder1",
        "folder2/folder1",
        "folder2",
        "folder1/folder2/folder2",
        "folder1/folder2/folder1",
        "folder1/folder2",
        "folder1/folder1/folder2",
        "folder1/folder1/folder1",
        "folder1/folder1",
        "folder1",
        "folder4",
        "",
    ]

    root: Folder = tree.root_folder()
    ruleset: Ruleset = Ruleset("only_hosts", {TagID("TAG1"): TagGroupID("TG1")})
    rules: list[tuple[Folder, int, Rule]] = [(root, 0, Rule.from_ruleset_defaults(root, ruleset))]

    for nr in range(1, 3):
        folder = Folder.new(tree=tree, name="folder%d" % nr, parent_folder=root)
        rules.append((folder, 0, Rule.from_ruleset_defaults(folder, ruleset)))
        for x in range(1, 3):
            subfolder = Folder.new(tree=tree, name="folder%d" % x, parent_folder=folder)
            rules.append((subfolder, 0, Rule.from_ruleset_defaults(folder, ruleset)))
            for y in range(1, 3):
                sub_subfolder = Folder.new(tree=tree, name="folder%d" % y, parent_folder=subfolder)
                rules.append((sub_subfolder, 0, Rule.from_ruleset_defaults(folder, ruleset)))

    # Also test renamed folder
    folder4 = Folder.new(tree=tree, name="folder4", parent_folder=root)
    folder4._title = "abc"
    rules.append((folder4, 0, Rule.from_ruleset_defaults(folder4, ruleset)))

    sorted_rules = sorted(
        rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True
    )
    with disable_redis():
        assert (
            list(rule[0].path() for rule in rulesets.rules_grouped_by_folder(sorted_rules, root))
            == expected_folder_order
        )
