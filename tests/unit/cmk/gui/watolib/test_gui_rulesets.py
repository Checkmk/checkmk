import pytest  # type: ignore

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato  # pylint: disable=unused-import

from cmk.gui.exceptions import MKGeneralException
import cmk.gui.config as config
import cmk.gui.watolib.rulesets as rulesets
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders


def _rule(ruleset_name):
    ruleset = rulesets.Ruleset(ruleset_name, ruleset_matcher.get_tag_to_group_map(config.tags))
    return rulesets.Rule(hosts_and_folders.Folder.root_folder(), ruleset)


@pytest.mark.parametrize(
    "ruleset_name,default_value,is_binary",
    [
        # non-binary host ruleset
        ("inventory_processes_rules", None, False),
        # binary host ruleset
        ("only_hosts", True, True),
        # non-binary service ruleset
        ("checkgroup_parameters:local", None, False),
        # binary service ruleset
        ("clustered_services", True, True),
    ])
def test_rule_initialize(register_builtin_html, ruleset_name, default_value, is_binary):
    rule = _rule(ruleset_name)
    assert isinstance(rule.conditions, rulesets.RuleConditions)
    assert rule.rule_options == {}
    assert rule.value == default_value
    assert rule.ruleset.rulespec.is_binary_ruleset == is_binary


def test_rule_from_config_unhandled_format(register_builtin_html,):
    rule = _rule("inventory_processes_rules")
    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rule.from_config([])

    with pytest.raises(MKGeneralException, match="Invalid rule"):
        rule.from_config((None,))


