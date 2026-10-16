#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.mysql import check_mysql_connections, parse_mysql


def test_mysql_connections_check_without_max_connections() -> None:
    # Crash group 4823: the service was discovered, but a later agent output
    # lacked the server variable max_connections.
    parsed = parse_mysql([["Max_used_connections", "80"], ["Threads_connected", "10"]])

    assert list(check_mysql_connections("mysql", {}, parsed)) == [
        (3, "Connection information is missing: max_connections"),
    ]
