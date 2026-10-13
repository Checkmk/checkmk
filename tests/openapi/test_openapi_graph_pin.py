#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.unit.rest_api_client import ClientRegistry


def test_get_graph_pin_returns_null_when_never_set(clients: ClientRegistry) -> None:
    assert clients.Graph.get_pin().json == {"pin_time": None}


def test_set_graph_pin_persists_the_timestamp(clients: ClientRegistry) -> None:
    clients.Graph.set_pin(1700000000)

    assert clients.Graph.get_pin().json == {"pin_time": 1700000000}


def test_set_graph_pin_removes_the_pin_when_null(clients: ClientRegistry) -> None:
    clients.Graph.set_pin(1700000000)

    clients.Graph.set_pin(None)

    assert clients.Graph.get_pin().json == {"pin_time": None}
