#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from dataclasses import dataclass
from typing import Callable

import pytest

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.utils import version
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
    "ruleset_name,rule_spec",
    [
        # non-binary host ruleset
        (
            "inventory_processes_rules",
            ("VAL", ["HOSTLIST"]),
        ),
        (
            "inventory_processes_rules",
            ("VAL", ["tag", "specs"], ["HOSTLIST"]),
        ),
        # binary host ruleset
        (
            "only_hosts",
            (["HOSTLIST"],),
        ),
        (
            "only_hosts",
            (
                rulesets.NEGATE,
                ["HOSTLIST"],
            ),
        ),
        # non-binary service ruleset
        (
            "checkgroup_parameters:local",
            ("VAL", ["HOSTLIST"], ["SVC", "LIST"]),
        ),
        # binary service ruleset
        (
            "clustered_services",
            (["HOSTLIST"], ["SVC", "LIST"]),
        ),
        (
            "clustered_services",
            (rulesets.NEGATE, ["HOSTLIST"], ["SVC", "LIST"]),
        ),
    ],
)
def test_rule_from_config_tuple(ruleset_name, rule_spec):
    ruleset = rulesets.Ruleset(
        ruleset_name, ruleset_matcher.get_tag_to_group_map(active_config.tags)
    )
    error = "Found old style tuple ruleset"
    with pytest.raises(MKGeneralException, match=error):
        ruleset.from_config(hosts_and_folders.Folder.root_folder(), [rule_spec])


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
    with_admin_login,
    search_options: rulesets.SearchOptions,
    rule_config: RuleSpec,
    folder_name: str,
    expected_result: bool,
):
    hosts_and_folders.Folder.create_missing_folders(folder_name)
    folder = hosts_and_folders.Folder.folder(folder_name)
    ruleset = _ruleset("host_contactgroups")
    rule = rulesets.Rule.from_config(folder, ruleset, rule_config)
    ruleset.append_rule(folder, rule)

    assert ruleset.matches_search_with_rules(search_options) == expected_result


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
            hosts_and_folders.Folder.root_folder(),
            _ruleset(ruleset),
            {"id": "1", "value": value, "condition": {"host_name": ["HOSTLIST"]}},
        )

    @staticmethod
    def gcp_rule() -> rulesets.Rule:
        return _RuleHelper._make_rule(
            "special_agents:gcp",
            {
                "project": "old_value",
                "credentials": ("password", "hunter2"),
                "services": ["gcs", "gce"],
            },
        )

    @staticmethod
    def ssh_rule() -> rulesets.Rule:
        return _RuleHelper._make_rule(
            "agent_config:lnx_remote_alert_handlers",
            {"handlers": {}, "runas": "old_value", "sshkey": ("private_key", "public_key")},
        )


@pytest.fixture(
    params=[
        _RuleHelper(_RuleHelper.gcp_rule, "credentials", ("password", "geheim"), "project"),
        pytest.param(
            _RuleHelper(_RuleHelper.ssh_rule, "sshkey", ("new_priv", "public_key"), "runas"),
            marks=pytest.mark.skipif(
                version.is_raw_edition(),
                reason="lnx_remote_alert_handlers is not available in raw edition",
            ),
        ),
    ]
)
def rule_helper(request) -> _RuleHelper:
    return request.param


def test_to_log_masks_secrets(request_context) -> None:
    log = str(_RuleHelper.gcp_rule().to_log())
    assert "'password'" in log, "password tuple is present"
    assert "hunter2" not in log, "password is masked"


def test_diff_rules_new_rule(request_context, rule_helper) -> None:
    new = rule_helper.rule()
    diff = new.ruleset.diff_rules(None, new)
    assert rule_helper.secret_attr in diff, "Attribute is added in new rule"
    assert "******" in diff, "Attribute is masked"


def test_diff_to_no_changes(request_context, rule_helper) -> None:
    rule = rule_helper.rule()
    assert rule.diff_to(rule) == "Nothing was changed."


def test_diff_to_secret_changed(request_context, rule_helper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    assert old.diff_to(new) == "Redacted secrets changed."


def test_diff_to_secret_unchanged(request_context, rule_helper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.other_attr] = "new_value"
    diff = old.diff_to(new)
    assert "Redacted secrets changed." not in diff
    assert 'changed from "old_value" to "new_value".' in diff


def test_diff_to_secret_and_other_attribute_changed(request_context, rule_helper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    new.value[rule_helper.other_attr] = "new_value"
    diff = old.diff_to(new)
    assert "Redacted secrets changed." in diff
    assert 'changed from "old_value" to "new_value".' in diff
