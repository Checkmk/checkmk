#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.check_legacy_includes.db2 import parse_db2_dbs
from cmk.base.legacy_checks.db2_connections import check_db2_connections


def test_check_db2_connections_without_port() -> None:
    section = parse_db2_dbs([["[[[db2inst:DB1]]]"], ["connections", "40"]])

    results = list(check_db2_connections("db2inst:DB1", {"levels_total": (150, 200)}, section))

    assert [(state, text) for state, text, *_ in results] == [(0, "Connections: 40")]
