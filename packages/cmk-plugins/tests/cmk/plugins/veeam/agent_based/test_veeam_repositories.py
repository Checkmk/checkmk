#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.veeam.agent_based import veeam_repositories
from cmk.plugins.veeam.agent_based.veeam_repositories import (
    check_veeam_repositories,
    discovery_veeam_repositories,
    parse_veeam_repositories,
    VeeamRepository,
)

PARAMS = {"levels": (80.0, 90.0)}


@pytest.fixture
def _value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(veeam_repositories, "get_value_store", dict)


def _repository(name: str = "repo-1", **overrides: object) -> str:
    repo_dict: dict[str, object] = {
        "id": "id-1",
        "name": name,
        "type": "WinLocal",
        "description": "Primary repository",
        "hostId": "host-id-1",
        "hostName": "repo-host-1",
        "path": "C:\\Backups",
        "capacityGB": 1000.0,
        "freeGB": 500.0,
        "usedSpaceGB": 500.0,
        "isOnline": True,
        "isOutOfDate": False,
    }
    repo_dict.update(overrides)
    return json.dumps(repo_dict)


def test_discovery_veeam_repositories() -> None:
    section = parse_veeam_repositories([[_repository("repo-1")], [_repository("repo-2")]])
    assert list(discovery_veeam_repositories(section)) == [
        Service(item="WinLocal - repo-1"),
        Service(item="WinLocal - repo-2"),
    ]


def test_parse_veeam_repositories() -> None:
    section = parse_veeam_repositories([[_repository("repo-1")]])
    assert section == {
        "WinLocal - repo-1": VeeamRepository(
            type="WinLocal",
            description="Primary repository",
            capacity_gb=1000.0,
            free_gb=500.0,
            is_online=True,
            is_out_of_date=False,
            host_name="repo-host-1",
            path="C:\\Backups",
            extent_type=None,
        )
    }


def test_parse_veeam_repositories_optional_fields_absent() -> None:
    repo_dict = json.loads(_repository())
    del repo_dict["hostName"]
    del repo_dict["path"]
    section = parse_veeam_repositories([[json.dumps(repo_dict)]])
    repository = section["WinLocal - repo-1"]
    assert repository.host_name is None
    assert repository.path is None


def test_parse_veeam_repositories_scaleout_extent_uses_extent_type_as_category() -> None:
    section = parse_veeam_repositories(
        [
            [
                _repository(
                    scaleOutRepositoryDetails={
                        "scaleOutRepositoryId": "so-id-1",
                        "membership": "Performance",
                        "extentType": "WinLocal",
                    }
                )
            ]
        ]
    )
    repository = section["WinLocal Extent - repo-1"]
    assert repository.extent_type == "WinLocal"


def test_check_veeam_repositories_offline_is_crit_and_reports_nothing_else(
    _value_store: None,
) -> None:
    section = parse_veeam_repositories([[_repository(isOnline=False)]])
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    assert results == [Result(state=State.CRIT, summary="Offline")]


def test_check_veeam_repositories_out_of_date_is_warn(_value_store: None) -> None:
    section = parse_veeam_repositories([[_repository(isOutOfDate=True)]])
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    assert Result(state=State.WARN, summary="Out of date") in results


def test_check_veeam_repositories_used_space_is_derived_from_capacity_and_free(
    _value_store: None,
) -> None:
    section = parse_veeam_repositories(
        [[_repository(capacityGB=1000.0, freeGB=500.0, usedSpaceGB=123.0)]]
    )
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    metrics = [r for r in results if isinstance(r, Metric)]
    assert (
        Metric("fs_used", 512000.0, levels=(819200.0, 921600.0), boundaries=(0.0, 1024000.0))
        in metrics
    )


def test_check_veeam_repositories_used_space_ok_below_levels(_value_store: None) -> None:
    section = parse_veeam_repositories([[_repository(capacityGB=1000.0, freeGB=500.0)]])
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    assert any(
        isinstance(r, Result) and r.state == State.OK and r.summary.startswith("Used:")
        for r in results
    )


def test_check_veeam_repositories_used_space_crit_above_levels(_value_store: None) -> None:
    section = parse_veeam_repositories([[_repository(capacityGB=1000.0, freeGB=50.0)]])
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    assert any(
        isinstance(r, Result) and r.state == State.CRIT and r.summary.startswith("Used:")
        for r in results
    )


def test_check_veeam_repositories_default_params_first_run_still_reports_details(
    _value_store: None,
) -> None:
    section = parse_veeam_repositories([[_repository()]])
    results = list(
        check_veeam_repositories("WinLocal - repo-1", FILESYSTEM_DEFAULT_PARAMS, section)
    )
    assert Result(state=State.OK, notice="Host: repo-host-1") in results


def test_check_veeam_repositories_details(_value_store: None) -> None:
    section = parse_veeam_repositories([[_repository()]])
    results = list(check_veeam_repositories("WinLocal - repo-1", PARAMS, section))
    assert Result(state=State.OK, notice="Host: repo-host-1") in results
    assert Result(state=State.OK, notice="Path: C:\\Backups") in results
    assert Result(state=State.OK, notice="Description: Primary repository") in results


def test_check_veeam_repositories_vanished_item_yields_nothing(_value_store: None) -> None:
    section = parse_veeam_repositories([[_repository("repo-1")]])
    assert list(check_veeam_repositories("WinLocal - repo-2", PARAMS, section)) == []
