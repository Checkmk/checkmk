#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockType

import cmk.product_telemetry.collectors.site_info as site_info_collector
from cmk.product_telemetry.exceptions import SiteInfoInvalidError, SiteInfoItemsInvalidError
from cmk.utils.paths import check_mk_config_dir


@pytest.fixture()
def wato_path() -> Path:
    # Almost all paths in cmk.utils.paths are patched by default in tests/unit/conftest.py
    wato_fp = check_mk_config_dir / "wato"
    wato_fp.mkdir(parents=True, exist_ok=True)
    return wato_fp


@pytest.mark.usefixtures("mock_instance_id")
def test_collect_and_number_of_folders(local_connection: MockType, wato_path: Path) -> None:
    local_connection.query.return_value = [[10, 20, "cre", "2.2.0"]]

    (wato_path / "folder1" / "subfolder1").mkdir(parents=True, exist_ok=True)
    (wato_path / "folder1" / "subfolder2").mkdir(parents=True, exist_ok=True)
    (wato_path / "folder2" / "subfolder3").mkdir(parents=True, exist_ok=True)

    data = site_info_collector.collect(check_mk_config_dir)

    assert data.count_hosts == 10
    assert data.count_services == 20
    assert data.count_folders == 5
    assert data.edition == "cre"
    assert data.cmk_version == "2.2.0"


@pytest.mark.usefixtures("mock_instance_id")
def test_collect_too_many_columns(local_connection: MockType) -> None:
    local_connection.query.return_value = [[0, 0, "test", "1", "unexpected"]]
    with pytest.raises(SiteInfoItemsInvalidError):
        site_info_collector.collect(check_mk_config_dir)


@pytest.mark.usefixtures("mock_instance_id")
def test_collect_too_few_columns(local_connection: MockType) -> None:
    local_connection.query.return_value = [[0, 0, "test"]]
    with pytest.raises(SiteInfoItemsInvalidError):
        site_info_collector.collect(check_mk_config_dir)


@pytest.mark.usefixtures("mock_instance_id")
def test_collect_no_site_info(local_connection: MockType) -> None:
    local_connection.query.return_value = []
    with pytest.raises(SiteInfoInvalidError):
        site_info_collector.collect(check_mk_config_dir)
