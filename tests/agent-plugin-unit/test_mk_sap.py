#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple

import agents.plugins.mk_sap as mk_sap

Value = namedtuple("Value", ["value"])  # pylint: disable=collections-namedtuple-call


class FakeConnectionTree:
    def __init__(self, tree_data):
        self.tree_data = tree_data

    def EXTERNAL_USER_NAME(self, value):
        pass

    def MONITOR_NAME(self, value):
        pass

    @property
    def TREE_NODES(self):
        return Value(self.tree_data)

    @property
    def RETURN(self):
        return Value({"TYPE": "NOT_E"})

    def invoke(self):
        pass

    def discover(self, what):
        return self

    def create_function_call(self):
        return self


def test_empty_tree(monkeypatch):
    monkeypatch.setattr(mk_sap, "conn", FakeConnectionTree({}))
    result = mk_sap.mon_tree({"user": "apu_user"}, "apu_ms_name", "apu_mon_name")
    assert result == {}
