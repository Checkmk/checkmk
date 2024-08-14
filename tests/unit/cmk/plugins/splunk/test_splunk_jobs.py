#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.splunk.agent_based import splunk_jobs as plugin


def test_parse_splunk_jobs() -> None:
    string_table = [
        ["2019-05-16T11:17:00.000+00:00", "splunk-system-user", "app", "DONE", "True"],
        ["2019-05-16T10:17:01.000+00:00", "admin", "app", "FAILED", "False"],
    ]

    actual = plugin.parse_splunk_jobs(string_table)
    expected = plugin.JobsInfo(
        jobs=(
            plugin.Job(
                published_at=datetime.datetime(2019, 5, 16, 11, 17, tzinfo=ZoneInfo("UTC")),
                author="splunk-system-user",
                application="app",
                dispatch_state="DONE",
                is_zombie=True,
            ),
            plugin.Job(
                published_at=datetime.datetime(2019, 5, 16, 10, 17, 1, tzinfo=ZoneInfo("UTC")),
                author="admin",
                application="app",
                dispatch_state="FAILED",
                is_zombie=False,
            ),
        ),
        meta=plugin.JobsMetaInfo(count=2, failures=1, zombies=1),
    )

    assert actual == expected


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(
            ["<datetime>", "splunk-system-user", "app", "DONE", "True"],
            id="bad datetime for 'published_at' field",
        ),
        pytest.param(
            ["2019-05-16T11:17:00.000+00:00", "splunk-system-user", "app", "DONE", "<bool>"],
            id="bad bool for 'is_zombie' field",
        ),
        pytest.param(
            ["2019-05-16T11:17:00.000+00:00", "splunk-system-user", "app", "DONE"],
            id="missing field",
        ),
        pytest.param(
            ["2019-05-16T11:17:00.000+00:00", "splunk-system-user", "app", "DONE", "True", "[x]"],
            id="too many fields",
        ),
    ],
)
def test_parse_splunk_jobs_ignores_bad_agent_output(string_table: StringTable) -> None:
    actual = plugin.parse_splunk_jobs(string_table)
    expected = plugin.JobsInfo(
        jobs=tuple(), meta=plugin.JobsMetaInfo(count=0, failures=0, zombies=0)
    )
    assert actual == expected


def test_check_splunk_jobs() -> None:
    sections = plugin.JobsInfo(
        jobs=(
            plugin.Job(
                published_at=datetime.datetime(2019, 5, 16, 11, 17, tzinfo=ZoneInfo("UTC")),
                author="system",
                application="app",
                dispatch_state="DONE",
                is_zombie=True,
            ),
            plugin.Job(
                published_at=datetime.datetime(2019, 5, 16, 10, 17, 1, tzinfo=ZoneInfo("UTC")),
                author="admin",
                application="app",
                dispatch_state="FAILED",
                is_zombie=False,
            ),
        ),
        meta=plugin.JobsMetaInfo(count=2, failures=1, zombies=1),
    )
    params = plugin.CheckParams(
        job_count=("fixed", (10, 15)),
        failed_count=("fixed", (0, 0)),
        zombie_count=("fixed", (1, 2)),
    )

    *actual, job_1, job_2 = list(plugin.check_splunk_jobs(params=params, section=sections))
    expected: CheckResult = [
        Result(state=State.OK, summary="Job count: 2"),
        Metric("job_total", 2.0, levels=(10.0, 15.0)),
        Result(state=State.CRIT, summary="Failed jobs: 1 (warn/crit at 0/0)"),
        Metric("failed_total", 1.0, levels=(0.0, 0.0)),
        Result(state=State.WARN, summary="Zombie jobs: 1 (warn/crit at 1/2)"),
        Metric("zombie_total", 1.0, levels=(1.0, 2.0)),
    ]

    assert actual == expected

    assert isinstance(job_1, Result)
    assert "Author: system, Application: app, State: DONE, Zombie: True" in job_1.details

    assert isinstance(job_2, Result)
    assert "Author: admin, Application: app, State: FAILED, Zombie: False" in job_2.details
