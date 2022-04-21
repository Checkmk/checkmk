#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.users import create_and_destroy_user

import cmk.utils.paths

import cmk.gui.permissions as permissions
from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, LoggedInUser
from cmk.gui.logged_in import user as global_user
from cmk.gui.logged_in import UserContext
from cmk.gui.watolib.utils import may_edit_ruleset


def test_user_context(with_user):
    user_id = with_user[0]
    assert global_user.id is None
    with UserContext(user_id):
        assert global_user.id == user_id
    assert global_user.id is None


def test_super_user_context(request_context, run_as_superuser):
    assert global_user.id is None
    with run_as_superuser():
        assert global_user.role_ids == ["admin"]
    assert global_user.id is None


def test_user_context_with_exception(with_user):
    user_id = with_user[0]
    assert global_user.id is None
    with pytest.raises(MKAuthException):
        with UserContext(user_id):
            assert global_user.id == user_id
            raise MKAuthException()

    assert global_user.id is None


def test_user_context_nested(with_user, with_admin):
    first_user_id = with_user[0]
    second_user_id = with_admin[0]

    assert global_user.id is None
    with UserContext(first_user_id):
        assert global_user.id == first_user_id

        with UserContext(second_user_id):
            assert global_user.id == second_user_id

        assert global_user.id == first_user_id

    assert global_user.id is None


@pytest.mark.parametrize(
    "user, alias, email, role_ids, baserole_id",
    [
        (
            LoggedInNobody(),
            "Unauthenticated user",
            "nobody",
            [],
            "guest",  # TODO: Why is this guest "guest"?
        ),
        (
            LoggedInSuperUser(),
            "Superuser for unauthenticated pages",
            "admin",
            ["admin"],
            "admin",
        ),
    ],
)
def test_unauthenticated_users(user, alias, email, role_ids, baserole_id):
    assert user.id is None
    assert user.alias == alias
    assert user.email == email
    assert user.confdir is None

    assert user.role_ids == role_ids
    assert user.get_attribute("roles") == role_ids
    assert user.baserole_id == baserole_id

    assert user.get_attribute("baz", "default") == "default"
    assert user.get_attribute("foo") is None

    assert user.customer_id is None
    assert user.contact_groups == []
    assert user.stars == set()
    assert user.is_site_disabled("any_site") is False

    assert user.load_file("any_file", "default") == "default"
    assert user.file_modified("any_file") == 0

    with pytest.raises(TypeError):
        user.save_stars()
    with pytest.raises(TypeError):
        user.save_site_config()


@pytest.mark.parametrize("user", [LoggedInNobody(), LoggedInSuperUser()])
@pytest.mark.usefixtures("request_context")
def test_unauthenticated_users_language(mocker, user):
    mocker.patch.object(active_config, "default_language", "esperanto")
    assert user.language == "esperanto"

    user.language = "sindarin"
    assert user.language == "sindarin"

    user.reset_language()
    assert user.language == "esperanto"


@pytest.mark.parametrize("user", [LoggedInNobody(), LoggedInSuperUser()])
def test_unauthenticated_users_authorized_sites(monkeypatch, user):
    assert user.authorized_sites({"site1": {},}) == {
        "site1": {},
    }

    monkeypatch.setattr("cmk.gui.site_config.allsites", lambda: {"site1": {}, "site2": {}})
    assert user.authorized_sites() == {"site1": {}, "site2": {}}


@pytest.mark.parametrize("user", [LoggedInNobody(), LoggedInSuperUser()])
def test_unauthenticated_users_authorized_login_sites(monkeypatch, user):
    monkeypatch.setattr("cmk.gui.site_config.get_login_slave_sites", lambda: ["slave_site"])
    monkeypatch.setattr(
        "cmk.gui.site_config.allsites",
        lambda: {
            "master_site": {},
            "slave_site": {},
        },
    )
    assert user.authorized_login_sites() == {"slave_site": {}}


@pytest.mark.usefixtures("request_context")
def test_logged_in_nobody_permissions(mocker):
    user = LoggedInNobody()

    mocker.patch.object(active_config, "roles", {})
    mocker.patch.object(permissions, "permission_registry")

    assert user.may("any_permission") is False
    with pytest.raises(MKAuthException):
        user.need_permission("any_permission")


@pytest.mark.usefixtures("request_context")
def test_logged_in_super_user_permissions(mocker):
    user = LoggedInSuperUser()

    mocker.patch.object(
        active_config,
        "roles",
        {
            "admin": {"permissions": {"eat_other_peoples_cake": True}},
        },
    )
    mocker.patch.object(permissions, "permission_registry")

    assert user.may("eat_other_peoples_cake") is True
    assert user.may("drink_other_peoples_milk") is False
    user.need_permission("eat_other_peoples_cake")
    with pytest.raises(MKAuthException):
        user.need_permission("drink_other_peoples_milk")


