#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui import login
from cmk.gui.config import Config, get_default_config, make_config_object
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.hosts_and_folders import FolderTree, make_folder_tree
from cmk.ruleset_matcher.tags import get_effective_tag_config
from cmk.utils.redis import disable_redis
from tests.testlib.gui.common_fixtures import (
    create_flask_app,
    create_wsgi_app,
    perform_gui_cleanup_after_test,
    perform_load_config,
    perform_load_plugins,
)
from tests.testlib.gui.users import create_and_destroy_user
from tests.testlib.gui.web_test_app import (
    WebTestAppForCMK,
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


@pytest.fixture()
def load_config(request_context: None) -> Iterator[Config]:
    yield from perform_load_config()


@pytest.fixture(scope="session", autouse=True)
def load_plugins(test_edition: Edition) -> None:
    perform_load_plugins(test_edition)


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of `flask_app` fixture."""
    yield


@pytest.fixture(name="config")
def fixture_config() -> Config:
    raw_config = get_default_config()
    raw_config["tags"] = get_effective_tag_config(raw_config["wato_tags"])
    return make_config_object(raw_config)


@pytest.fixture(name="tree")
def fixture_tree(patch_omd_site: None, config: Config) -> Iterator[FolderTree]:
    with disable_redis():
        yield make_folder_tree(config)


@pytest.fixture()
def with_admin(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin", config=load_config) as user:
        yield user


@pytest.fixture()
def with_admin_login(load_config: Config, with_admin: tuple[UserId, str]) -> Iterator[UserId]:
    user_id = with_admin[0]
    with login.TransactionIdContext(
        user_id, UserPermissions(load_config.roles, permission_registry, {user_id: ["admin"]}, [])
    ):
        yield user_id


@pytest.fixture()
def with_user(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="user", config=load_config) as user:
        yield user


@pytest.fixture()
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    yield from create_wsgi_app(flask_app)
