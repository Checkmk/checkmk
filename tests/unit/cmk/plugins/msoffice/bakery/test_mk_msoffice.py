#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from json import dumps
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin, PluginConfig, Secret
from cmk.plugins.msoffice.bakery.mk_msoffice import bakery_plugin_mk_msoffice
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "mk_msoffice"
CONFIG = {
    "deployment": ("sync", None),
    "client_id": "b7f1c2e9-4d3a-4e2b-9c1a-8f2e7d6c5b4a",
    "tenant_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "client_secret": Secret(
        "hdggdkIU-dkkjdj-dddfp376-s3cr3tdkdkdlidd6", "explicit_password", "uuid-1"
    ),
}

WINDOWS_JSON_CONFIG = {
    "ClientId": "b7f1c2e9-4d3a-4e2b-9c1a-8f2e7d6c5b4a",
    "TenantId": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "ClientSecret": "hdggdkIU-dkkjdj-dddfp376-s3cr3tdkdkdlidd6",
}

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf=CONFIG,
        files=[
            Plugin(base_os=OS.WINDOWS, source=Path("mk_msoffice.ps1")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=dumps(WINDOWS_JSON_CONFIG, indent=4).splitlines(),
                target=Path("msoffice_cfg.json"),
                include_header=False,
            ),
        ],
    ),
    "do_not_deploy": APIBakeletTestSet(
        conf={"deployment": ("do_not_deploy", None)},
        files=[],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_mk_msoffice(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_mk_msoffice, TEST_SETS[test_name], mocker, tmp_path)
