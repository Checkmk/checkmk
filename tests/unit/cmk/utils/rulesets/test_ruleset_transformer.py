#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, NamedTuple, Tuple, Union

import pytest

import cmk.utils.paths
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
import cmk.utils.tags
from cmk.utils.exceptions import MKGeneralException


def test_transform_tuple_ruleset():
    ruleset: Union[List[Tuple[str, List[str]]], List[Dict[str, List[str]]]] = [
        ("VAL1", ["HOSTLIST1"]),
        ("VAL2", ["HOSTLIST2"]),
    ]

    ruleset_matcher.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
        ruleset, is_binary=False, is_service=False
    )

    assert ruleset == [
        {
            "value": "VAL1",
            "condition": {
                "host_name": ["HOSTLIST1"],
            },
        },
        {
            "value": "VAL2",
            "condition": {
                "host_name": ["HOSTLIST2"],
            },
        },
    ]


def test_transform_mixed_ruleset():
    ruleset = [
        ("VAL1", ["HOSTLIST1"]),
        {
            "value": "VAL",
            "condition": {
                "host_name": ["HOSTLIST"],
            },
        },
    ]

    ruleset_matcher.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
        ruleset, is_binary=False, is_service=False
    )

    assert ruleset == [
        {
            "value": "VAL1",
            "condition": {
                "host_name": ["HOSTLIST1"],
            },
        },
        {
            "value": "VAL",
            "condition": {
                "host_name": ["HOSTLIST"],
            },
        },
    ]


def test_transform_physical_hosts():
    with pytest.raises(MKGeneralException, match="PHYSICAL_HOSTS"):
        ruleset_matcher.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
            [
                ("VAL1", tuple_rulesets.PHYSICAL_HOSTS),
            ],
            is_binary=False,
            is_service=False,
        )


def test_transform_cluster_hosts():
    with pytest.raises(MKGeneralException, match="CLUSTER_HOSTS"):
        ruleset_matcher.RulesetToDictTransformer(tag_to_group_map={}).transform_in_place(
            [
                ("VAL1", tuple_rulesets.CLUSTER_HOSTS),
            ],
            is_binary=False,
            is_service=False,
        )


class Case(NamedTuple):
    is_service: bool
    is_binary: bool
    old: tuple
    new: dict
    ident: str


NON_BINARY_HOST_RULESET = [
    Case(
        ident="simple",
        is_service=False,
        is_binary=False,
        old=("VAL", ["HOSTLIST"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": ["HOSTLIST"],
            },
        },
    ),
    Case(
        ident="empty_host_list",
        is_service=False,
        is_binary=False,
        old=("VAL", []),
        new={
            "value": "VAL",
            "condition": {
                "host_name": [],
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
                "host_name": ["HOST1", "HOST2"],
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
                "host_name": [
                    {"$regex": "REGEX"},
                ]
            },
        },
    ),
    Case(
        ident="multi_host_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["~REGEX", "~2REGEX"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": [
                    {"$regex": "REGEX"},
                    {"$regex": "2REGEX"},
                ],
            },
        },
    ),
    Case(
        ident="hosts_negated",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!HOST1", "!HOST2"] + tuple_rulesets.ALL_HOSTS),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {"$nor": ["HOST1", "HOST2"]},
            },
        },
    ),
    Case(
        ident="single_host_negated",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!HOST1"] + tuple_rulesets.ALL_HOSTS),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {"$nor": ["HOST1"]},
            },
        },
    ),
    Case(
        ident="single_host_regex_negated",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!~HOST1"] + tuple_rulesets.ALL_HOSTS),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {
                    "$nor": [
                        {"$regex": "HOST1"},
                    ],
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
                "host_name": [
                    {"$regex": "HOST1"},
                    "HOST2",
                ],
            },
        },
    ),
    Case(
        ident="hosts_negated_with_regex",
        is_service=False,
        is_binary=False,
        old=("VAL", ["!~HOST1", "!HOST2"] + tuple_rulesets.ALL_HOSTS),
        new={
            "value": "VAL",
            "condition": {
                "host_name": {
                    "$nor": [
                        {"$regex": "HOST1"},
                        "HOST2",
                    ],
                },
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
                "host_name": ["HOSTLIST"],
                "host_tags": {
                    "tg_group1": "tag",
                    "tg_group2": "specs",
                },
            },
        },
    ),
    Case(
        ident="host_tags_with_folder",
        is_service=False,
        is_binary=False,
        old=("VAL", ["tag", "specs", "/aaa/+"], ["HOSTLIST"]),
        new={
            "value": "VAL",
            "condition": {
                "host_name": ["HOSTLIST"],
                "host_folder": "/aaa/",
                "host_tags": {
                    "tg_group1": "tag",
                    "tg_group2": "specs",
                },
            },
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
                "host_tags": {
                    "tg_group1": "tag",
                    "tg_group2": "specs",
                },
            },
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
                "host_name": ["HOSTLIST"],
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
                "host_name": ["HOSTLIST"],
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
                "host_name": ["HOSTLIST"],
                "host_tags": {"TG1": "TAG1"},
            },
        },
    ),
    Case(
        ident="not_equal_tag_match",
        is_service=False,
        is_binary=True,
        old=(["!TAG1", "!TAG2"], tuple_rulesets.ALL_HOSTS),
        new={
            "value": True,
            "condition": {
                "host_tags": {
                    "TG1": {"$ne": "TAG1"},
                    "TG2": {"$ne": "TAG2"},
                },
            },
        },
    ),
]

