#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.common_fixtures import (
    create_flask_app,
    create_wsgi_app,
    perform_gui_cleanup_after_test,
    perform_load_config,
    perform_load_plugins,
)
from tests.unit.cmk.web_test_app import (
    WebTestAppForCMK,
)


@pytest.fixture()
def load_config(request_context: None) -> Iterator[None]:
    yield from perform_load_config()


@pytest.fixture(scope="session", autouse=True)
def load_plugins() -> None:
    perform_load_plugins()


@pytest.fixture()
def ui_context(load_plugins: None, load_config: None) -> Iterator[None]:
    """Helper fixture to provide an initialized UI context to tests outside of tests/unit/cmk/gui"""
    yield


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
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture()
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    yield from create_wsgi_app(flask_app)
