#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Iterator

import pytest

from tests.testlib.gui.openapi_test_helper import (
    clear_app_instance_caches,
    create_api_client,
    create_sample_host_context,
    create_test_groups,
)
from tests.testlib.gui.web_test_app import WebTestAppForCMK
from tests.testlib.rest_api_client import RestApiClient


@pytest.fixture()
def api_client(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str
) -> RestApiClient:
    return create_api_client(aut_user_auth_wsgi_app, base_without_version)


@pytest.fixture()
def with_groups(
    monkeypatch: pytest.MonkeyPatch,
    request_context,
    with_admin_login,
    suppress_remote_automation_calls,
) -> Iterator[None]:
    yield from create_test_groups(monkeypatch)


@pytest.fixture(name="sample_host")
def fixture_sample_host(request_context: None) -> Iterator[str]:
    yield from create_sample_host_context()


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app() -> None:
    clear_app_instance_caches()
