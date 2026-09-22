#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest import mock

import pytest

from cmk.livestatus_client import (
    get_rrd_data,
    LqUnsafeValueError,
    RRDResponse,
    SingleSiteConnection,
)
from cmk.livestatus_client.queries import Query


def _connection_returning(response: object) -> mock.Mock:
    connection: mock.Mock = mock.create_autospec(SingleSiteConnection, instance=True)
    connection.query_value.return_value = response
    return connection


def _compiled_query(connection: mock.Mock) -> str:
    connection.query_value.assert_called_once()
    query: Query = connection.query_value.call_args.args[0]
    return query.compile()


def test_get_rrd_data_wire_format_and_response() -> None:
    connection = _connection_returning([100, 200, 1, 1.5, 2.5])

    response = get_rrd_data(connection, "my-host", "CPU load", "load1.max", 100, 200)

    assert _compiled_query(connection) == (
        "GET services\n"
        "Columns: rrddata:m1:load1.max:100:200:1:400\n"
        "Filter: host_name = my-host\n"
        "Filter: description = CPU load\n"
        "And: 2"
    )
    assert response == RRDResponse(range(100, 200, 1), [1.5, 2.5])


def test_get_rrd_data_queries_hosts_table_for_host_graphs() -> None:
    connection = _connection_returning([100, 200, 1, 0.5])

    response = get_rrd_data(connection, "my-host", "_HOST_", "load1.max", 100, 200)

    assert _compiled_query(connection) == (
        "GET hosts\nColumns: rrddata:m1:load1.max:100:200:1:400\nFilter: name = my-host"
    )
    assert response == RRDResponse(range(100, 200, 1), [0.5])


def test_get_rrd_data_rejects_newline_in_rpn() -> None:
    connection = _connection_returning([])
    with pytest.raises(LqUnsafeValueError, match="Invalid Livestatus Query string"):
        get_rrd_data(connection, "my-host", "CPU load", "load1.max\nFilter: injected", 100, 200)
    connection.query_value.assert_not_called()


def test_get_rrd_data_rejects_whitespace_in_rpn() -> None:
    connection = _connection_returning([])
    with pytest.raises(LqUnsafeValueError, match="contains whitespace"):
        get_rrd_data(connection, "my-host", "CPU load", "load1.max 1 +", 100, 200)
    connection.query_value.assert_not_called()
