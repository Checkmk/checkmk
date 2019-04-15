# encoding: utf-8
# pylint: disable=redefined-outer-name

from typing import NamedTuple
from pathlib2 import Path
import pytest  # type: ignore
import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
from cmk.utils.exceptions import MKGeneralException


def test_transform_tuple_ruleset():
    ruleset = [
        ("VAL1", ["HOSTLIST1"]),
        ("VAL2", ["HOSTLIST2"]),
    ]

    tuple_rulesets.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
        ruleset, is_binary=False, is_service=False)

    assert ruleset == [
        {
            "value": "VAL1",
            "condition": {
                "host_name": "HOSTLIST1",
            }
        },
        {
            "value": "VAL2",
            "condition": {
                "host_name": "HOSTLIST2",
            }
        },
    ]


def test_transform_mixed_ruleset():
    ruleset = [
        ("VAL1", ["HOSTLIST1"]),
        {
            "value": "VAL",
            "condition": {
                "host_name": "HOSTLIST"
            },
        },
    ]

    tuple_rulesets.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
        ruleset, is_binary=False, is_service=False)

    assert ruleset == [
        {
            "value": "VAL1",
            "condition": {
                "host_name": "HOSTLIST1",
            }
        },
        {
            "value": "VAL",
            "condition": {
                "host_name": "HOSTLIST"
            },
        },
    ]


def test_transform_physical_hosts():
    with pytest.raises(MKGeneralException, match="PHYSICAL_HOSTS"):
        tuple_rulesets.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
            [
                ("VAL1", tuple_rulesets.PHYSICAL_HOSTS),
            ], is_binary=False, is_service=False)


def test_transform_cluster_hosts():
    with pytest.raises(MKGeneralException, match="CLUSTER_HOSTS"):
        tuple_rulesets.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
            [
                ("VAL1", tuple_rulesets.CLUSTER_HOSTS),
            ], is_binary=False, is_service=False)


Case = NamedTuple("Case", [
    ("is_service", bool),
    ("is_binary", bool),
    ("old", tuple),
    ("new", dict),
    ("ident", str),
])

NON_BINARY_HOST_RULESET = [
    Case(
        ident="simple",
        is_service=False,
        is_binary=False,
        old=("VAL", ["HOSTLIST"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": "HOSTLIST"
            },
        },
    ),
    Case(
        ident="list_no_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["HOST1", "HOST2"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {
                    "$in": ["HOST1", "HOST2"]
                }
            },
        },
    ),
    Case(
        ident="host_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["~REGEX"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {
                    "$regex": "^REGEX"
                }
            },
        },
    ),
    Case(
        ident="hosts_negated",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!HOST1", "!HOST2"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {
                    "$nin": ["HOST1", "HOST2"],
                },
            },
        },
    ),
    Case(
        ident="one_host_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["~HOST1", "HOST2"]),
        new={
            "value": "VAL",
            "condition": {
                "$or": [{
                    "host_name": {
                        "$regex": "^HOST1"
                    },
                }, {
                    "host_name": {
                        "$eq": "HOST2"
                    },
                }],
            },
        },
    ),
    Case(
        ident="hosts_negated_with_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!~HOST1", "!HOST2"]),
        new={
            "value": "VAL",
            "condition": {
                "$nor": [{
                    "host_name": {
                        "$regex": "^HOST1"
                    },
                }, {
                    "host_name": {
                        "$eq": "HOST2"
                    },
                }],
            },
        },
    ),
    Case(
        ident="host_tags",
        is_service=False,
        is_binary=False,
        old=("VAL", ["tag", "specs"], ["HOSTLIST"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": "HOSTLIST",
                "host_tags.tg_group1": "tag",
                "host_tags.tg_group2": "specs",
            }
        },
    ),
    Case(
        ident="host_tags",
        is_service=False,
        is_binary=False,
        old=("VAL", ["tag", "specs"], tuple_rulesets.ALL_HOSTS),
        new={
            "value": "VAL",
            "condition": {
                "host_tags.tg_group1": "tag",
                "host_tags.tg_group2": "specs",
            }
        },
    ),
]

