#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.users import create_and_destroy_user

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui import permissions
from cmk.gui.config import (
    active_config,
    builtin_role_ids,
    default_authorized_builtin_role_ids,
    default_unauthorized_builtin_role_ids,
)
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, LoggedInUser
from cmk.gui.logged_in import user as global_user
from cmk.gui.session import SuperUserContext, UserContext
from cmk.gui.watolib.rulesets import may_edit_ruleset


def test_user_context(with_user: tuple[UserId, str]) -> None:
    user_id = with_user[0]
    assert global_user.id is None
    with UserContext(user_id):
        assert global_user.id == user_id
    assert global_user.id is None


@pytest.mark.usefixtures("request_context")
def test_super_user_context() -> None:
    assert global_user.id is None
    with SuperUserContext():
        assert global_user.role_ids == ["admin"]
    assert global_user.id is None


def test_user_context_with_exception(with_user: tuple[UserId, str]) -> None:
    user_id = with_user[0]
    assert global_user.id is None
    with pytest.raises(MKAuthException):
        with UserContext(user_id):
            assert global_user.id == user_id
            raise MKAuthException()

    assert global_user.id is None


def test_user_context_nested(with_user: tuple[UserId, str], with_admin: tuple[UserId, str]) -> None:
    first_user_id = with_user[0]
    second_user_id = with_admin[0]

    assert global_user.id is None
    with UserContext(first_user_id):
        assert global_user.id == first_user_id

        with UserContext(second_user_id):
            assert global_user.id == second_user_id

        assert global_user.id == first_user_id

    assert global_user.id is None


def test_user_context_explicit_permissions(with_user: tuple[UserId, str]) -> None:
    assert not global_user.may("some_permission")
    with UserContext(
        with_user[0],
        explicit_permissions={"some_permission", "some_other_permission"},
    ):
        assert global_user.may("some_permission")
    assert not global_user.may("some_permission")


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
            "Superuser for internal use",
            "admin",
            ["admin"],
            "admin",
        ),
    ],
)
def test_unauthenticated_users(
    user: LoggedInUser, alias: str, email: str, role_ids: Sequence[str], baserole_id: str
) -> None:
    assert user.id is None
    assert user.alias == alias
    assert user.email == email
    assert user.confdir is None

    assert user.role_ids == role_ids
    assert user.get_attribute("roles") == role_ids

    assert user.get_attribute("baz", "default") == "default"
    assert user.get_attribute("foo") is None

    assert user.customer_id is None
    assert user.contact_groups == []
    assert user.stars == set()
    assert user.is_site_disabled(SiteId("any_site")) is False

    assert user.load_file("unittest", "default") == "default"
    assert user.file_modified("any_file") == 0

    with pytest.raises(TypeError):
        user.save_stars()
    with pytest.raises(TypeError):
        user.save_site_config()


@pytest.mark.parametrize("user", [LoggedInNobody(), LoggedInSuperUser()])
@pytest.mark.usefixtures("request_context")
def test_unauthenticated_users_language(monkeypatch: MonkeyPatch, user: LoggedInUser) -> None:
    with monkeypatch.context() as m:
        m.setattr(active_config, "default_language", "esperanto")
        assert user.language == "esperanto"

        user.language = "sindarin"
        assert user.language == "sindarin"

        user.reset_language()
        assert user.language == "esperanto"


@pytest.mark.parametrize("user", [LoggedInNobody(), LoggedInSuperUser()])
def test_unauthenticated_users_authorized_sites(
    monkeypatch: MonkeyPatch, user: LoggedInUser
) -> None:
    assert user.authorized_sites(
        SiteConfigurations(
            {
                SiteId("site1"): (
                    site1_config := SiteConfiguration(
                        {
                            "id": SiteId("site1"),
                            "alias": "Local site site1",
                            "socket": ("local", None),
                            "disable_wato": True,
                            "disabled": False,
                            "insecure": False,
                            "url_prefix": "/site1/",
                            "multisiteurl": "",
                            "persist": False,
                            "replicate_ec": False,
                            "replicate_mkps": False,
                            "replication": None,
                            "timeout": 5,
                            "user_login": True,
                            "proxy": None,
                            "user_sync": "all",
                            "status_host": None,
                            "message_broker_port": 5672,
                        }
                    )
                ),
            }
        )
    ) == {
        "site1": {
            "id": SiteId("site1"),
            "alias": "Local site site1",
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": "/site1/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": None,
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
        },
    }
    site2_config = SiteConfiguration(
        {
            "id": SiteId("site2"),
            "alias": "Local site site2",
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": "/site2/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": None,
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
        }
    )

    monkeypatch.setattr(
        "cmk.gui.site_config.enabled_sites",
        lambda: {
            "site1": site1_config,
            "site2": site2_config,
        },
    )
    assert user.authorized_sites() == {
        "site1": site1_config,
        "site2": site2_config,
    }


