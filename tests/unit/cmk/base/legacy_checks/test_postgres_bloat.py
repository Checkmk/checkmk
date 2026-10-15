#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.postgres_bloat import check_postgres_bloat
from cmk.plugins.postgres.lib import parse_dbs


def test_section_without_header_line_is_reported() -> None:
    row = ["np", "pg_catalog", "pg_class", "54", "81", "56", "0.7", "25", "458752", "448 kB"]
    section = parse_dbs(
        [
            ["[databases_start]"],
            ["np"],
            ["[databases_end]"],
            row,
            [*row[:2], "pg_depend", *row[3:]],
        ]
    )

    assert list(check_postgres_bloat("np", {}, section)) == [
        (3, "Cannot evaluate bloat data: column 'tbloat' is missing in the agent output")
    ]
