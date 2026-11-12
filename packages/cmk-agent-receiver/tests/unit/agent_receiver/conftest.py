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

from cmk.agent_receiver.agent_receiver.checkmk_rest_api import ControllerCertSettings
from cmk.agent_receiver.lib.certs import agent_root_ca, get_local_site_cn, relay_root_ca
from cmk.agent_receiver.lib.config import Config, get_config
from cmk.agent_receiver.main import main_app
from cmk.testlib.agent_receiver.certs import set_up_site_certs


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
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


@pytest.fixture
def site_edition() -> str:
    # Unlike Community, Pro offers agent updates. Unlike Ultimate, it has no relays.
    return "pro"


@pytest.fixture
def setup_site_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, site_edition: str
) -> Iterator[Config]:
    site_env(monkeypatch, tmp_path)
    get_config.cache_clear()
    config = get_config()
    (config.omd_root / "version").symlink_to(f"some.detailed.version.{site_edition}")
    config.agent_output_dir.mkdir(parents=True)
    config.r4r_dir.mkdir(parents=True)
    config.log_path.parent.mkdir(parents=True)
    set_up_site_certs(config=config)
    yield config
    # Tests that use the site without requesting it must fail, not reuse this one.
    get_config.cache_clear()
    agent_root_ca.cache_clear()
    relay_root_ca.cache_clear()
    get_local_site_cn.cache_clear()


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def mock_controller_certificate_settings(mocker: MockerFixture) -> None:
    mocker.patch("cmk.agent_receiver.agent_receiver.endpoints.internal_credentials")
    mocker.patch(
        "cmk.agent_receiver.agent_receiver.endpoints.controller_certificate_settings",
        return_value=ControllerCertSettings(lifetime_in_months=12),
    )


@pytest.fixture(name="client")
def fixture_client(setup_site_context: Config) -> Iterator[TestClient]:
    # Through the main app, so that its lifespan runs as in production.
    with TestClient(
        main_app(),
        base_url=f"http://testserver/{setup_site_context.site_name}/agent-receiver",
    ) as client:
        yield client


@pytest.fixture(name="uuid", scope="session")
def fixture_uuid() -> UUID4:
    return UUID(str(uuid4()))
