#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_config_backup import (
    check_veeam_config_backup,
    CheckParameters,
    ConfigBackup,
    discovery_veeam_config_backup,
    parse_veeam_config_backup,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch

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
    results = list(check_veeam_config_backup(PARAMS, section))
    assert results == [Result(state=State.WARN, summary="Configuration backup disabled")]


def test_check_veeam_config_backup_disabled_state_is_configurable() -> None:
    params = CheckParameters(disabled_state=0, age=PARAMS["age"])
    assert (section := parse_veeam_config_backup(_config_backup(isEnabled=False))) is not None
    results = list(check_veeam_config_backup(params, section))
    assert results == [Result(state=State.OK, summary="Configuration backup disabled")]


def test_check_veeam_config_backup_never_run_is_crit() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(lastSuccessfulBackup={"sessionId": "abc-123"})
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section))
    assert Result(state=State.CRIT, summary="No successful backup yet") in results


def test_check_veeam_config_backup_reports_age_metric() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(
                lastSuccessfulBackup={"lastSuccessfulTime": "2019-01-21T00:00:00.000+00:00"}
            )
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section))
    assert any(isinstance(r, Metric) and r.name == "veeam_config_backup_age" for r in results)


def test_check_veeam_config_backup_future_timestamp_does_not_crash() -> None:
    assert (
        section := parse_veeam_config_backup(
            _config_backup(
                lastSuccessfulBackup={"lastSuccessfulTime": "2999-01-21T00:00:00.000+00:00"}
            )
        )
    ) is not None
    results = list(check_veeam_config_backup(PARAMS, section))
    assert any(
        isinstance(r, Result) and "last successful backup is in the future" in r.summary
        for r in results
    )


def test_check_veeam_config_backup_details() -> None:
    assert (section := parse_veeam_config_backup(_config_backup())) is not None
    results = list(check_veeam_config_backup(PARAMS, section))
    assert Result(state=State.OK, summary="Restore points kept: 7") in results
    assert Result(state=State.OK, summary="Encryption: enabled") in results
    assert Result(state=State.OK, summary="Target repository ID: repo-1") in results
