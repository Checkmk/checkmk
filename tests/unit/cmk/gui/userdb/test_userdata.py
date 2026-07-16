#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.events.notify_types import EventRule
from cmk.gui.type_defs import LastLoginInfo, SessionInfo, TwoFactorCredentials, UserSpec
from cmk.gui.userdb import get_user_attributes, UserAttribute
from cmk.gui.userdb.store import load_users, save_users
from cmk.gui.userdb.user_attributes import ForceAuthUserUserAttribute
from cmk.gui.userdb.userdata import UserData, UserDataDiff, UserDB, UserNotFoundError


def _fully_populated_userspec(user_id: UserId) -> UserSpec:
    """A UserSpec with every field that UserData knows how to represent set to a non-default value."""
    return UserSpec(
        {
            # fields that to_userspec() always writes
            "alias": "Happy Testuser",
            "contactgroups": ["cg1", "cg2"],
            "enforce_pw_change": True,
            "fallback_contact": True,
            "is_automation_user": False,
            "locked": False,
            "num_failed_logins": 3,
            "pager": "555-1234",
            "roles": ["admin", "user"],
            "serial": 7,
            "session_info": {},
            "store_automation_secret": False,
            "user_id": user_id,
            "user_scheme_serial": 2,
            # fields written only when not None
            "automation_secret": "supersecret42",
            "connector": "htpasswd",
            "password": PasswordHash("$2y$04$abcdefghijklmnopqrstuv"),
            "email": "happy@example.com",
            "language": "de",
            "ldap_pw_last_changed": "2024-01-01T00:00:00",
            "two_factor_credentials": TwoFactorCredentials(
                webauthn_credentials={},
                backup_codes=[],
                totp_credentials={},
            ),
            "host_notification_options": "durfs",
            "notification_period": "24X7",
            "service_notification_options": "wucr",
            "notifications_enabled": True,
            "notification_method": "email",
            "last_login": LastLoginInfo(timestamp=1700000000),
            "temperature_unit": "celsius",
            "ui_sidebar_position": "left",
            "navbar_changes_action": "slideout",
            "ui_theme": "modern-dark",
            "start_url": "/dashboard.py",
            "idle_timeout": 3600,
            "created_on_version": "2.4.0",
            # written only when the list is non-empty
            "notification_rules": [cast(EventRule, {"description": "rule1"})],
            # fields written unless their "key absent" sentinel applies
            "customer": "customer1",
            "disable_notifications": {"disabled": True},
            "force_authuser": True,
            "last_pw_change": 1699999999,
            "show_mode": "default_show_less",
            "nav_hide_icons_title": "hide",
            "icons_per_item": "entry",
            # value-transformed field
            "authorized_sites": [SiteId("site1"), SiteId("site2")],
        }
    )


def test_from_userspec_to_userspec_roundtrip_preserves_all_modelled_fields() -> None:
    user_id = UserId("happy")
    original = _fully_populated_userspec(user_id)

    roundtripped = UserData.from_userspec(user_id, original, []).to_userspec()

    assert roundtripped == original


def _user(
    spec: Mapping[str, object],
    user_attributes: Sequence[tuple[str, UserAttribute]] = (),
) -> UserData:
    return UserData.from_userspec(
        UserId("happy"),
        cast(UserSpec, {"alias": "Happy Testuser", "roles": []} | dict(spec)),
        user_attributes,
    )


def test_diff_reports_only_changed_fields() -> None:
    before = _user({})
    after = _user({"email": "happy@example.com", "force_authuser": False})

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == (
        'Value of "email" changed from None to "happy@example.com".\n'
        'Attribute "force_authuser" with value False added.'
    )


def test_diff_reports_changed_secrets_without_revealing_them() -> None:
    before = _user({"password": PasswordHash("$2y$04$oldhash")})
    after = _user(
        {
            "password": PasswordHash("$2y$04$newhash"),
            "automation_secret": "automation-secret",
            "two_factor_credentials": TwoFactorCredentials(
                webauthn_credentials={},
                backup_codes=[PasswordHash("$2y$04$backupcode")],
                totp_credentials={},
            ),
        }
    )

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == ""
    assert diff.credentials_changed