NON_BINARY_SERVICE_RULESET = [
    Case(
        ident="simple_single_service",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOST"], ["SVC"]),
        new={
            "value": "VAL",
            "condition": {
                "service_description": [{"$regex": "SVC"}],
                "host_name": ["HOST"],
            },
        },
    ),
    Case(
        ident="simple_single_service_negated",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOST"], ["!SVC"] + tuple_rulesets.ALL_SERVICES),
        new={
            "value": "VAL",
            "condition": {
                "service_description": {"$nor": [{"$regex": "SVC"}]},
                "host_name": ["HOST"],
            },
        },
    ),
    Case(
        ident="simple",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOSTLIST"], ["SVC", "LIST"]),
        new={
            "value": "VAL",
            "condition": {
                "service_description": [
                    {"$regex": "SVC"},
                    {"$regex": "LIST"},
                ],
                "host_name": ["HOSTLIST"],
            },
        },
    ),
    Case(
        ident="empty_item_list",
        is_service=True,
        is_binary=False,
        old=("VAL", ["HOSTLIST"], []),
        new={
            "value": "VAL",
            "condition": {
                "service_description": [],
                "host_name": ["HOSTLIST"],
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
                "service_description": [
                    {"$regex": "SVC$"},
                    {"$regex": "LIST"},
                ],
                "host_name": ["HOSTLIST"],
            },
        },
    ),
    Case(
        ident="negated_with_all_hosts",
        is_service=True,
        is_binary=False,
        old=("VAL", tuple_rulesets.ALL_HOSTS, ["!SVC", "!LIST"] + tuple_rulesets.ALL_SERVICES),
        new={
            "value": "VAL",
            "condition": {
                "service_description": {
                    "$nor": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                }
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
                "service_description": [
                    {"$regex": "SVC"},
                    {"$regex": "LIST"},
                ],
                "host_name": ["HOSTLIST"],
                "host_tags": {"TG1": "TAG1"},
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
                "service_description": [
                    {"$regex": "SVC"},
                    {"$regex": "LIST"},
                ],
                "host_name": ["HOSTLIST"],
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
                "host_name": ["HOSTLIST"],
                "host_tags": {"TG1": "TAG1"},
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
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                "host_name": ["HOSTLIST"],
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
                "service_description": [
                    {"$regex": "SVC"},
                    {"$regex": "LIST"},
                ],
                "host_name": ["HOSTLIST"],
                "host_tags": {"TG1": "TAG1"},
            },
        },
    ),
    Case(
        ident="list_of_hosts_and_services",
        is_service=True,
        is_binary=True,
        old=(tuple_rulesets.NEGATE, ["HOST", "LIST"], ["SVC", "LIST"]),
        new={
            "value": False,
            "condition": {
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
                "host_name": ["HOST", "LIST"],
            },
        },
    ),
    Case(
        ident="list_of_host_regexes_and_services",
        is_service=True,
        is_binary=True,
        old=(tuple_rulesets.NEGATE, ["~HOST", "~LIST"], ["SVC", "LIST"]),
        new={
            "value": False,
            "condition": {
                "host_name": [
                    {"$regex": "HOST"},
                    {"$regex": "LIST"},
                ],
                "service_description": [
                    {"$regex": "SVC"},
                    {"$regex": "LIST"},
                ],
            },
        },
    ),
    Case(
        ident="list_of_host_regexes_and_services_negated",
        is_service=True,
        is_binary=True,
        old=(
            tuple_rulesets.NEGATE,
            ["!~HOST", "!~LIST"] + tuple_rulesets.ALL_HOSTS,
            ["!SVC", "!LIST"] + tuple_rulesets.ALL_SERVICES,
        ),
        new={
            "value": False,
            "condition": {
                "host_name": {
                    "$nor": [
                        {"$regex": "HOST"},
                        {"$regex": "LIST"},
                    ]
                },
                "service_description": {
                    "$nor": [
                        {"$regex": "SVC"},
                        {"$regex": "LIST"},
                    ]
                },
            },
        },
    ),
]

TAG_TO_GROUP_MAP = {
    "TAG1": "TG1",
    "TAG2": "TG2",
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
        {"disabled": True},
        None,
    ],
)
@pytest.mark.parametrize(
    "case",
    NON_BINARY_HOST_RULESET
    + BINARY_HOST_RULESET
    + NON_BINARY_SERVICE_RULESET
    + BINARY_SERVICE_RULESET,
    ids=_generate_id,
)
def test_transform(case, rule_options):
    rule_spec = case.old
    if rule_options is not None:
        rule_spec = rule_spec + (rule_options,)

    ruleset = [rule_spec]
    ruleset_matcher.RulesetToDictTransformer(tag_to_group_map=TAG_TO_GROUP_MAP).transform_in_place(
        ruleset, is_service=case.is_service, is_binary=case.is_binary
    )

    expected = case.new.copy()
    if rule_options is not None:
        expected["options"] = rule_options

    assert ruleset[0] == expected


def test_get_tag_to_group_map(monkeypatch):
    tag_config = cmk.utils.tags.TagConfig.from_config(
        {
            "aux_tags": [{"id": "bla", "title": "bl\xfcb"}],
            "tag_groups": [
                {
                    "id": "criticality",
                    "tags": [
                        {"aux_tags": ["bla"], "id": "prod", "title": "Productive system"},
                    ],
                    "title": "Criticality",
                },
                {
                    "id": "networking",
                    "tags": [
                        {"aux_tags": [], "id": "lan", "title": "Local network (low latency)"},
                    ],
                    "title": "Networking Segment",
                },
            ],
        }
    )
    assert ruleset_matcher.get_tag_to_group_map(tag_config) == {
        "bla": "bla",
        "lan": "networking",
        "prod": "criticality",
    }
