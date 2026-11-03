#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime, UTC

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_config_backup import (
    check_plugin_veeam_config_backup,
    check_veeam_config_backup,
    CheckParameters,
    ConfigBackup,
    discovery_veeam_config_backup,
    parse_veeam_config_backup,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch

NOW = datetime.fromisoformat("2026-09-21T00:00:00+00:00").timestamp()

PARAMS = CheckParameters(
    disabled_state=1,
    age=("fixed", (48 * 3600.0, 96 * 3600.0)),
)


def _config_backup(**overrides: object) -> list[list[str]]:
    config_dict: dict[str, object] = {
        "isEnabled": True,
        "lastSuccessfulBackup": {"lastSuccessfulTime": "2019-01-21T00:00:00.000+00:00"},
        "restorePointsToKeep": 7,
        "encryption": {"isEnabled": True},
        "backupRepositoryId": "repo-1",
    }
    config_dict.update(overrides)
    return [[json.dumps(config_dict)]]


def test_discovery_veeam_config_backup() -> None:
    assert (section := parse_veeam_config_backup(_config_backup())) is not None
    assert list(discovery_veeam_config_backup(section)) == [Service()]


def test_parse_veeam_config_backup() -> None:
    section = parse_veeam_config_backup(_config_backup())
    assert section == ConfigBackup(
        is_enabled=True,
        last_successful_time=parse_iso8601_epoch("2019-01-21T00:00:00.000+00:00"),
        restore_points_to_keep=7,
        encryption_enabled=True,
        backup_repository_id="repo-1",
    )


def test_parse_veeam_config_backup_never_run() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(lastSuccessfulBackup={"sessionId": "abc-123"})
        )
    ) is not None
    assert section.last_successful_time is None


def test_parse_veeam_config_backup_returns_none_for_empty_section() -> None:
    assert parse_veeam_config_backup([]) is None


def test_check_veeam_config_backup_disabled_is_warn_by_default() -> None:
    assert (section := parse_veeam_config_backup(_config_backup(isEnabled=False))) is not None
    results = list(check_veeam_config_backup(PARAMS, section, now=NOW))
    assert results == [Result(state=State.WARN, summary="Configuration backup disabled")]


def test_check_veeam_config_backup_disabled_state_is_configurable() -> None:
    params = CheckParameters(disabled_state=0, age=PARAMS["age"])
    assert (section := parse_veeam_config_backup(_config_backup(isEnabled=False))) is not None
    results = list(check_veeam_config_backup(params, section, now=NOW))
    assert results == [Result(state=State.OK, summary="Configuration backup disabled")]


def test_check_veeam_config_backup_never_run_is_crit() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(lastSuccessfulBackup={"sessionId": "abc-123"})
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section, now=NOW))
    assert Result(state=State.CRIT, summary="No successful backup yet") in results


def test_check_veeam_config_backup_reports_age_metric() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(
                lastSuccessfulBackup={"lastSuccessfulTime": "2019-01-21T00:00:00.000+00:00"}
            )
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section, now=NOW))
    assert any(isinstance(r, Metric) and r.name == "veeam_config_backup_age" for r in results)


def test_check_veeam_config_backup_summary() -> None:
    assert (section := parse_veeam_config_backup(_config_backup())) is not None
    now = datetime.fromisoformat("2019-01-21T20:05:00+00:00").timestamp()
    results = list(check_veeam_config_backup(PARAMS, section, now=now))
    assert [r.summary for r in results if isinstance(r, Result) and r.summary] == [
        "Last successful backup age: 20 hours 5 minutes"
    ]


def test_check_veeam_config_backup_future_timestamp_has_no_age_metric() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(
                lastSuccessfulBackup={"lastSuccessfulTime": "2999-01-21T00:00:00.000+00:00"}
            )
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section, now=NOW))
    assert Result(state=State.OK, summary="Last successful backup: in the future") in results
    assert not any(isinstance(r, Metric) and r.name == "veeam_config_backup_age" for r in results)


def test_check_veeam_config_backup_details() -> None:
    assert (section := parse_veeam_config_backup(_config_backup())) is not None
    results = list(check_veeam_config_backup(PARAMS, section, now=NOW))
    assert Result(state=State.OK, notice="Restore points kept: 7") in results
    assert Result(state=State.OK, notice="Encryption: enabled") in results
    assert Result(state=State.OK, notice="Target repository ID: repo-1") in results


def _age_state(params: CheckParameters, hours_ago: float) -> State:
    last_success = datetime.fromtimestamp(NOW - hours_ago * 3600, tz=UTC).isoformat()
    assert (
        section := parse_veeam_config_backup(
            _config_backup(lastSuccessfulBackup={"lastSuccessfulTime": last_success})
        )
    ) is not None
    (result,) = (
        r
        for r in check_veeam_config_backup(params, section, now=NOW)
        if isinstance(r, Result) and r.summary.startswith("Last successful backup age")
    )
    return result.state


def test_default_levels_are_the_ones_tested_here() -> None:
    assert check_plugin_veeam_config_backup.check_default_parameters == PARAMS


@pytest.mark.parametrize(
    "hours_ago, expected",
    [
        pytest.param(47, State.OK, id="less than 48 hours"),
        pytest.param(50, State.WARN, id="48 hours or more"),
        pytest.param(100, State.CRIT, id="96 hours or more"),
    ],
)
def test_backup_age_default_levels(hours_ago: float, expected: State) -> None:
    assert _age_state(PARAMS, hours_ago) is expected


def test_changed_backup_age_levels_are_applied() -> None:
    params = CheckParameters(disabled_state=1, age=("fixed", (12 * 3600.0, 24 * 3600.0)))
    assert _age_state(params, 13) is State.WARN