def test_diff_ignores_internal_state() -> None:
    session = {"session": SessionInfo(session_id="session", started_at=0, last_activity=0)}
    before = _user({"session_info": session, "user_scheme_serial": 0})
    after = _user({"user_scheme_serial": 1})

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == ""
    assert not diff.credentials_changed


def test_diff_reports_builtin_attribute_once() -> None:
    # force_authuser is both an explicit UserData field and a registered user attribute
    attrs = [("force_authuser", ForceAuthUserUserAttribute())]
    before = _user({}, attrs)
    after = _user({"force_authuser": False}, attrs)

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == 'Attribute "force_authuser" with value False added.'


# --- UserDB CRUD (persisted; needs the user store) ----------------------------------------------


def _seed_users(specs: dict[UserId, UserSpec]) -> None:
    """Write the given users into the store, preserving any users already present."""
    save_users(
        profiles={**load_users(lock=True), **specs},
        user_attributes=get_user_attributes([]),
        user_connections=[],
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
    )


def _user_db() -> UserDB:
    return UserDB(get_user_attributes([]), [], pprint_value=False)


@pytest.mark.usefixtures("request_context")
def test_get_user_for_editing_persists_mutations() -> None:
    user_id = UserId("happy")
    _seed_users({user_id: UserSpec({"alias": "Happy Testuser", "roles": []})})

    with _user_db().get_user_for_editing(user_id) as user_data:
        user_data.email = "happy@example.com"
        user_data.pager = "555-1234"

    reloaded = load_users()[user_id]
    assert reloaded["email"] == "happy@example.com"
    assert reloaded["pager"] == "555-1234"


@pytest.mark.usefixtures("request_context")
def test_delete_users_returns_the_deleted_users() -> None:
    drop = UserId("drop")
    _seed_users({drop: UserSpec({"alias": "Drop Me", "roles": [], "connector": "htpasswd"})})

    deleted = _user_db().delete_users([drop])

    assert set(deleted) == {drop}
    assert deleted[drop].alias == "Drop Me"
    assert deleted[drop].connection_id == "htpasswd"


@pytest.mark.usefixtures("request_context")
def test_delete_users_removes_only_the_requested_users() -> None:
    keep, drop = UserId("keep"), UserId("drop")
    _seed_users(
        {
            keep: UserSpec({"alias": "Keep Me", "roles": []}),
            drop: UserSpec({"alias": "Drop Me", "roles": []}),
        }
    )

    _user_db().delete_users([drop])

    remaining = load_users()
    assert drop not in remaining
    assert keep in remaining


@pytest.mark.usefixtures("request_context")
def test_delete_users_tolerates_the_same_user_requested_twice() -> None:
    drop = UserId("drop")
    _seed_users({drop: UserSpec({"alias": "Drop Me", "roles": []})})

    deleted = _user_db().delete_users([drop, drop])

    assert set(deleted) == {drop}
    assert drop not in load_users()


@pytest.mark.usefixtures("request_context")
def test_delete_users_raises_naming_all_unknown_users() -> None:
    user_id = UserId("happy")
    _seed_users({user_id: UserSpec({"alias": "Happy Testuser", "roles": []})})

    with pytest.raises(UserNotFoundError, match="Unknown users: ghost, phantom"):
        _user_db().delete_users([user_id, UserId("phantom"), UserId("ghost")])


@pytest.mark.usefixtures("request_context")
def test_delete_users_deletes_nothing_when_any_user_is_unknown() -> None:
    user_id = UserId("happy")
    _seed_users({user_id: UserSpec({"alias": "Happy Testuser", "roles": []})})

    with pytest.raises(UserNotFoundError):
        _user_db().delete_users([user_id, UserId("ghost")])

    assert user_id in load_users()
