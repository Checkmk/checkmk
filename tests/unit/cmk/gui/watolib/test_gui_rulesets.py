#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.utils.type_defs import RuleOptions, RuleOptionsSpec, RuleSpec

import cmk.gui.utils

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders
import cmk.gui.watolib.rulesets as rulesets
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.plugins.wato.check_parameters.local import _parameter_valuespec_local
from cmk.gui.plugins.wato.check_parameters.ps import _valuespec_inventory_processes_rules


def _ruleset(ruleset_name) -> rulesets.Ruleset:
    return rulesets.Ruleset(ruleset_name, ruleset_matcher.get_tag_to_group_map(active_config.tags))


GEN_ID_COUNT = {"c": 0}


@pytest.fixture(autouse=True)
def fixture_gen_id(monkeypatch):
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
            "checkgroup_parameters:local",
            _parameter_valuespec_local().default_value(),
            False,
        ),
        # binary service ruleset
        ("clustered_services", True, True),
    ],
)
def test_rule_from_ruleset_defaults(
    request_context, ruleset_name, default_value, is_binary
) -> None:
    ruleset = _ruleset(ruleset_name)
    rule = rulesets.Rule.from_ruleset_defaults(hosts_and_folders.Folder.root_folder(), ruleset)
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


def test_rule_from_config_unhandled_format(
    request_context,
):
    ruleset = _ruleset("inventory_processes_rules")

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            hosts_and_folders.Folder.root_folder(),
            ruleset,
            [],
        )

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rulesets.Rule.from_config(
            hosts_and_folders.Folder.root_folder(),
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
            ("VAL", ["HOSTLIST"]),
            {
                "value": "VAL",
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            "inventory_processes_rules",
            ("VAL", ["tag", "specs"], ["HOSTLIST"]),
            {
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
        # binary host ruleset
        (
            "only_hosts",
            (["HOSTLIST"],),
            {
                "value": True,
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            "only_hosts",
            (
                rulesets.NEGATE,
                ["HOSTLIST"],
            ),
            {
                "value": False,
                "conditions": {
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        # non-binary service ruleset
        (
            "checkgroup_parameters:local",
            ("VAL", ["HOSTLIST"], ["SVC", "LIST"]),
            {
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
            (["HOSTLIST"], ["SVC", "LIST"]),
            {
                "value": True,
                "conditions": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
        (
            "clustered_services",
            (rulesets.NEGATE, ["HOSTLIST"], ["SVC", "LIST"]),
            {
                "value": False,
                "conditions": {
                    "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                    "host_name": ["HOSTLIST"],
                },
            },
        ),
    ],
)
def test_rule_from_config_tuple(
    request_context,
    ruleset_name,
    rule_spec,
    expected_attributes,
    rule_options: Optional[RuleOptionsSpec],
):
    if rule_options is not None:
        rule_spec = rule_spec + (rule_options,)

    ruleset = rulesets.Ruleset(
        ruleset_name, ruleset_matcher.get_tag_to_group_map(active_config.tags)
    )
    ruleset.from_config(hosts_and_folders.Folder.root_folder(), [rule_spec])
    rule = ruleset.get_folder_rules(hosts_and_folders.Folder.root_folder())[0]

    for key, val in expected_attributes.items():
        if key == "conditions":
            assert rule.conditions.to_config(rulesets.UseHostFolder.NONE) == val
        else:
            assert getattr(rule, key) == val

    if rule_options is not None:
        assert rule.rule_options == RuleOptions.from_config(rule_options)
    else:
        assert rule.rule_options == RuleOptions.from_config({})


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
            "checkgroup_parameters:local",
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
    request_context,
    ruleset_name,
    rule_spec: RuleSpec,
    expected_attributes,
    rule_options: RuleOptionsSpec,
):
    rule_spec = rule_spec.copy()
    if rule_options is not None:
        rule_spec["options"] = rule_options

    rule = rulesets.Rule.from_config(
        hosts_and_folders.Folder.root_folder(),
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
def test_ruleset_to_config(request_context, monkeypatch, wato_use_git, expected_result) -> None:
    monkeypatch.setattr(active_config, "wato_use_git", wato_use_git)

    ruleset = rulesets.Ruleset(
        "checkgroup_parameters:local", ruleset_matcher.get_tag_to_group_map(active_config.tags)
    )
    ruleset.from_config(
        hosts_and_folders.Folder.root_folder(),
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
    assert ruleset.to_config(hosts_and_folders.Folder.root_folder()) == expected_result


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
    with_admin_login, monkeypatch, wato_use_git, expected_result
) -> None:
    monkeypatch.setattr(active_config, "wato_use_git", wato_use_git)

    ruleset = rulesets.Ruleset(
        "checkgroup_parameters:local", ruleset_matcher.get_tag_to_group_map(active_config.tags)
    )

    hosts_and_folders.Folder.create_missing_folders("abc")
    folder = hosts_and_folders.Folder.folder("abc")

    ruleset.from_config(
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
    assert ruleset.to_config(folder) == expected_result


def test_rule_clone(request_context) -> None:
    rule = rulesets.Rule.from_config(
        hosts_and_folders.Folder.root_folder(),
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
