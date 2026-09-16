#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.global_settings.pages import app_data, ensure_permitted
from cmk.gui.i18n import _l
from cmk.gui.permissions import permission_registry
from cmk.gui.role_types import CustomUserRole
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Integer
from cmk.shared_typing import global_settings as shared
from cmk.web.utils.icons import IconNames
from cmk.web.utils.permission_verification import PermissionName
from tests.testlib.gui.web_test_app import SetConfig, WebTestAppForCMK


@pytest.fixture(name="factory_defaults")
def fixture_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give a factory default to the test variables only, which hides every real variable
    and with it every real group. The real lookup runs an automation that needs a site."""
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: {"test_var_a": 1, "test_var_b": 2}),  # noqa: ARG005
    )


@pytest.fixture(name="executables_variable")
def fixture_executables_variable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: {"actions": 1}),  # noqa: ARG005
    )
    with _registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "actions"):
        yield


@contextmanager
def _registered(group: ConfigVariableGroup, *varnames: str) -> Iterator[None]:
    config_variable_group_registry.register(group)
    variables = [
        ConfigVariable(
            group=group,
            primary_domain=ConfigDomainGUI,
            ident=varname,
            form_spec=lambda context: Integer(title=Title("Test")),  # noqa: ARG005
        )
        for varname in varnames
    ]
    shadowed = [
        config_variable_registry[varname]
        for varname in varnames
        if varname in config_variable_registry
    ]
    for variable in variables:
        config_variable_registry.register(variable)
    try:
        yield
    finally:
        for variable in variables:
            config_variable_registry.unregister(variable.ident())
        for variable in shadowed:
            config_variable_registry.register(variable)
        config_variable_group_registry.unregister(group.ident())


@contextmanager
def _logged_in(user_id: UserId, *permissions: PermissionName) -> Iterator[None]:
    role = CustomUserRole(
        alias="Test role",
        permissions=dict.fromkeys(permissions, True),
        builtin=False,
        basedon="no_permissions",
    )
    with login.TransactionIdContext(
        user_id,
        UserPermissions({"test_role": role}, permission_registry, {user_id: ["test_role"]}, []),
    ):
        yield


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_registered_group_with_a_visible_variable_becomes_a_topic(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topics = app_data(load_config).topics
    assert [topic.headline for topic in topics] == ["Test group"]
    assert [variable.name for variable in topics[0].variables] == ["test_var_a"]


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_group_without_visible_variables_yields_no_topic(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Empty group"), sort_index=1)):
        topics = app_data(load_config).topics
    assert topics == []


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_the_group_icon_and_description_become_the_topic_header(load_config: Config) -> None:
    group = ConfigVariableGroup(
        title=_l("Test group"),
        sort_index=1,
        icon=IconNames.sites,
        description=_l("Configures the test"),
    )
    with _registered(group, "test_var_a"):
        topic = app_data(load_config).topics[0]
    assert topic.icon == shared.IconNames.sites
    assert topic.subline == "Configures the test"


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_group_without_icon_and_description_gets_the_defaults(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topic = app_data(load_config).topics[0]
    assert topic.icon == shared.IconNames.configuration
    assert topic.subline == ""


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_topics_follow_the_group_sort_index(load_config: Config) -> None:
    with (
        _registered(ConfigVariableGroup(title=_l("Later"), sort_index=20), "test_var_a"),
        _registered(ConfigVariableGroup(title=_l("Earlier"), sort_index=10), "test_var_b"),
    ):
        topics = app_data(load_config).topics
    assert [topic.headline for topic in topics] == ["Earlier", "Later"]


@pytest.mark.usefixtures("executables_variable", "with_admin_login")
def test_an_administrator_sees_a_variable_that_adds_executables(load_config: Config) -> None:
    topics = app_data(load_config).topics
    assert [variable.name for variable in topics[0].variables] == ["actions"]


@pytest.mark.usefixtures("executables_variable")
def test_a_variable_the_user_may_not_read_is_left_out(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with _logged_in(with_user[0], "wato.use", "wato.global"):
        assert app_data(load_config).topics == []


@pytest.mark.usefixtures("with_admin_login")
def test_an_administrator_reaches_the_page(load_config: Config) -> None:
    ensure_permitted(load_config)


@pytest.mark.usefixtures("with_user_login")
def test_the_page_needs_the_global_settings_permission(load_config: Config) -> None:
    with pytest.raises(MKAuthException, match="Global settings"):
        ensure_permitted(load_config)


def test_reading_all_modules_suffices_for_the_page(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with _logged_in(with_user[0], "wato.use", "wato.seeall"):
        ensure_permitted(load_config)


@pytest.mark.usefixtures("with_admin_login")
def test_a_disabled_setup_refuses_the_page(load_config: Config) -> None:
    with pytest.raises(MKGeneralException):
        ensure_permitted(dataclasses.replace(load_config, wato_enabled=False))


@pytest.mark.usefixtures(
    "factory_defaults", "patch_theme", "suppress_license_banner", "suppress_license_expiry_header"
)
def test_the_read_only_message_is_shown_on_the_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK, set_config: SetConfig
) -> None:
    with set_config(
        wato_read_only={"enabled": True, "rw_users": [], "message": "Maintenance in progress"}
    ):
        response = logged_in_admin_wsgi_app.get("/NO_SITE/check_mk/global_settings.py", status=200)
    assert "Maintenance in progress" in response.text
