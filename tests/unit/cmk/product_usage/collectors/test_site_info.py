#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

import pytest
from pytest_mock import MockerFixture, MockType

import cmk.product_usage.collectors.site_info as site_info_collector
from cmk.product_usage.exceptions import SiteInfoInvalidError, SiteInfoItemsInvalidError
from cmk.utils.paths import check_mk_config_dir, omd_root, var_dir


@pytest.fixture()
def wato_path() -> Path:
    # Almost all paths in cmk.utils.paths are patched by default in tests/unit/conftest.py
    wato_fp = check_mk_config_dir / "wato"
    wato_fp.mkdir(parents=True, exist_ok=True)
    return wato_fp


@pytest.fixture()
def mock_checkmk_info(mocker: MockerFixture) -> None:
    mocker.patch(
        "cmk.ccc.version.get_general_version_infos",
        return_value={"version": "2.2.0", "edition": "pro"},
    )


@pytest.mark.usefixtures("mock_instance_id", "mock_checkmk_info")
def test_collect_and_number_of_folders(local_connection: MockType, wato_path: Path) -> None:
    local_connection.query.return_value = [[10, 20]]

    (wato_path / "folder1" / "subfolder1").mkdir(parents=True, exist_ok=True)
    (wato_path / "folder1" / "subfolder2").mkdir(parents=True, exist_ok=True)
    (wato_path / "folder2" / "subfolder3").mkdir(parents=True, exist_ok=True)

    data = site_info_collector.collect(check_mk_config_dir, var_dir, omd_root)

    assert data.count_hosts == 10
    assert data.count_services == 20
    assert data.count_folders == 5
    assert data.edition == "pro"
    assert data.cmk_version == "2.2.0"


@pytest.mark.usefixtures("mock_instance_id", "mock_checkmk_info")
def test_collect_too_many_columns(local_connection: MockType) -> None:
    local_connection.query.return_value = [[0, 0, "unexpected"]]
    with pytest.raises(SiteInfoItemsInvalidError):
        site_info_collector.collect(check_mk_config_dir, var_dir, omd_root)


@pytest.mark.usefixtures("mock_instance_id", "mock_checkmk_info")
def test_collect_too_few_columns(local_connection: MockType) -> None:
    local_connection.query.return_value = [[0]]
    with pytest.raises(SiteInfoItemsInvalidError):
        site_info_collector.collect(check_mk_config_dir, var_dir, omd_root)


@pytest.mark.usefixtures("mock_instance_id", "mock_checkmk_info")
def test_collect_no_site_info(local_connection: MockType) -> None:
    local_connection.query.return_value = []
    with pytest.raises(SiteInfoInvalidError):
        site_info_collector.collect(check_mk_config_dir, var_dir, omd_root)


def test_get_or_create_product_usage_site_id() -> None:
    product_usage_site_id_fp = site_info_collector.product_usage_site_id_file_path(var_dir)

    assert site_info_collector.get_product_usage_site_id(product_usage_site_id_fp) is None

    product_usage_site_id = site_info_collector.get_or_create_product_usage_site_id(
        product_usage_site_id_fp
    )

    assert isinstance(product_usage_site_id, UUID)

    # We get the ID again to verify it was stored correctly
    assert (
        site_info_collector.get_product_usage_site_id(product_usage_site_id_fp)
        == product_usage_site_id
    )
