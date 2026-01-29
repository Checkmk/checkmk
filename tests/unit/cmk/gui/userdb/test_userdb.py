#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from pytest import MonkeyPatch

import cmk.ccc.version
import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.crypto import password_hashing
from cmk.crypto.password import Password
from cmk.gui import http, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.ldap_integration import ldap_connector as ldap
from cmk.gui.session import session
from cmk.gui.type_defs import (
    CustomUserAttrSpec,
    SessionInfo,
    TotpCredential,
    TwoFactorCredentials,
    UserSpec,
    WebAuthnCredential,
)
from cmk.gui.user_connection_config_types import (
    Fixed,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
)
from cmk.gui.userdb import get_user_attributes
from cmk.gui.userdb.htpasswd import hash_password
from cmk.gui.userdb.session import is_valid_user_session, load_session_infos
from cmk.gui.userdb.store import (
    load_custom_attr,
    load_user,
    save_custom_attr,
    save_two_factor_credentials,
    save_users,
)
from cmk.gui.utils.htpasswd import Htpasswd
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import Dictionary
from tests.testlib.common.repo import is_ultimatemt_repo

if TYPE_CHECKING:
    from tests.unit.cmk.web_test_app import SetConfig, SingleRequest, WebTestAppForCMK


@pytest.fixture(name="user_id")
def fixture_user_id(with_user: tuple[UserId, str]) -> UserId:
    return with_user[0]


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def single_user_session_enabled(set_config: SetConfig, user_id: UserId) -> Generator[None]:
    with set_config(single_user_session=10):
        assert active_config.single_user_session == 10
        yield


@pytest.fixture(scope="function")
def single_auth_request(wsgi_app: WebTestAppForCMK, auth_request: http.Request) -> SingleRequest:
    """Do a single authenticated request, thereby persisting the session to disk."""

    def caller(*, in_the_past: int = 0) -> tuple[UserId, SessionInfo]:
        wsgi_app.get(auth_request)
        infos = load_session_infos(session.user.ident, lock=True)

        # When `in_the_past` is a positive integer, the resulting session will have happened
        # that many seconds in the past.
        session.session_info.last_activity -= in_the_past
        session.session_info.started_at -= in_the_past

        session_id = session.session_info.session_id
        user_id = auth_request.environ["REMOTE_USER"]
        session.session_info.session_state = infos[session_id].session_state = (
            session.check_and_update_session_state()
        )
        userdb.session.save_session_infos(user_id, session_infos={session_id: session.session_info})
        assert session.user.id == user_id
        assert session.session_info.session_state == "logged_in"
        return session.user.id, infos[session_id]

    return caller


def _load_users_uncached(*, lock: bool) -> userdb.Users:
    try:
        # The magic attribute has been added by the lru_cache decorator.
        userdb.load_users.cache_clear()  # type: ignore[attr-defined]
        return userdb.load_users(lock=lock)
    finally:
        userdb.load_users.cache_clear()  # type: ignore[attr-defined]


TimedOutSession = Callable[[], tuple[UserId, SessionInfo]]


def _load_failed_logins(user_id: UserId) -> int | None:
    return load_custom_attr(user_id=user_id, key="num_failed_logins", parser=int)


def test_on_succeeded_login(single_auth_request: SingleRequest) -> None:
    assert active_config.single_user_session is None

    user_id, session_info = single_auth_request()
    session_id = session_info.session_id

    assert _load_failed_logins(user_id) == 0
    assert len(session_info.csrf_token) == 36

    # Verify the session was initialized
    session_infos = load_session_infos(user_id)
    assert session_infos == {
        session_id: SessionInfo(
            session_id=session_id,
            started_at=session_info.started_at,
            last_activity=session_info.last_activity,
            flashes=[],
            csrf_token=session_info.csrf_token,
            encrypter_secret=session_info.encrypter_secret,
            session_state="logged_in",
            auth_type="web_server",
        )
    }

    # Ensure the failed login count is 0
    assert _load_failed_logins(user_id) == 0


