#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import UUID4
from pytest_mock import MockerFixture
from starlette.routing import Mount

from cmk.agent_receiver.agent_receiver.checkmk_rest_api import ControllerCertSettings
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.main import main_app
from cmk.testlib.agent_receiver.certs import set_up_ca_certs


@pytest.fixture(autouse=True)
def fixture_umask() -> Iterator[None]:
    """Ensure the unit tests always use the same umask"""
    old_mask = os.umask(0o0007)
    try:
        yield
    finally:
        os.umask(old_mask)


def site_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site_id = "NO_SITE"
    site_dir = tmp_path / site_id
    site_dir.mkdir()
    monkeypatch.setenv("OMD_ROOT", str(site_dir))
    monkeypatch.setenv("OMD_SITE", site_id)


@pytest.fixture(autouse=True)
def setup_site_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site_env(monkeypatch, tmp_path)
    config = get_config()
    config.agent_output_dir.mkdir(parents=True)
    config.r4r_dir.mkdir(parents=True)
    config.log_path.parent.mkdir(parents=True)
    set_up_ca_certs(config=config)


@pytest.fixture(autouse=True)
def mock_controller_certificate_settings(mocker: MockerFixture) -> None:
    mocker.patch("cmk.agent_receiver.agent_receiver.endpoints.internal_credentials")
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.controller_certificate_settings",
        return_value=ControllerCertSettings(lifetime_in_months=12),
    )


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    app = main_app()
    assert len(app.routes) == 2
    assert isinstance(mount := app.routes[1], Mount)
    return TestClient(mount.app)


@pytest.fixture(name="uuid")
def fixture_uuid() -> UUID4:
    return UUID(str(uuid4()))
