#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.snmplib import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPVersion,
    SpecialColumn,
)

from cmk.agent_based.v1 import OIDBytes, OIDCached, OIDEnd, SNMPTree


class TestSNMPHostConfig:
    def test_serialization(self) -> None:
        conf = SNMPHostConfig(
            is_ipv6_primary=False,
            hostname=HostName("unittest"),
            ipaddress=HostAddress("127.0.0.1"),
            credentials="",
            port=0,
            bulkwalk_enabled=True,
            snmp_version=SNMPVersion.V2C,
            bulk_walk_size_of=0,
            timing={},
            oid_range_limits={},
            snmpv3_contexts=[],
            character_encoding=None,
            snmp_backend=SNMPBackendEnum.STORED_WALK,
        )
        assert conf.deserialize(conf.serialize()) == conf


class TestSNMPDetectSpec:
    @pytest.fixture
    def specs(self):
        return SNMPDetectSpec(
            [
                [
                    ("oid0", "regex0", True),
                    ("oid1", "regex1", True),
                    ("oid2", "regex2", False),
                ]
            ]
        )

    def test_serialization(self, specs: SNMPDetectSpec) -> None:
        assert SNMPDetectSpec.from_json(specs.to_json()) == specs


def test_snmptree_from_frontend() -> None:
    frontend_tree = SNMPTree(
        base="1.2",
        oids=[
            "2",
            OIDCached("2"),
            OIDBytes("2"),
            OIDEnd(),
        ],
    )
    tree = BackendSNMPTree.from_frontend(base=frontend_tree.base, oids=frontend_tree.oids)

    assert tree.base == frontend_tree.base
    assert tree.oids == [
        BackendOIDSpec("2", "string", False),
        BackendOIDSpec("2", "string", True),
        BackendOIDSpec("2", "binary", False),
        BackendOIDSpec(SpecialColumn.END, "string", False),
    ]


@pytest.mark.parametrize(
    "tree",
    [
        BackendSNMPTree(
            base=".1.2.3",
            oids=[
                BackendOIDSpec("4.5.6", "string", False),
                BackendOIDSpec("7.8.9", "string", False),
            ],
        ),
        BackendSNMPTree(
            base=".1.2.3",
            oids=[
                BackendOIDSpec("4.5.6", "binary", False),
                BackendOIDSpec("7.8.9", "string", True),
                BackendOIDSpec(SpecialColumn.END, "string", False),
            ],
        ),
    ],
)
def test_serialize_snmptree(tree: BackendSNMPTree) -> None:
    assert tree.from_json(json.loads(json.dumps(tree.to_json()))) == tree