def test_on_failed_login_no_locking(user_id: UserId) -> None:
    now = datetime.now()
    user_attributes = get_user_attributes([])
    assert active_config.lock_on_logon_failures == 10
    assert _load_failed_logins(user_id) == 0
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=10,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 1
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=10,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 2
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=10,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 3
    assert not userdb.user_locked(user_id, load_user(user_id))


def test_on_failed_login_count_reset_on_succeeded_login(user_id: UserId) -> None:
    now = datetime.now()
    user_attributes = get_user_attributes(active_config.wato_user_attrs)
    assert active_config.lock_on_logon_failures == 10
    assert _load_failed_logins(user_id) == 0
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=10,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 1
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.session.on_succeeded_login(user_id, now)
    assert _load_failed_logins(user_id) == 0
    assert not userdb.user_locked(user_id, load_user(user_id))


def test_on_failed_login_with_locking(user_id: UserId) -> None:
    now = datetime.now()
    user_attributes = get_user_attributes([])
    assert _load_failed_logins(user_id) == 0
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=3,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 1
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=3,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 2
    assert not userdb.user_locked(user_id, load_user(user_id))

    userdb.on_failed_login(
        user_id,
        user_attributes,
        now=now,
        lock_on_logon_failures=3,
        log_logon_failures=True,
    )
    assert _load_failed_logins(user_id) == 3
    assert userdb.user_locked(user_id, load_user(user_id))


def test_on_logout_no_session(
    wsgi_app: WebTestAppForCMK, auth_request: http.Request, with_user: tuple[UserId, str]
) -> None:
    # login using user
    wsgi_app.login(*with_user)
    wsgi_app.get(auth_request)

    user_id = session.user.ident
    old_session = session.session_info
    session_id = old_session.session_id

    # logout
    old_session.logout()
    userdb.session.save_session_infos(user_id, {session_id: old_session})

    # Make another request to update "last_activity"
    wsgi_app.get(auth_request)
    # import time

    # time.sleep(2)
    # print("slept 2", datetime.now().timestamp())

    assert session.session_info.session_id != old_session.session_id
    assert session.session_info.started_at >= old_session.started_at
    #        assert session.session_info.last_activity == int(datetime.now().timestamp())
    assert session.session_info.last_activity >= old_session.last_activity