BINARY_HOST_RULESET = [
    Case(
        ident="no_tags",
        is_service=False,
        is_binary=True,
        old=(["HOSTLIST"],),
        new={
            "value": True,
            "condition": {
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="empty_tags_all_hosts",
        is_service=False,
        is_binary=True,
        old=(
            [],
            tuple_rulesets.ALL_HOSTS,
        ),
        new={
            "value": True,
            "condition": {},
        },
    ),
    Case(
        ident="negated",
        is_service=False,
        is_binary=True,
        old=(
            tuple_rulesets.NEGATE,
            ["HOSTLIST"],
        ),
        new={
            "value": False,
            "condition": {
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="negated_with_tags",
        is_service=False,
        is_binary=True,
        old=(
            tuple_rulesets.NEGATE,
            ["TAG1"],
            ["HOSTLIST"],
        ),
        new={
            "value": False,
            "condition": {
                "host_name": "HOSTLIST",
                "host_tags.TG1": "TAG1",
            },
        },
    ),
]

NON_BINARY_SERVICE_RULESET = [
    Case(
        ident="simple",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": "VAL",
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="complete_match_regex_no_tags",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOSTLIST"], ["SVC$", "LIST"]),
        new={
            "value": "VAL",
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC$"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="negated_with_all_hosts",
        is_service=True,
        is_binary=False,
        old=("VAL", tuple_rulesets.ALL_HOSTS, ["!SVC", "!LIST"]),
        new={
            "value": "VAL",
            "condition": {
                "$nor": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
            },
        },
    ),
]

BINARY_SERVICE_RULESET = [
    Case(
        ident="simple",
        is_service=True,
        is_binary=True,
        old=(["TAG1"], ["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": True,
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
                "host_tags.TG1": "TAG1",
            },
        },
    ),
    Case(
        ident="no_tags",
        is_service=True,
        is_binary=True,
        old=(["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": True,
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="all_services",
        is_service=True,
        is_binary=True,
        old=(["TAG1"], ["HOSTLIST"], tuple_rulesets.ALL_SERVICES),
        new={
            "value": True,
            "condition": {
                "host_name": "HOSTLIST",
                "host_tags.TG1": "TAG1",
            },
        },
    ),
    Case(
        ident="negated",
        is_service=True,
        is_binary=True,
        old=(tuple_rulesets.NEGATE, ["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": False,
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
            },
        },
    ),
    Case(
        ident="negated_with_tags",
        is_service=True,
        is_binary=True,
        old=(tuple_rulesets.NEGATE, ["TAG1"], ["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": False,
            "condition": {
                "$or": [{
                    "service_description": {
                        "$regex": "^SVC"
                    },
                }, {
                    "service_description": {
                        "$regex": "^LIST"
                    },
                }],
                "host_name": "HOSTLIST",
                "host_tags.TG1": "TAG1",
            },
        },
    ),
]

TAG_TO_GROUP_MAP = {
    "TAG1": "TG1",
    "tag": "tg_group1",
    "specs": "tg_group2",
}


def _generate_id(val):
    """Create textual representation of the test for identification of the test"""
    parts = [
        "service" if val.is_service else "host",
        "binary" if val.is_binary else "non-binary",
        val.ident,
    ]
    return "_".join(parts)


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
    "case",
    NON_BINARY_HOST_RULESET + BINARY_HOST_RULESET + NON_BINARY_SERVICE_RULESET +
    BINARY_SERVICE_RULESET,
    ids=_generate_id)
def test_transform(case, rule_options):
    rule_spec = case.old
    if rule_options is not None:
        rule_spec = rule_spec + (rule_options,)

    ruleset = [rule_spec]
    tuple_rulesets.RulesetToDictTransformer(tag_to_group_map=TAG_TO_GROUP_MAP).transform_in_place(
        ruleset, is_service=case.is_service, is_binary=case.is_binary)

    expected = case.new.copy()
    if rule_options is not None:
        expected["options"] = rule_options

    assert ruleset[0] == expected


def test_get_tag_to_group_map(monkeypatch):
    # Would be cleaner to use existing fixtures from tests/unit/cmk/gui/conftest.py
    import cmk.gui.config as gui_config
    monkeypatch.setattr(gui_config, "omd_site", lambda: "NO_SITE")
    multisite_mk = Path(cmk.utils.paths.default_config_dir) / "multisite.mk"
    multisite_mk.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    multisite_mk.touch()  # pylint: disable=no-member

    assert tuple_rulesets.get_tag_to_group_map(tuple_rulesets.get_tag_config_from_gui()) == {
        'ip-v4v6': 'address_family',
        'snmp-v1': 'snmp',
        'ip-v6': 'ip-v6',
        'all-agents': 'agent',
        'ip-v4': 'ip-v4',
        'snmp': 'snmp',
        'cmk-agent': 'agent',
        'ip-v6-only': 'address_family',
        'ping': 'ping',
        'auto-piggyback': 'piggyback',
        'tcp': 'tcp',
        'no-snmp': 'snmp',
        'piggyback': 'piggyback',
        'ip-v4-only': 'address_family',
        'snmp-v2': 'snmp',
        'no-piggyback': 'piggyback',
        'no-ip': 'address_family',
        'no-agent': 'agent',
        'special-agents': 'agent',
    }