MONITORING_USER_CACHED_PROFILE = {
    "alias": "Test user",
    "authorized_sites": ["heute", "heute_slave_1"],
    "contactgroups": ["all"],
    "disable_notifications": {},
    "email": "test_user@tribe29.com",
    "fallback_contact": False,
    "force_authuser": False,
    "locked": False,
    "language": "de",
    "pager": "",
    "roles": ["user"],
    "start_url": None,
    "ui_theme": "modern-dark",
}

MONITORING_USER_SITECONFIG = {
    "heute_slave_1": {"disabled": False},
    "heute_slave_2": {"disabled": True},
}

MONITORING_USER_BUTTONCOUNTS = {
    "cb_host": 1.9024999999999999,
    "cb_hoststatus": 1.8073749999999997,
}

MONITORING_USER_FAVORITES = ["heute;CPU load"]


@pytest.fixture(name="monitoring_user")
def fixture_monitoring_user(request_context):
    """Returns a "Normal monitoring user" object."""
    user_dir = cmk.utils.paths.profile_dir / "test"
    user_dir.mkdir(parents=True)
    user_dir.joinpath("cached_profile.mk").write_text(str(MONITORING_USER_CACHED_PROFILE))
    # SITE STATUS snapin settings:
    user_dir.joinpath("siteconfig.mk").write_text(str(MONITORING_USER_SITECONFIG))
    # Ordering of the buttons:
    user_dir.joinpath("buttoncounts.mk").write_text(str(MONITORING_USER_BUTTONCOUNTS))
    # Favorites set in the commands menu:
    user_dir.joinpath("favorites.mk").write_text(str(MONITORING_USER_FAVORITES))

    assert builtin_role_ids == ["user", "admin", "guest"]
    assert "test" not in active_config.admin_users

    with create_and_destroy_user(username="test") as user:
        yield LoggedInUser(user[0])


def test_monitoring_user(monitoring_user):
    assert monitoring_user.id == "test"
    assert monitoring_user.alias == "Test user"
    assert monitoring_user.email == "test_user_test@tribe29.com"
    assert monitoring_user.confdir.endswith("/web/test")

    assert monitoring_user.role_ids == ["user"]
    assert monitoring_user.get_attribute("roles") == ["user"]
    assert monitoring_user.baserole_id == "user"

    assert monitoring_user.get_attribute("ui_theme") == "modern-dark"

    assert monitoring_user.language == "de"
    assert monitoring_user.customer_id is None
    assert monitoring_user.contact_groups == ["all"]

    assert monitoring_user.stars == set(MONITORING_USER_FAVORITES)
    monitoring_user.stars.add("heute;Memory")
    assert monitoring_user.stars == {"heute;CPU load", "heute;Memory"}
    monitoring_user.save_stars()
    assert set(monitoring_user.load_file("favorites", [])) == monitoring_user.stars

    assert monitoring_user.is_site_disabled("heute_slave_1") is False
    assert monitoring_user.is_site_disabled("heute_slave_2") is True

    assert monitoring_user.load_file("siteconfig", None) == MONITORING_USER_SITECONFIG
    assert monitoring_user.file_modified("siteconfig") > 0
    assert monitoring_user.file_modified("unknown_file") == 0

    monitoring_user.disable_site("heute_slave_1")
    monitoring_user.enable_site("heute_slave_2")
    assert monitoring_user.is_site_disabled("heute_slave_1") is True
    assert monitoring_user.is_site_disabled("heute_slave_2") is False

    assert monitoring_user.show_help is False
    monitoring_user.show_help = True
    assert monitoring_user.show_help is True

    assert monitoring_user.acknowledged_notifications == 0
    timestamp = 1578479929
    monitoring_user.acknowledged_notifications = timestamp
    assert monitoring_user.acknowledged_notifications == timestamp


def test_monitoring_user_read_broken_file(monitoring_user):
    with Path(monitoring_user.confdir, "asd.mk").open("w") as f:
        f.write("%#%#%")

    assert monitoring_user.load_file("asd", deflt="xyz") == "xyz"


def test_monitoring_user_permissions(mocker, monitoring_user):
    mocker.patch.object(
        active_config,
        "roles",
        {
            "user": {
                "permissions": {
                    "action.star": False,
                    "general.edit_views": True,
                }
            },
        },
    )
    mocker.patch.object(permissions, "permission_registry")

    assert monitoring_user.may("action.star") is False
    assert monitoring_user.may("general.edit_views") is True
    assert monitoring_user.may("unknown_permission") is False

    with pytest.raises(MKAuthException):
        monitoring_user.need_permission("action.start")
    monitoring_user.need_permission("general.edit_views")
    with pytest.raises(MKAuthException):
        monitoring_user.need_permission("unknown_permission")


@pytest.mark.parametrize(
    "varname",
    [
        "custom_checks",
        "datasource_programs",
        "agent_config:mrpe",
        "agent_config:agent_paths",
        "agent_config:runas",
        "agent_config:only_from",
    ],
)
def test_ruleset_permissions_with_commandline_access(monitoring_user, varname):
    assert may_edit_ruleset(varname) is False
