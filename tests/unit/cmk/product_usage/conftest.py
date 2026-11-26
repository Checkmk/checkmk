#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Iterator

import pytest
import responses
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
    mocker.patch("cmk.product_usage.collectors.inventory.LocalConnection", return_value=lc_mock)
    mocker.patch("cmk.product_usage.collectors.agents.LocalConnection", return_value=lc_mock)
    return lc_mock


@pytest.fixture(name="site_api")
def fixture_site_api() -> Iterator[responses.RequestsMock]:
    """The REST API of this site, which the agent updater collector asks over HTTP

    Every test that reaches collection must hold this, or the collector talks to
    whatever really listens on the port of a developer's site.
    """
    with responses.RequestsMock() as mocked_site_api:
        yield mocked_site_api
