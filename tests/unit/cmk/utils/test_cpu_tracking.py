#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.utils.cpu_tracking import Snapshot


def json_identity(serializable: object) -> object:
    return json.loads(json.dumps(serializable))


class TestCpuTracking:
    @pytest.fixture
    def null(self) -> Snapshot:
        return Snapshot.null()

    @pytest.fixture
    def now(self) -> Snapshot:
        return Snapshot.take()

    def test_eq_neq(self, null: Snapshot, now):
        assert null == Snapshot.null()
        assert null != now
        assert now != null
        assert bool(null) is False
        assert bool(now) is True

    def test_add_null_null(self, null: Snapshot) -> None:
        assert null + null == null

    def test_add_null_now(self, null: Snapshot, now) -> None:
        assert null + now == now

    def test_sub_null_null(self, null: Snapshot) -> None:
        assert null - null == null

    def test_sub_now_null(self, now: Snapshot, null: Snapshot) -> None:
        assert now - null == now

    def test_sub_now_now(self, now: Snapshot, null: Snapshot) -> None:
        assert now - now == null

    def test_json_serialization_null(self, null: Snapshot) -> None:
        assert Snapshot.deserialize(json_identity(null.serialize())) == null

    def test_json_serialization_now(self, now) -> None:
        assert Snapshot.deserialize(json_identity(now.serialize())) == now
