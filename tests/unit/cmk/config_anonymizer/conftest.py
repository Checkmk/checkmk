#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from cmk.base import config  # astrein: disable=cmk-module-layer-violation
from cmk.ccc.version import edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.utils import paths
from tests.testlib.gui.common_fixtures import (
    create_flask_app,
    perform_gui_cleanup_after_test,
    perform_load_plugins,
)


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


@pytest.fixture(scope="session", autouse=True)
def load_plugins() -> None:
    perform_load_plugins(edition(paths.omd_root))


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture(scope="session")
def agent_based_plugins() -> AgentBasedPlugins:
    """Load all check plugins, tolerating errors from non-free edition plugins unavailable
    in the community edition (e.g. missing cmk.plugins.graylog.lib)."""
    return config.load_all_plugins()
