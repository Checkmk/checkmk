#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest  # type: ignore[import]

from cmk.snmplib.type_defs import (
    BackendSNMPTree,
    OIDBytes,
    OIDCached,
    OIDSpec,
    SNMPDetectSpec,
    SpecialColumn,
)


class TestSNMPDetectSpec:
    @pytest.fixture
    def specs(self):
        return SNMPDetectSpec([[
            ("oid0", "regex0", True),
            ("oid1", "regex1", True),
            ("oid2", "regex2", False),
        ]])

    def test_serialization(self, specs):
        assert SNMPDetectSpec.from_json(specs.to_json()) == specs


@pytest.mark.parametrize("base, oids", [
    ('.1.2', ['1', '2']),
    ('.1.2', ['1', OIDCached('2')]),
    ('.1.2', ['1', OIDBytes('2')]),
    ('.1.2', ['1', SpecialColumn.END]),
])
def test_snmptree(base, oids):
    tree = BackendSNMPTree.from_frontend(base=base, oids=oids)

    assert tree.base == base
    assert isinstance(tree.oids, list)
    for oid in tree.oids:
        assert isinstance(oid, (OIDSpec, SpecialColumn))


@pytest.mark.parametrize("tree", [
    BackendSNMPTree(base=".1.2.3", oids=[OIDSpec("4.5.6"), OIDSpec("7.8.9")]),
    BackendSNMPTree(base=".1.2.3", oids=[OIDCached("4.5.6"), OIDBytes("7.8.9")]),
    BackendSNMPTree(base=".1.2.3", oids=[OIDSpec("4.5.6"), SpecialColumn.END]),
    BackendSNMPTree(base=".1.2.3", oids=[OIDBytes("4.5.6"), SpecialColumn.END]),
])
def test_serialize_snmptree(tree):
    assert tree.from_json(json.loads(json.dumps(tree.to_json()))) == tree
