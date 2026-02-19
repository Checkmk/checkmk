#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site


@pytest.mark.skip_if_edition("community", "pro", "cloud")
def test_clickhouse_exists(site: Site) -> None:
    assert (site.root / "bin" / "clickhouse").exists()


@pytest.mark.skip_if_edition("community", "pro", "cloud")
def test_clickhouse_executable(site: Site) -> None:
    assert (
        "ClickHouse local version 25.8.16.10001.altinitystable (altinity build)."
        in site.check_output(["clickhouse", "--version"])
    )
