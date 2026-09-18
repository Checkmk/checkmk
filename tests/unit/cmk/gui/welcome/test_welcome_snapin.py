#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

import contextlib
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.welcome.snapin import SidebarWelcomeSnapin
from tests.testlib.gui.users import create_and_destroy_user

NO_PERMISSIONS = UserPermissions({}, {}, {}, [])


@contextlib.contextmanager
def _logged_in_admin_created_on(config: Config, version: str | None) -> Iterator[None]:
    custom_attrs = UserSpec() if version is None else UserSpec(created_on_version=version)
    with (
        create_and_destroy_user(role="admin", custom_attrs=custom_attrs, config=config) as (
            user_id,
            _password,
        ),
        login.TransactionIdContext(
            user_id,
            UserPermissions(config.roles, permission_registry, {user_id: ["admin"]}, []),
        ),
    ):
        yield


@pytest.mark.parametrize(
    "created_on_version, included",
    [
        pytest.param(None, False, id="user predating the attribute"),
        pytest.param("2.4.0p5", False, id="user created in 2.4"),
        pytest.param("2.5.0", True, id="user created in 2.5"),
        pytest.param("2.6.0b1", True, id="user created in 2.6"),
    ],
)
def test_default_sidebar_membership_follows_the_user_creation_version(
    load_config: Config,
    created_on_version: str | None,
    included: bool,
) -> None:
    with _logged_in_admin_created_on(load_config, created_on_version):
        assert SidebarWelcomeSnapin.included_in_default_sidebar() is included


def test_snapin_is_visible_to_a_user_who_may_set_up_monitoring(with_admin_login: UserId) -> None:
    assert SidebarWelcomeSnapin.may_see(NO_PERMISSIONS) is True


def test_snapin_is_hidden_from_a_user_without_setup_permissions(with_user_login: UserId) -> None:
    assert SidebarWelcomeSnapin.may_see(NO_PERMISSIONS) is False


def test_snapin_renders_the_welcome_snapin_component(with_admin_login: UserId) -> None:
    with output_funnel.plugged():
        SidebarWelcomeSnapin().show(Config())
        rendered = output_funnel.drain()

    assert "cmk-welcome-snapin" in rendered


def test_snapin_does_not_carry_the_start_page_flag(with_admin_login: UserId) -> None:
    with output_funnel.plugged():
        SidebarWelcomeSnapin().show(Config())
        rendered = output_funnel.drain()

    assert "is_start_url" not in rendered