@pytest.mark.parametrize(
    "rule_options",
    [
        {
            "disabled": True
        },
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
                    'host_name': ['HOSTLIST'],
                },
            },
        ),
        (
            "inventory_processes_rules",
            ("VAL", ["tag", "specs"], ["HOSTLIST"]),
            {
                "value": "VAL",
                "conditions": {
                    'host_name': ['HOSTLIST'],
                    'host_tags': {
                        'specs': 'specs',
                        'tag': 'tag',
                    },
                },
            },
        ),
        # binary host ruleset
        ("only_hosts", (["HOSTLIST"],), {
            "value": True,
            "conditions": {
                'host_name': ['HOSTLIST'],
            }
        }),
        ("only_hosts", (
            rulesets.NEGATE,
            ["HOSTLIST"],
        ), {
            "value": False,
            "conditions": {
                'host_name': ['HOSTLIST'],
            },
        }),
        # non-binary service ruleset
        ("checkgroup_parameters:local", ("VAL", ["HOSTLIST"], ["SVC", "LIST"]), {
            "value": "VAL",
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
        # binary service ruleset
        ("clustered_services", (["HOSTLIST"], ["SVC", "LIST"]), {
            "value": True,
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
        ("clustered_services", (rulesets.NEGATE, ["HOSTLIST"], ["SVC", "LIST"]), {
            "value": False,
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
    ])
def test_rule_from_config_tuple(register_builtin_html, ruleset_name, rule_spec, expected_attributes,
                                rule_options):
    if rule_options is not None:
        rule_spec = rule_spec + (rule_options,)

    ruleset = rulesets.Ruleset(ruleset_name, ruleset_matcher.get_tag_to_group_map(config.tags))
    ruleset.from_config(hosts_and_folders.Folder.root_folder(), [rule_spec])
    rule = ruleset.get_folder_rules(hosts_and_folders.Folder.root_folder())[0]

    for key, val in expected_attributes.items():
        if key == "conditions":
            assert rule.conditions._to_config() == val
        else:
            assert getattr(rule, key) == val

    if rule_options is not None:
        assert rule.rule_options == rule_options
    else:
        assert rule.rule_options == {}


@pytest.mark.parametrize(
    "rule_options",
    [
        {
            "disabled": True
        },
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
                "value": "VAL",
                "condition": {
                    'host_name': ['HOSTLIST'],
                },
            },
            {
                "value": "VAL",
                "conditions": {
                    'host_name': ['HOSTLIST'],
                },
            },
        ),
        (
            "inventory_processes_rules",
            {
                "value": "VAL",
                "condition": {
                    'host_name': ['HOSTLIST'],
                    'host_tags': {
                        'specs': 'specs',
                        'tag': 'tag',
                    }
                },
            },
            {
                "value": "VAL",
                "conditions": {
                    'host_name': ['HOSTLIST'],
                    'host_tags': {
                        'specs': 'specs',
                        'tag': 'tag',
                    },
                },
            },
        ),
        # $or tags
        (
            "inventory_processes_rules",
            {
                "value": "ORED_TAGS",
                "condition": {
                    'host_tags': {
                        'specs': {
                            "$or": [
                                'specs',
                                'tag',
                            ],
                        }
                    }
                },
            },
            {
                "value": "ORED_TAGS",
                "conditions": {
                    'host_tags': {
                        'specs': {
                            "$or": [
                                'specs',
                                'tag',
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
                "value": "NORED_TAGS",
                "condition": {
                    'host_tags': {
                        'specs': {
                            "$nor": [
                                'specs',
                                'tag',
                            ],
                        }
                    }
                },
            },
            {
                "value": "NORED_TAGS",
                "conditions": {
                    'host_tags': {
                        'specs': {
                            "$nor": [
                                'specs',
                                'tag',
                            ],
                        }
                    }
                },
            },
        ),
        # binary host ruleset
        ("only_hosts", {
            "value": True,
            "condition": {
                'host_name': ['HOSTLIST'],
            },
        }, {
            "value": True,
            "conditions": {
                'host_name': ['HOSTLIST'],
            },
        }),
        ("only_hosts", {
            "value": False,
            "condition": {
                'host_name': ['HOSTLIST'],
            },
        }, {
            "value": False,
            "conditions": {
                'host_name': ['HOSTLIST'],
            },
        }),
        # non-binary service ruleset
        ("checkgroup_parameters:local", {
            "value": "VAL",
            "condition": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }, {
            "value": "VAL",
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
        # binary service ruleset
        ("clustered_services", {
            "value": True,
            "condition": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }, {
            "value": True,
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
        ("clustered_services", {
            "value": False,
            "condition": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }, {
            "value": False,
            "conditions": {
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
                'host_name': ['HOSTLIST']
            },
        }),
    ])
def test_rule_from_config_dict(register_builtin_html, ruleset_name, rule_spec, expected_attributes,
                               rule_options):
    rule_spec = rule_spec.copy()
    if rule_options is not None:
        rule_spec["options"] = rule_options

    rule = _rule(ruleset_name)
    rule.from_config(rule_spec)

    for key, val in expected_attributes.items():
        if key == "conditions":
            assert rule.conditions._to_config() == val
        else:
            assert getattr(rule, key) == val

    if rule_options is not None:
        assert rule.rule_options == rule_options
    else:
        assert rule.rule_options == {}

    # test for synchronous to_dict on the way
    rule_spec_for_config = rule_spec.copy()
    assert rule.to_config() == rule_spec_for_config


@pytest.mark.parametrize(
    "wato_use_git,expected_result",
    [
        (True, """
checkgroup_parameters.setdefault('local', [])

checkgroup_parameters['local'] = [
{'condition': {'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'value': 'VAL'},
{'condition': {'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'value': 'VAL2'},
] + checkgroup_parameters['local']

"""),
        # TODO: Can currently not be tested because it's PYTHONHASHSEED specific. The pprint test above is enough for the moment.
        #    (False, """
        #checkgroup_parameters.setdefault('local', [])
        #
        #checkgroup_parameters['local'] = [
        #{'condition': {'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}], 'host_folder': '%#%FOLDER_PATH%#%', 'host_name': ['HOSTLIST']}, 'value': 'VAL'},
        #{'condition': {'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}], 'host_folder': '%#%FOLDER_PATH%#%', 'host_name': ['HOSTLIST']}, 'value': 'VAL2'},
        #] + checkgroup_parameters['local']
        #
        #"""),
    ])
def test_ruleset_to_config(register_builtin_html, monkeypatch, wato_use_git, expected_result):
    monkeypatch.setattr(config, "wato_use_git", wato_use_git)

    ruleset = rulesets.Ruleset("checkgroup_parameters:local",
                               ruleset_matcher.get_tag_to_group_map(config.tags))
    ruleset.from_config(hosts_and_folders.Folder.root_folder(), [
        {
            "value": "VAL",
            "condition": {
                'host_name': ['HOSTLIST'],
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
            },
        },
        {
            "value": "VAL2",
            "condition": {
                'host_name': ['HOSTLIST'],
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
            },
        },
    ])
    assert ruleset.to_config(hosts_and_folders.Folder.root_folder()) == expected_result


@pytest.mark.parametrize("wato_use_git,expected_result", [
    (True, """
checkgroup_parameters.setdefault('local', [])

checkgroup_parameters['local'] = [
{'condition': {'host_folder': '%#%FOLDER_PATH%#%',
               'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'value': 'VAL'},
{'condition': {'host_folder': '%#%FOLDER_PATH%#%',
               'host_name': ['HOSTLIST'],
               'service_description': [{'$regex': 'SVC'}, {'$regex': 'LIST'}]},
 'value': 'VAL2'},
] + checkgroup_parameters['local']

"""),
])
def test_ruleset_to_config_sub_folder(register_builtin_html, monkeypatch, load_config, wato_use_git,
                                      expected_result):
    monkeypatch.setattr(config, "wato_use_git", wato_use_git)

    ruleset = rulesets.Ruleset("checkgroup_parameters:local",
                               ruleset_matcher.get_tag_to_group_map(config.tags))

    monkeypatch.setattr(config, "user", config.LoggedInSuperUser())
    hosts_and_folders.Folder.create_missing_folders("abc")
    folder = hosts_and_folders.Folder.folder("abc")

    ruleset.from_config(folder, [
        {
            "value": "VAL",
            "condition": {
                'host_name': ['HOSTLIST'],
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
            },
        },
        {
            "value": "VAL2",
            "condition": {
                'host_name': ['HOSTLIST'],
                'service_description': [{
                    '$regex': 'SVC'
                }, {
                    '$regex': 'LIST'
                }],
            },
        },
    ])
    assert ruleset.to_config(folder) == expected_result


def test_rule_clone(register_builtin_html):
    rule = _rule("clustered_services")
    rule.from_config({
        "value": True,
        "condition": {
            'host_name': 'HOSTLIST',
            'service_description': [{
                '$regex': 'SVC'
            }, {
                '$regex': 'LIST'
            }],
        },
    })

    cloned_rule = rule.clone()

    assert rule.to_config() == cloned_rule.to_config()
    assert rule.folder == cloned_rule.folder
    assert rule.ruleset == cloned_rule.ruleset
