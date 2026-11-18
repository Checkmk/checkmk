#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from collections.abc import Mapping
from pathlib import Path

import pytest

import cmk.product_usage.collectors.site_creation as site_creation_collector


def test_platform_creation_time_is_the_time_that_the_platform_passes_in_the_cloud_edition_config(
    tmp_path: Path,
) -> None:
    _write_cloud_edition_config(tmp_path, {"site_created_at": 1767600000})

    created_at = site_creation_collector.platform_creation_time(tmp_path)

    assert created_at == 1767600000


@pytest.mark.parametrize(
    "edition_config",
    [
        pytest.param({"site_created_at": None}, id="null"),
        pytest.param({}, id="missing"),
    ],
)
def test_site_without_a_creation_time_from_the_platform_has_no_platform_creation_time(
    tmp_path: Path, edition_config: Mapping[str, object]
) -> None:
    _write_cloud_edition_config(tmp_path, edition_config)

    created_at = site_creation_collector.platform_creation_time(tmp_path)

    assert created_at is None


@pytest.mark.parametrize(
    "site_created_at",
    [
        pytest.param("1767600000", id="string"),
        pytest.param(True, id="boolean"),
        pytest.param(1767600000.5, id="fraction"),
        pytest.param(0, id="zero"),
    ],
)
def test_platform_creation_time_rejects_a_value_that_is_no_positive_whole_number_of_seconds(
    tmp_path: Path, site_created_at: object
) -> None:
    _write_cloud_edition_config(tmp_path, {"site_created_at": site_created_at})

    with pytest.raises(ValueError):
        site_creation_collector.platform_creation_time(tmp_path)


def test_site_without_an_edition_config_reads_the_creation_time_from_the_admin_panel_url_file(
    tmp_path: Path,
) -> None:
    # The platform still writes the Cloud edition config under its old name
    _write_cloud_edition_config(
        tmp_path, {"site_created_at": 1767600000}, file_name="admin_panel_url.json"
    )

    created_at = site_creation_collector.platform_creation_time(tmp_path)

    assert created_at == 1767600000


def test_site_with_both_files_reads_the_creation_time_from_the_edition_config(
    tmp_path: Path,
) -> None:
    _write_cloud_edition_config(tmp_path, {"site_created_at": 1767700000})
    _write_cloud_edition_config(
        tmp_path, {"site_created_at": 1767600000}, file_name="admin_panel_url.json"
    )

    created_at = site_creation_collector.platform_creation_time(tmp_path)

    assert created_at == 1767700000


def test_site_with_an_edition_config_without_a_creation_time_ignores_the_admin_panel_url_file(
    tmp_path: Path,
) -> None:
    # Like load_cloud_edition_config(): the edition config replaces the old file, it adds nothing
    _write_cloud_edition_config(tmp_path, {})
    _write_cloud_edition_config(
        tmp_path, {"site_created_at": 1767600000}, file_name="admin_panel_url.json"
    )

    created_at = site_creation_collector.platform_creation_time(tmp_path)

    assert created_at is None


def test_instance_id_creation_time_is_the_instance_id_modification_time_in_whole_seconds(
    tmp_path: Path,
) -> None:
    _write_instance_id(tmp_path, mtime=1767700800.75)

    created_at = site_creation_collector.instance_id_creation_time(tmp_path)

    assert created_at == 1767700800


def _write_cloud_edition_config(
    cloud_config_dir: Path,
    fields: Mapping[str, object],
    *,
    file_name: str = "edition_config.json",
) -> None:
    """Write a shortened Cloud edition config: the collector reads only the creation time"""
    (cloud_config_dir / file_name).write_text(json.dumps(fields))


def _write_instance_id(omd_root: Path, *, mtime: float) -> None:
    instance_id = omd_root / "etc/omd/instance_id"
    instance_id.parent.mkdir(parents=True)
    instance_id.write_text("0f8fad5b-d9cb-469f-a165-70867728950e")
    os.utime(instance_id, (1767790000, mtime))
