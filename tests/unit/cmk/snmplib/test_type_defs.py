#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Sequence

import pytest

from cmk.utils.type_defs import HostAddress, HostName, SectionName

from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPContext,
    SNMPDetectSpec,
    SNMPHostConfig,
    SpecialColumn,
)

from cmk.base.api.agent_based.type_defs import OIDSpecTuple


class TestSNMPHostConfig:
    @pytest.mark.parametrize(
        ["section_name", "expected_contexts"],
        [
            pytest.param(None, ["bar"], id="blank section name (e.g. for connection test)"),
            pytest.param(SectionName("foo"), ["foo"], id="match"),
            pytest.param(SectionName("bar"), ["bar"], id="default with identical section name"),
            pytest.param(SectionName("foobar"), ["bar"], id="default"),
        ],
    )
    def test_snmpv3_contexts_of(
        self, section_name: SectionName, expected_contexts: Sequence[SNMPContext]
    ) -> None:
        conf = SNMPHostConfig(
            is_ipv6_primary=False,
            hostname=HostName("unittest"),
            ipaddress=HostAddress("127.0.0.1"),
            credentials=("user", "password"),
            port=0,
            is_bulkwalk_host=True,
            is_snmpv2or3_without_bulkwalk_host=True,
            bulk_walk_size_of=0,
            timing={},
            oid_range_limits={},
            snmpv3_contexts=[("foo", ["foo"]), (None, ["bar"])],
            character_encoding=None,
            snmp_backend=SNMPBackendEnum.STORED_WALK,
        )

        ctx = conf.snmpv3_contexts_of(section_name=section_name)
        assert ctx == expected_contexts


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
    base = "1.2"
    tree = BackendSNMPTree.from_frontend(
        base=base,
        oids=[
            OIDSpecTuple("2", "string", False),
            OIDSpecTuple("2", "string", True),
            OIDSpecTuple("2", "binary", False),
            OIDSpecTuple(SpecialColumn.END, "string", False),
        ],
    )

    assert tree.base == base
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
