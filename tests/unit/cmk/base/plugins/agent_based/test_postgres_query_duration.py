#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResults, Result, State
from cmk.base.plugins.agent_based.postgres_query_duration import (
    check_postgres_query_duration,
    cluster_check_postgres_query_duration,
)


# TODO: a named tuple would be nice
def Query(seconds="", pid="", current_query="", usename="", client_addr="", state=""):
    return {
        "seconds": seconds,
        "pid": pid,
        "current_query": current_query,
        "usename": usename,
        "client_addr": client_addr,
        "state": state,
    }


def test_check_postgres_query_duration_no_data() -> None:
    assert list(check_postgres_query_duration("item", {})) == [
        IgnoreResults("Login into database failed"),
    ]


def test_check_postgres_query_duration_no_queries() -> None:
    assert list(check_postgres_query_duration("item", {"item": []})) == [
        Result(state=State.OK, summary="No queries running"),
    ]


def test_check_postgres_query_duration_basic() -> None:
    section = {
        "item": [
            Query(seconds="2"),  # not used
            Query(seconds="23", pid="4242", current_query="Where is Waldo", state="anxious"),
        ]
    }
    assert list(check_postgres_query_duration("item", section)) == [
        Result(state=State.OK, summary="Longest query: 23 seconds"),
        Result(state=State.OK, summary="Query state: anxious"),
        Result(state=State.OK, summary="PID: 4242"),
        Result(state=State.OK, summary="Query: Where is Waldo"),
    ]


def test_cluster_check_postgres_query_duration_basic() -> None:
    node1_section = {
        "item": [
            Query(seconds="23", pid="4242", current_query="Where is Hugo", state="amused"),
        ]
    }
    node2_section = {
        "item": [
            Query(seconds="22", pid="4242", current_query="Where is Waldo", state="anxious"),
        ]
    }

    clustered_sections = {
        "node1": node1_section,
        "node2": node2_section,
    }

    assert list(cluster_check_postgres_query_duration("item", clustered_sections)) == [
        Result(state=State.OK, summary="Longest query: 23 seconds"),
        Result(state=State.OK, summary="Query state: amused"),
        Result(state=State.OK, summary="PID: 4242"),
        Result(state=State.OK, summary="Query: Where is Hugo"),
    ]
