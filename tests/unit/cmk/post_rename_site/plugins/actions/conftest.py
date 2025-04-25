#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import typing
from collections.abc import Iterator

import pytest
from flask import Flask
from pytest_mock import MockerFixture
from werkzeug.test import create_environ

from tests.unit.cmk.gui.common_fixtures import (
    create_flask_app,
    create_wsgi_app,
    perform_gui_cleanup_after_test,
    perform_load_config,
    perform_load_plugins,
)
from tests.unit.cmk.gui.users import create_and_destroy_user
from tests.unit.cmk.web_test_app import (
    WebTestAppForCMK,
)

from cmk.ccc.user import UserId

from cmk.gui import http


@pytest.fixture()
def admin_auth_request(
    with_admin: tuple[UserId, str],
) -> typing.Generator[http.Request]:
    # NOTE:
    # REMOTE_USER will be omitted by `flask_app.test_client()` if only passed via an
    # environment dict. When however a Request is passed in, the environment of the Request will
    # not be touched.
    user_id, _ = with_admin
    yield http.Request({**create_environ(), "REMOTE_USER": str(user_id)})


@pytest.fixture()
def flask_app(
    patch_omd_site: None,
    use_fakeredis_client: None,
    load_plugins: None,
) -> Iterator[Flask]:
    yield from create_flask_app()


@pytest.fixture(autouse=True)
def gui_cleanup_after_test(
    mocker: MockerFixture,
) -> Iterator[None]:
    yield from perform_gui_cleanup_after_test(mocker)


@pytest.fixture()
def load_config(request_context: None) -> Iterator[None]:
    yield from perform_load_config()


@pytest.fixture(scope="session", autouse=True)
def load_plugins() -> None:
    perform_load_plugins()


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture()
def with_admin(load_config: None) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin") as user:
        yield user


@pytest.fixture()
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    yield from create_wsgi_app(flask_app)


@pytest.fixture(autouse=True)
def post_rename_request_context(
    wsgi_app: WebTestAppForCMK,
    gui_cleanup_after_test: None,
    admin_auth_request: http.Request,
) -> None:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    wsgi_app.get(admin_auth_request)