@pytest.mark.usefixtures("request_context")
def test_logged_in_nobody_permissions(mocker: MockerFixture, monkeypatch: MonkeyPatch) -> None:
    user = LoggedInNobody()
    mocker.patch.object(permissions, "permission_registry")
    with monkeypatch.context() as m:
        m.setattr(active_config, "roles", {})

        assert user.may("any_permission") is False
        with pytest.raises(MKAuthException):
            user.need_permission("any_permission")


@pytest.mark.usefixtures("request_context")
def test_logged_in_super_user_permissions(mocker: MockerFixture, monkeypatch: MonkeyPatch) -> None:
    user = LoggedInSuperUser()
    mocker.patch.object(permissions, "permission_registry")
    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "roles",
            {
                "admin": {"permissions": {"eat_other_peoples_cake": True}},
            },
        )

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
    "email": "test_user@checkmk.com",
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
def fixture_monitoring_user() -> Iterator[LoggedInUser]:
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

    assert default_authorized_builtin_role_ids == ["user", "admin", "guest"]
    assert default_unauthorized_builtin_role_ids == ["agent_registration", "no_permissions"]
    assert builtin_role_ids == ["user", "admin", "guest", "agent_registration", "no_permissions"]
    assert "test" not in active_config.admin_users

    with create_and_destroy_user(username="test") as user:
        yield LoggedInUser(user[0])


def test_monitoring_user(request_context: None, monitoring_user: LoggedInUser) -> None:
    assert monitoring_user.id == "test"
    assert monitoring_user.alias == "Test user"
    assert monitoring_user.email == "test_user_test@checkmk.com"
    assert monitoring_user.confdir
    assert str(monitoring_user.confdir).endswith("/web/test")

    assert monitoring_user.role_ids == ["user"]
    assert monitoring_user.get_attribute("roles") == ["user"]

    assert monitoring_user.get_attribute("ui_theme") == "modern-dark"

    assert monitoring_user.language == "de"
    assert monitoring_user.customer_id is None
    assert monitoring_user.contact_groups == ["all"]

    assert monitoring_user.stars == set(MONITORING_USER_FAVORITES)
    monitoring_user.stars.add("heute;Memory")
    assert monitoring_user.stars == {"heute;CPU load", "heute;Memory"}
    monitoring_user.save_stars()
    assert set(monitoring_user.load_file("favorites", [])) == monitoring_user.stars

    assert monitoring_user.is_site_disabled(SiteId("heute_slave_1")) is False
    assert monitoring_user.is_site_disabled(SiteId("heute_slave_2")) is True

    assert monitoring_user.load_file("siteconfig", None) == MONITORING_USER_SITECONFIG
    assert monitoring_user.file_modified("siteconfig") > 0
    assert monitoring_user.file_modified("unknown_file") == 0

    monitoring_user.disable_site(SiteId("heute_slave_1"))
    monitoring_user.enable_site(SiteId("heute_slave_2"))
    assert monitoring_user.is_site_disabled(SiteId("heute_slave_1")) is True
    assert monitoring_user.is_site_disabled(SiteId("heute_slave_2")) is False

    assert monitoring_user.inline_help_as_text is False
    monitoring_user.inline_help_as_text = True
    assert monitoring_user.inline_help_as_text is True

    assert monitoring_user.acknowledged_notifications == 0
    timestamp = 1578479929
    monitoring_user.acknowledged_notifications = timestamp
    assert monitoring_user.acknowledged_notifications == timestamp


def test_monitoring_user_read_broken_file(
    request_context: None, monitoring_user: LoggedInUser
) -> None:
    assert monitoring_user.confdir
    with Path(monitoring_user.confdir, "unittest.mk").open("w") as f:
        f.write("%#%#%")

    assert monitoring_user.load_file("unittest", deflt="xyz") == "xyz"


def test_monitoring_user_permissions(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    request_context: None,
    monitoring_user: LoggedInUser,
) -> None:
    mocker.patch.object(permissions, "permission_registry")
    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "roles",
            {
                # The admin permissions are needed, otherwise the teardown code would not run due to
                # missing permissions.
                "admin": {
                    "permissions": {
                        "wato.users": True,
                        "wato.edit": True,
                    },
                },
                "user": {
                    "permissions": {
                        "action.star": False,
                        "general.edit_views": True,
                    }
                },
            },
        )

        assert monitoring_user.may("action.star") is False
        assert monitoring_user.may("general.edit_views") is True
        assert monitoring_user.may("unknown_permission") is False

        with pytest.raises(MKAuthException):
            monitoring_user.need_permission("action.start")
        monitoring_user.need_permission("general.edit_views")
        with pytest.raises(MKAuthException):
            monitoring_user.need_permission("unknown_permission")


@pytest.mark.usefixtures("request_context", "monitoring_user")
@pytest.mark.parametrize(
    "varname",
    [
        "custom_checks",
        "datasource_programs",
        RuleGroup.AgentConfig("mrpe"),
        RuleGroup.AgentConfig("agent_paths"),
        RuleGroup.AgentConfig("runas"),
        RuleGroup.AgentConfig("only_from"),
    ],
)
def test_ruleset_permissions_with_commandline_access(varname: str) -> None:
    assert may_edit_ruleset(varname) is False
