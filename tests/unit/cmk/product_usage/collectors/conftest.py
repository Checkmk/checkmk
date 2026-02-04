#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

import pytest
from pytest_mock import MockerFixture, MockType

from cmk.utils.paths import var_dir


@pytest.fixture()
def mock_instance_id() -> None:
    # omd_root is already patched in tests/unit/conftest.py
    instance_id_fp = var_dir / "product_usage" / "site_id"
    instance_id_fp.parent.mkdir(parents=True, exist_ok=True)
    instance_id_fp.write_text(uuid.uuid4().__str__())


@pytest.fixture()
def local_connection(mocker: MockerFixture) -> MockType:
    lc_mock: MockType = mocker.Mock()
    mocker.patch("cmk.product_usage.collectors.checks.LocalConnection", return_value=lc_mock)
    mocker.patch("cmk.product_usage.collectors.site_info.LocalConnection", return_value=lc_mock)
    return lc_mock
