#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# ruff: noqa: RUF100
# ruff: noqa: I001

from collections import namedtuple

import pytest
from agents.plugins import mk_sap

Value = namedtuple("Value", ["value"])  # nosemgrep: typing-namedtuple-call


class FakeConnectionTree:
    def __init__(self, tree_data):
        self.tree_data = tree_data

    def EXTERNAL_USER_NAME(self, value):
        pass

    def MONITOR_NAME(self, value):
        pass

    @property
    def TREE_NODES(self):
        return self.tree_data

    @property
    def RETURN(self):
        return {"TYPE": "NOT_E"}

    def invoke(self):
        pass

    def discover(self, what):
        return self

    def call(self, func_name, **kwargs):
        return self

    def create_function_call(self):
        return self

    def __getitem__(self, x):
        return getattr(self, x)


def test_empty_tree(monkeypatch):
    fake_connection_tree = FakeConnectionTree({})
    result = mk_sap.mon_tree(
        fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name"
    )
    assert result == {}


def test_simple_tree(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            {"MTNAMESHRT": "root", "ALPARINTRE": 0},
            {"MTNAMESHRT": "02", "ALPARINTRE": 3},
            {"MTNAMESHRT": "01", "ALPARINTRE": 1},
        ]
    )
    result = mk_sap.mon_tree(
        fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name"
    )

    assert result == [
        {"ALPARINTRE": 0, "MTNAMESHRT": "root", "PATH": "apu_ms_name/root"},
        {"ALPARINTRE": 3, "MTNAMESHRT": "02", "PATH": "apu_ms_name/root/01/02"},
        {"ALPARINTRE": 1, "MTNAMESHRT": "01", "PATH": "apu_ms_name/root/01"},
    ]


def test_recursion_simple(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            # this element says it is it's own parent.
            # this happened for three different customer: SUP-6945 SUP-9293 SUP-9015
            {"MTNAMESHRT": "root", "ALPARINTRE": 1},
        ]
    )
    with pytest.raises(mk_sap.SapError):
        mk_sap.mon_tree(fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name")


def test_recursion(monkeypatch):
    fake_connection_tree = FakeConnectionTree(
        [
            # here the recursion is build over multiple elements:
            # 01 parent: 03, 03 parent 02, 02 parent 01
            {"MTNAMESHRT": "01", "ALPARINTRE": 3},
            {"MTNAMESHRT": "02", "ALPARINTRE": 1},
            {"MTNAMESHRT": "03", "ALPARINTRE": 2},
        ]
    )
    with pytest.raises(mk_sap.SapError) as exception:
        mk_sap.mon_tree(fake_connection_tree, {"user": "apu_user"}, "apu_ms_name", "apu_mon_name")
        assert "01" in str(exception.value)
