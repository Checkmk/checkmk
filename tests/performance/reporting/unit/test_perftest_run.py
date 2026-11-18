#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import date

import pytest

from tests.performance.reporting.perftest_run import (
    database,
    job_name,
    run_date,
    upload,
    version,
)

TODAY = date(2026, 11, 18)


@pytest.mark.parametrize(
    "given, env, name",
    [
        pytest.param("daily", {}, "2.6.0-2026.11.18.pro", id="daily"),
        pytest.param("2.5.0p3", {}, "2.5.0p3.pro", id="version"),
        pytest.param("2.5.0p3", {"RELEASE": "2.5.0p3.custom"}, "2.5.0p3.custom", id="release"),
    ],
)
def test_a_job_is_named_after_its_version_and_edition_or_release(
    given: str, env: dict[str, str], name: str
) -> None:
    assert job_name(version(given, "2.6.0", TODAY), "pro", env) == name


def test_a_run_belongs_to_the_day_it_started() -> None:
    assert run_date({"PERFTEST_DATE": "2026-11-17"}) == date(2026, 11, 17)


@pytest.mark.parametrize(
    "suite, db",
    [
        ("data-backend", "performance_data_backend"),
        ("monitoring_views", "performance_component"),
    ],
)
def test_a_suite_uploads_into_its_database(suite: str, db: str) -> None:
    assert database(suite) == db


def test_failed_check_fails_the_upload_after_all_checks_ran() -> None:
    runs: list[Sequence[str]] = []

    def plot(args: Sequence[str]) -> int:
        runs.append(args)
        return 2 if len(runs) == 1 else 0

    uploaded = upload(["--root-dir=results"], plot=plot)

    assert not uploaded
    assert len(runs) == 3