def test_on_logout_invalidate_session(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    assert session_info.session_id in load_session_infos(user_id)

    session_info.logout()
    userdb.session.save_session_infos(user_id, {session_info.session_id: session_info})

    assert (
        load_session_infos(user_id)[session_info.session_id].session_state == "credentials_needed"
    )


def test_access_denied_with_invalidated_session(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session_id = session_info.session_id

    assert session_id in load_session_infos(user_id)
    assert is_valid_user_session(user_id, load_session_infos(user_id), session_id)
    session.logout()
    userdb.session.save_session_infos(user_id, {session_id: session.session_info})

    assert (
        load_session_infos(user_id)[session_info.session_id].session_state == "credentials_needed"
    )
    assert not is_valid_user_session(user_id, load_session_infos(user_id), session_id)


def test_invalid_field_in_session_info_ignored(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session_id = session_info.session_id

    assert "two_factor_complete" not in load_session_infos(user_id)

    old_session_info = asdict(load_session_infos(user_id)[session_id])
    old_session_info["two_factor_complete"] = False

    assert "two_factor_complete" in old_session_info

    # Not using userdb.session.save_session_infos to force "two_factor_complete" into the data
    save_custom_attr(
        user_id,
        "session_info",
        repr({session_id: old_session_info}),
    )

    manipulated_session_info = load_custom_attr(user_id=user_id, key="session_info", parser=str)
    assert manipulated_session_info is not None
    assert "two_factor_complete" in manipulated_session_info
    assert "two_factor_complete" not in load_session_infos(user_id)


def test_on_access_update_valid_session(
    wsgi_app: WebTestAppForCMK,
    auth_request: http.Request,
) -> None:
    """Test that accessing with a valid session updates last_activity."""
    wsgi_app.get(auth_request)

    # We push the access further in the past to see if its updated on the next request.
    session.session_info.last_activity -= 3600
    session.persist()

    old_session_info = session.session_info

    assert session.session_info.session_id == old_session_info.session_id

    wsgi_app.get(auth_request)

    assert session.session_info.session_id == old_session_info.session_id
    assert session.session_info.started_at == old_session_info.started_at
    assert session.session_info.last_activity > old_session_info.last_activity


def test_timed_out_session_gets_a_new_one_instead(
    wsgi_app: WebTestAppForCMK, auth_request: http.Request, with_user: tuple[UserId, str]
) -> None:
    # login user
    wsgi_app.login(*with_user)

    user_id = session.user.ident
    session_id = session.session_info.session_id

    # Make the session older than it actually was
    # user is logged out.
    old_session = session.session_info
    old_session.started_at -= 3600 * 2
    old_session.last_activity -= 3600 * 2
    userdb.session.save_session_infos(user_id, {session_id: old_session})

    # Make another request to update "last_activity"
    wsgi_app.get(auth_request)

    # A new session is created, because the old one expired.
    assert session.session_info.session_id != old_session.session_id
    assert session.session_info.started_at != old_session.started_at
    assert session.session_info.last_activity > old_session.last_activity


@pytest.mark.usefixtures("single_user_session_enabled")
def test_update_unknown_session(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session_valid = session_info.session_id
    session_info = load_session_infos(user_id)[session_valid]
    session_info.started_at = 10
    assert not is_valid_user_session(user_id, load_session_infos(user_id), "xyz")


def test_logout_on_idle_timeout(single_auth_request: SingleRequest, set_config: SetConfig) -> None:
    user_id, session_info = single_auth_request()
    session.initialize(
        user_id,
        auth_type="web_server",
        user_permissions=UserPermissions({}, {}, {}, []),
        secure_flag=False,
    )
    now = datetime.now()
    session.session_info = session_info
    session.session_info.last_activity = int(datetime.now().timestamp()) - 5401
    assert session.is_expired(now)


def test_logout_on_maximum_session_reached(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session.initialize(
        user_id,
        auth_type="web_server",
        user_permissions=UserPermissions({}, {}, {}, []),
        secure_flag=False,
    )
    now = datetime.now()
    session.session_info = session_info
    session.session_info.started_at = int(datetime.now().timestamp()) - 86401
    assert session.is_expired(now)


@pytest.mark.usefixtures("single_user_session_enabled")
def test_on_succeeded_login_already_existing_session(single_auth_request: SingleRequest) -> None:
    user_id, _session_info = single_auth_request()
    now = datetime.now()
    with pytest.raises(MKUserError, match="Another session"):
        userdb.session.on_succeeded_login(user_id, now)


def test_is_valid_user_session_single_user_session_disabled(user_id: UserId) -> None:
    assert active_config.single_user_session is None
    assert not is_valid_user_session(user_id, load_session_infos(user_id), "session1")


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_not_existing(user_id: UserId) -> None:
    assert not is_valid_user_session(user_id, load_session_infos(user_id), "not-existing-session")


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_still_valid_when_last_activity_extends_timeout(
    single_auth_request: SingleRequest,
) -> None:
    user_id, session_info = single_auth_request()

    # Time out session
    session_info.started_at -= 3600 * 2
    session_info.last_activity -= 3600 * 2
    userdb.session.save_session_infos(user_id, {session_info.session_id: session_info})

    session_timed_out = session_info.session_id

    assert is_valid_user_session(user_id, load_session_infos(user_id), session_timed_out)


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_valid(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session_valid = session_info.session_id
    assert is_valid_user_session(user_id, load_session_infos(user_id), session_valid)


def test_ensure_user_can_init_no_single_user_session(user_id: UserId) -> None:
    assert active_config.single_user_session is None
    userdb.session.ensure_user_can_init_session(user_id, datetime.now())


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_no_previous_session(user_id: UserId) -> None:
    userdb.session.ensure_user_can_init_session(user_id, datetime.now())


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_with_previous_session_timeout(user_id: UserId) -> None:
    userdb.session.ensure_user_can_init_session(user_id, datetime.now())


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_with_previous_invalidated_session(user_id: UserId) -> None:
    session.initialize(
        user_id,
        auth_type="web_server",
        user_permissions=UserPermissions({}, {}, {}, []),
        secure_flag=False,
    )
    session.logout()
    userdb.session.save_session_infos(
        user_id, {session.session_info.session_id: session.session_info}
    )

    userdb.session.ensure_user_can_init_session(user_id, datetime.now())


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_not_init_with_previous_session(single_auth_request: SingleRequest) -> None:
    now = datetime.now()
    user_id, _session_info = single_auth_request()
    with pytest.raises(MKUserError, match="Another session"):
        userdb.session.ensure_user_can_init_session(user_id, now)


def test_active_sessions_no_existing() -> None:
    assert userdb.session.active_sessions({}, datetime.now()) == {}


def test_active_sessions_remove_outdated() -> None:
    now = datetime.now()
    assert list(
        userdb.session.active_sessions(
            {
                "outdated": SessionInfo(
                    session_id="outdated",
                    started_at=int(now.timestamp()) - (86400 * 10),
                    last_activity=int(now.timestamp()) - (86400 * 8),
                    flashes=[],
                ),
                "keep": SessionInfo(
                    session_id="keep",
                    started_at=int(now.timestamp()) - (86400 * 10),
                    last_activity=int(now.timestamp()) - (86400 * 5),
                    flashes=[],
                ),
            },
            now,
        ).keys()
    ) == ["keep"]


def test_active_sessions_too_many() -> None:
    now = datetime.now()
    sessions = {
        f"keep_{num}": SessionInfo(
            session_id=f"keep_{num}",
            started_at=int(now.timestamp()) - (86400 * 10),
            last_activity=int(now.timestamp()) - (86400 * 5) + num,
            flashes=[],
        )
        for num in range(21)
    }

    assert sorted(
        [
            "keep_1",
            "keep_2",
            "keep_3",
            "keep_4",
            "keep_5",
            "keep_6",
            "keep_7",
            "keep_8",
            "keep_9",
            "keep_10",
            "keep_11",
            "keep_12",
            "keep_13",
            "keep_14",
            "keep_15",
            "keep_16",
            "keep_17",
            "keep_18",
            "keep_19",
            "keep_20",
        ]
    ) == sorted(userdb.session.active_sessions(sessions, now).keys())


def test_create_session_id_is_correct_type() -> None:
    id1 = userdb.session.create_session_id()
    assert isinstance(id1, str)


def test_create_session_id_changes() -> None:
    assert userdb.session.create_session_id() != userdb.session.create_session_id()


def test_invalidate_session(single_auth_request: SingleRequest) -> None:
    user_id, session_info = single_auth_request()
    session_id = session_info.session_id
    assert session_id in load_session_infos(user_id)
    session_info.logout()
    userdb.session.save_session_infos(user_id, {session_id: session_info})
    assert (
        load_session_infos(user_id)[session_info.session_id].session_state == "credentials_needed"
    )


def test_get_last_activity(single_auth_request: SingleRequest) -> None:
    user_id, _session_info = single_auth_request(in_the_past=0)
    now = datetime.now()

    user = _load_users_uncached(lock=False)[user_id]
    assert userdb.get_last_activity(user) <= int(now.timestamp())
    assert "session_info" in user


def test_user_attribute_sync_plugins() -> None:
    attrs = [
        CustomUserAttrSpec(
            {
                "add_custom_macro": False,
                "help": "VIP attribute",
                "name": "vip",
                "show_in_table": False,
                "title": "VIP",
                "topic": "ident",
                "type": "TextAscii",
                "user_editable": True,
            }
        )
    ]

    connection = ldap.LDAPUserConnector(
        LDAPUserConnectionConfig(
            id="ldp",
            description="",
            comment="",
            docu_url="",
            disabled=False,
            directory_type=(
                "ad",
                LDAPConnectionConfigFixed(
                    connect_to=(
                        "fixed_list",
                        Fixed(server="127.0.0.1"),
                    )
                ),
            ),
            bind=(
                "CN=svc_checkmk,OU=checkmktest-users,DC=int,DC=testdomain,DC=com",
                ("store", "AD_svc_checkmk"),
            ),
            port=636,
            use_ssl=True,
            user_dn="OU=checkmktest-users,DC=int,DC=testdomain,DC=com",
            user_scope="sub",
            user_filter="(&(objectclass=user)(objectcategory=person)(|(memberof=CN=cmk_AD_admins,OU=checkmktest-groups,DC=int,DC=testdomain,DC=com)))",
            user_id_umlauts="keep",
            group_dn="OU=checkmktest-groups,DC=int,DC=testdomain,DC=com",
            group_scope="sub",
            active_plugins={
                "alias": {},
                "auth_expire": {},
                "groups_to_contactgroups": {"nested": True},
                "disable_notifications": {"attr": "msDS-cloudExtensionAttribute1"},
                "email": {"attr": "mail"},
                "icons_per_item": {"attr": "msDS-cloudExtensionAttribute3"},
                "nav_hide_icons_title": {"attr": "msDS-cloudExtensionAttribute4"},
                "pager": {"attr": "mobile"},
                "groups_to_roles": {
                    "admin": [
                        (
                            "CN=cmk_AD_admins,OU=checkmktest-groups,DC=int,DC=testdomain,DC=com",
                            None,
                        )
                    ]
                },
                "show_mode": {"attr": "msDS-cloudExtensionAttribute2"},
                "ui_sidebar_position": {"attr": "msDS-cloudExtensionAttribute5"},
                "start_url": {"attr": "msDS-cloudExtensionAttribute9"},
                "temperature_unit": {"attr": "msDS-cloudExtensionAttribute6"},
                "ui_theme": {"attr": "msDS-cloudExtensionAttribute7"},
                "force_authuser": {"attr": "msDS-cloudExtensionAttribute8"},
            },
            cache_livetime=300,
            type="ldap",
        )
    )

    user_attributes = get_user_attributes(attrs)
    plugins = dict(ldap.all_attribute_plugins(user_attributes))
    ldap_plugin = plugins["vip"]
    assert ldap_plugin.title == "VIP"
    assert ldap_plugin.help == "VIP attribute"
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert isinstance(ldap_plugin.parameters(connection), Dictionary)

    assert "vip" in dict(ldap.ldap_attribute_plugins_elements(connection, user_attributes)).keys()


def test_check_credentials_local_user(with_user: tuple[UserId, str]) -> None:
    username, password = with_user
    assert (
        userdb.check_credentials(
            username,
            Password(password),
            get_user_attributes([]),
            datetime.now(),
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        == username
    )


@pytest.mark.usefixtures("request_context")
def test_check_credentials_local_user_create_htpasswd_user_ad_hoc() -> None:
    user_id = UserId("someuser")
    assert not userdb.user_exists(user_id)
    assert not userdb.user_exists_according_to_profile(user_id)
    assert user_id not in _load_users_uncached(lock=False)

    Htpasswd(cmk.utils.paths.htpasswd_file).save_all({user_id: hash_password(Password("cmk"))})
    # Once a user exists in the htpasswd, the GUI treats the user as existing user and will
    # automatically initialize the missing data structures
    assert userdb.user_exists(user_id)
    assert not userdb.user_exists_according_to_profile(user_id)
    assert user_id in _load_users_uncached(lock=False)

    assert (
        userdb.check_credentials(
            user_id,
            Password("cmk"),
            get_user_attributes([]),
            datetime.now(),
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        == user_id
    )

    # Nothing changes during regular access
    assert userdb.user_exists(user_id)
    assert not userdb.user_exists_according_to_profile(user_id)
    assert user_id in _load_users_uncached(lock=False)


def test_check_credentials_local_user_disallow_locked(with_user: tuple[UserId, str]) -> None:
    now = datetime.now()
    user_id, password = with_user
    user_attributes = get_user_attributes([])
    assert (
        userdb.check_credentials(
            user_id,
            Password(password),
            user_attributes,
            now,
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        == user_id
    )

    users = _load_users_uncached(lock=True)

    users[user_id]["locked"] = True
    save_users(
        users,
        user_attributes,
        user_connections=[],
        now=now,
        pprint_value=True,
        call_users_saved_hook=False,
    )

    with pytest.raises(MKUserError, match="User is locked"):
        userdb.check_credentials(
            user_id,
            Password(password),
            user_attributes,
            now,
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def make_cme(monkeypatch: MonkeyPatch, user_id: UserId, set_config: SetConfig) -> Generator[None]:
    monkeypatch.setattr(cmk.ccc.version, "omd_version", lambda: "2.0.0i1.cme")
    assert cmk.ccc.version.edition(cmk.utils.paths.omd_root) is cmk.ccc.version.Edition.ULTIMATEMT

    with set_config(current_customer="test-customer"):
        # Fix CRE mypy tests that do not have this attribute defined
        assert active_config.current_customer == "test-customer"
        yield


@pytest.mark.skipif(not is_ultimatemt_repo(), reason="managed-edition-only test")
@pytest.mark.usefixtures("make_cme")
def test_check_credentials_managed_global_user_is_allowed(with_user: tuple[UserId, str]) -> None:
    user_id, password = with_user
    now = datetime.now()
    from cmk.gui.nonfree.ultimatemt import managed  # type: ignore[import-untyped, unused-ignore]

    users = _load_users_uncached(lock=True)
    users[user_id]["customer"] = managed.SCOPE_GLOBAL
    save_users(
        users,
        (user_attributes := get_user_attributes([])),
        user_connections=[],
        now=now,
        pprint_value=True,
        call_users_saved_hook=False,
    )
    assert (
        userdb.check_credentials(
            user_id,
            Password(password),
            user_attributes,
            now,
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        == user_id
    )


@pytest.mark.skipif(not is_ultimatemt_repo(), reason="managed-edition-only test")
@pytest.mark.usefixtures("make_cme")
def test_check_credentials_managed_customer_user_is_allowed(with_user: tuple[UserId, str]) -> None:
    user_id, password = with_user
    now = datetime.now()
    users = _load_users_uncached(lock=True)
    users[user_id]["customer"] = "test-customer"
    save_users(
        users,
        (user_attributes := get_user_attributes([])),
        user_connections=[],
        now=now,
        pprint_value=True,
        call_users_saved_hook=False,
    )
    assert (
        userdb.check_credentials(
            user_id,
            Password(password),
            user_attributes,
            now,
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        == user_id
    )


@pytest.mark.skipif(not is_ultimatemt_repo(), reason="managed-edition-only test")
@pytest.mark.usefixtures("make_cme")
def test_check_credentials_managed_wrong_customer_user_is_denied(
    with_user: tuple[UserId, str],
) -> None:
    user_id, password = with_user
    now = datetime.now()
    users = _load_users_uncached(lock=True)
    users[user_id]["customer"] = "wrong-customer"
    save_users(
        users,
        (user_attributes := get_user_attributes([])),
        user_connections=[],
        now=now,
        pprint_value=True,
        call_users_saved_hook=False,
    )
    assert (
        userdb.check_credentials(
            user_id,
            Password(password),
            user_attributes,
            now,
            UserSpec(
                contactgroups=[],
                roles=["user"],
                force_authuser=False,
            ),
        )
        is False
    )


def test_load_custom_attr_not_existing(user_id: UserId) -> None:
    assert userdb.load_custom_attr(user_id=user_id, key="a", parser=str) is None


def test_load_custom_attr_not_existing_with_default(user_id: UserId) -> None:
    assert userdb.load_custom_attr(user_id=user_id, key="a", parser=str) is None


def test_load_custom_attr_from_file(user_id: UserId) -> None:
    with userdb.custom_attr_path(user_id, "a").open("w") as f:
        f.write("xyz\n")
    assert userdb.load_custom_attr(user_id=user_id, key="a", parser=str) == "xyz"


def test_load_custom_attr_convert(user_id: UserId) -> None:
    with userdb.custom_attr_path(user_id, "a").open("w") as f:
        f.write("xyz\n")
    assert (
        userdb.load_custom_attr(
            user_id=user_id, key="a", parser=lambda x: "a" if x == "xyz" else "b"
        )
        == "a"
    )


def test_load_two_factor_credentials_unset(user_id: UserId) -> None:
    assert userdb.load_two_factor_credentials(user_id) == {
        "webauthn_credentials": {},
        "backup_codes": [],
        "totp_credentials": {},
    }


def test_save_two_factor_credentials(user_id: UserId) -> None:
    credentials = TwoFactorCredentials(
        {
            "webauthn_credentials": {
                "id": WebAuthnCredential(
                    credential_id="id",
                    registered_at=1337,
                    alias="Steckding",
                    credential_data=b"whatever",
                ),
            },
            "backup_codes": [
                password_hashing.PasswordHash("asdr2ar2a2ra2rara2"),
                password_hashing.PasswordHash("dddddddddddddddddd"),
            ],
            "totp_credentials": {
                "uuid": TotpCredential(
                    {
                        "credential_id": "uuid",
                        "secret": b"whatever",
                        "version": 1,
                        "registered_at": 1337,
                        "alias": "Steckding",
                    }
                ),
            },
        }
    )
    save_two_factor_credentials(user_id, credentials)
    assert userdb.load_two_factor_credentials(user_id) == credentials


def test_disable_web_authentication(user_id: UserId) -> None:
    credentials = TwoFactorCredentials(
        {
            "webauthn_credentials": {
                "id": WebAuthnCredential(
                    {
                        "credential_id": "id",
                        "registered_at": 1337,
                        "alias": "Steckding",
                        "credential_data": b"whatever",
                    }
                ),
            },
            "backup_codes": [],
            "totp_credentials": {
                "uuid": TotpCredential(
                    {
                        "credential_id": "uuid",
                        "secret": b"whatever",
                        "version": 1,
                        "registered_at": 1337,
                        "alias": "Steckding",
                    }
                ),
            },
        }
    )
    save_two_factor_credentials(user_id, credentials)

    assert userdb.is_two_factor_login_enabled(user_id)
    userdb.disable_two_factor_authentication(user_id)
    assert not userdb.is_two_factor_login_enabled(user_id)


def test_make_two_factor_backup_codes(user_id: UserId) -> None:
    codes = userdb.make_two_factor_backup_codes()
    assert len(codes) == 10
    for password, pwhashed in codes:
        password_hashing.verify(password, pwhashed)


def test_is_two_factor_backup_code_valid_no_codes(user_id: UserId) -> None:
    assert not userdb.is_two_factor_backup_code_valid(user_id, Password("yxz"))


def test_is_two_factor_backup_code_valid_matches(user_id: UserId) -> None:
    codes = userdb.make_two_factor_backup_codes()
    credentials = userdb.load_two_factor_credentials(user_id)
    credentials["backup_codes"] = [pwhashed for _password, pwhashed in codes]
    save_two_factor_credentials(user_id, credentials)
    assert len(credentials["backup_codes"]) == 10

    valid = userdb.is_two_factor_backup_code_valid(user_id, codes[3][0])
    assert valid

    credentials = userdb.load_two_factor_credentials(user_id)
    assert len(credentials["backup_codes"]) == 9
