#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from testlib import is_managed_repo, on_time

import cmk.utils.paths
import cmk.utils.version
from cmk.utils.type_defs import UserId

import cmk.gui.config as config
import cmk.gui.plugins.userdb.htpasswd as htpasswd
import cmk.gui.plugins.userdb.ldap_connector as ldap
import cmk.gui.plugins.userdb.utils as utils
import cmk.gui.userdb as userdb
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.globals import g
from cmk.gui.valuespec import Dictionary


@pytest.fixture(name="fix_time", autouse=True)
def fixture_time():
    with on_time("2019-09-05 00:00:00", "UTC"):
        yield


@pytest.fixture(name="user_id")
def fixture_user_id(with_user):
    return UserId(with_user[0])


@pytest.fixture(name="zero_uuid")
def zero_uuid_fixture(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(uuid, "uuid4", lambda: "00000000-0000-0000-0000-000000000000")


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def single_user_session_enabled(monkeypatch, user_id):
    monkeypatch.setattr(config, "single_user_session", 10)
    assert config.single_user_session == 10


def _load_users_uncached(*, lock):
    try:
        return userdb.load_users(lock=lock)
    finally:
        # TODO: It's bad that we have to do this here (after each load_users)
        del g.users


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def lock_on_logon_failures_enabled(monkeypatch, user_id):
    monkeypatch.setattr(config, "lock_on_logon_failures", 3)
    assert config.lock_on_logon_failures == 3


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def user_idle_timeout_enabled(monkeypatch, user_id):
    monkeypatch.setattr(config, "user_idle_timeout", 8)
    assert config.user_idle_timeout == 8


@pytest.fixture(name="session_timed_out")
def fixture_session_timed_out(monkeypatch, user_id, fix_time):
    session_id = "sess1"
    now = int(time.time()) - 20
    userdb._save_session_infos(user_id, {
        session_id: userdb.SessionInfo(
            session_id,
            started_at=now,
            last_activity=now,
            flashes=[],
        )
    })
    return session_id


@pytest.fixture(name="session_valid")
def fixture_session_valid(monkeypatch, user_id, fix_time):
    session_id = "sess2"
    now = int(time.time()) - 5
    userdb._save_session_infos(user_id, {
        session_id: userdb.SessionInfo(
            session_id,
            started_at=now,
            last_activity=now,
            flashes=[],
        )
    })
    return session_id


@pytest.fixture(name="session_pre_20")
def fixture_session_pre_20(monkeypatch, user_id, fix_time):
    session_id = "sess2"
    userdb.save_custom_attr(user_id, "session_info", "%s|%s" % (session_id, int(time.time() - 5)))
    return session_id


def test_load_pre_20_session(user_id, session_pre_20):
    old_session = userdb._load_session_infos(user_id)
    assert isinstance(old_session, dict)
    assert old_session["sess2"].started_at == int(time.time()) - 5
    assert old_session["sess2"].last_activity == int(time.time()) - 5


def test_on_succeeded_login(user_id: UserId, zero_uuid: None) -> None:
    assert config.single_user_session is None

    # Never logged in before
    assert not userdb._load_session_infos(user_id)
    assert userdb._load_failed_logins(user_id) == 0

    session_id = userdb.on_succeeded_login(user_id)
    assert session_id != ""

    # Verify the session was initialized
    session_infos = userdb._load_session_infos(user_id)
    assert session_infos == {
        session_id: userdb.SessionInfo(
            session_id=session_id,
            started_at=int(time.time()),
            last_activity=int(time.time()),
            flashes=[],
            csrf_token="00000000-0000-0000-0000-000000000000",
        )
    }

    # Ensure the failed login count is 0
    assert userdb._load_failed_logins(user_id) == 0


@pytest.mark.usefixtures("register_builtin_html")
def test_on_failed_login_no_locking(user_id):
    assert config.lock_on_logon_failures is False
    assert userdb._load_failed_logins(user_id) == 0
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 1
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 2
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 3
    assert userdb.user_locked(user_id) is False


@pytest.mark.usefixtures("register_builtin_html")
def test_on_failed_login_count_reset_on_succeeded_login(user_id):
    assert config.lock_on_logon_failures is False
    assert userdb._load_failed_logins(user_id) == 0
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 1
    assert userdb.user_locked(user_id) is False

    userdb.on_succeeded_login(user_id)
    assert userdb._load_failed_logins(user_id) == 0
    assert userdb.user_locked(user_id) is False


@pytest.mark.usefixtures("lock_on_logon_failures_enabled", "register_builtin_html")
def test_on_failed_login_with_locking(user_id):
    assert config.lock_on_logon_failures == 3
    assert userdb._load_failed_logins(user_id) == 0
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 1
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 2
    assert userdb.user_locked(user_id) is False

    userdb.on_failed_login(user_id)
    assert userdb._load_failed_logins(user_id) == 3
    assert userdb.user_locked(user_id) is True


def test_on_logout_no_session(user_id):
    assert userdb.on_succeeded_login(user_id)
    assert userdb._load_session_infos(user_id)

    userdb.on_logout(user_id, session_id="")
    assert userdb._load_session_infos(user_id)


def test_on_logout_invalidate_session(user_id):
    session_id = userdb.on_succeeded_login(user_id)
    assert session_id in userdb._load_session_infos(user_id)

    userdb.on_logout(user_id, session_id)
    assert not userdb._load_session_infos(user_id)


def test_access_denied_with_invalidated_session(user_id):
    session_id = userdb.on_succeeded_login(user_id)
    assert session_id in userdb._load_session_infos(user_id)

    userdb.on_access(user_id, session_id)

    userdb.on_logout(user_id, session_id)
    assert not userdb._load_session_infos(user_id)

    with pytest.raises(MKAuthException, match="Invalid user session"):
        userdb.on_access(user_id, session_id)


def test_on_access_update_valid_session(user_id, session_valid):
    old_session_infos = userdb._load_session_infos(user_id)
    old_session = old_session_infos[session_valid]

    userdb.on_access(user_id, session_valid)
    userdb.on_end_of_request(user_id)

    new_session_infos = userdb._load_session_infos(user_id)
    new_session = new_session_infos[session_valid]

    assert new_session.session_id == old_session.session_id
    assert new_session.started_at == old_session.started_at
    assert new_session.last_activity == time.time()
    assert new_session.last_activity > old_session.last_activity


def test_on_access_update_idle_session(user_id, session_timed_out):
    old_session_infos = userdb._load_session_infos(user_id)
    old_session = old_session_infos[session_timed_out]

    userdb.on_access(user_id, session_timed_out)
    userdb.on_end_of_request(user_id)

    new_session_infos = userdb._load_session_infos(user_id)
    new_session = new_session_infos[session_timed_out]

    assert new_session.session_id == old_session.session_id
    assert new_session.started_at == old_session.started_at
    assert new_session.last_activity == time.time()
    assert new_session.last_activity > old_session.last_activity


@pytest.mark.usefixtures("single_user_session_enabled")
def test_on_access_update_unknown_session(user_id, session_valid):
    session_info = userdb._load_session_infos(user_id)[session_valid]
    session_info.started_at = 10

    with pytest.raises(MKAuthException, match="Invalid user session"):
        userdb.on_access(user_id, "xyz")


@pytest.mark.usefixtures("user_idle_timeout_enabled")
def test_on_access_logout_on_idle_timeout(user_id, session_timed_out):
    session_info = userdb._load_session_infos(user_id)[session_timed_out]
    session_info.started_at = int(time.time()) - 10

    with pytest.raises(MKAuthException, match="login timed out"):
        userdb.on_access(user_id, session_timed_out)


@pytest.mark.usefixtures("single_user_session_enabled")
def test_on_succeeded_login_already_existing_session(user_id, session_valid):
    with pytest.raises(MKUserError, match="Another session"):
        assert userdb.on_succeeded_login(user_id)


def test_is_valid_user_session_single_user_session_disabled(user_id):
    assert config.single_user_session is None
    assert userdb._is_valid_user_session(user_id, userdb._load_session_infos(user_id),
                                         "session1") is False


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_not_existing(user_id):
    assert userdb._is_valid_user_session(user_id, userdb._load_session_infos(user_id),
                                         "not-existing-session") is False


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_still_valid_when_last_activity_extends_timeout(
        user_id, session_timed_out):
    assert userdb._is_valid_user_session(user_id, userdb._load_session_infos(user_id),
                                         session_timed_out) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_valid(user_id, session_valid):
    assert userdb._is_valid_user_session(user_id, userdb._load_session_infos(user_id),
                                         session_valid) is True


def test_ensure_user_can_init_no_single_user_session(user_id):
    assert config.single_user_session is None
    assert userdb._ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_no_previous_session(user_id):
    assert userdb._ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_with_previous_session_timeout(monkeypatch, user_id):
    assert userdb._ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_not_init_with_previous_session(user_id, session_valid):
    with pytest.raises(MKUserError, match="Another session"):
        assert userdb._ensure_user_can_init_session(user_id) is False


def test_initialize_session_single_user_session(user_id: UserId, zero_uuid: None) -> None:
    session_id = userdb._initialize_session(user_id)
    assert session_id != ""
    session_infos = userdb._load_session_infos(user_id)
    assert session_infos[session_id] == userdb.SessionInfo(
        session_id=session_id,
        started_at=int(time.time()),
        last_activity=int(time.time()),
        flashes=[],
        csrf_token="00000000-0000-0000-0000-000000000000",
    )


def test_cleanup_old_sessions_no_existing():
    assert userdb._cleanup_old_sessions({}) == {}


def test_cleanup_old_sessions_remove_outdated():
    assert list(
        userdb._cleanup_old_sessions({
            "outdated": userdb.SessionInfo(
                session_id="outdated",
                started_at=int(time.time()) - (86400 * 10),
                last_activity=int(time.time()) - (86400 * 8),
                flashes=[],
            ),
            "keep": userdb.SessionInfo(
                session_id="keep",
                started_at=int(time.time()) - (86400 * 10),
                last_activity=int(time.time()) - (86400 * 5),
                flashes=[],
            ),
        }).keys()) == ["keep"]


def test_cleanup_old_sessions_too_many():
    sessions = {
        f"keep_{num}": userdb.SessionInfo(
            session_id=f"keep_{num}",
            started_at=int(time.time()) - (86400 * 10),
            last_activity=int(time.time()) - (86400 * 5) + num,
            flashes=[],
        ) for num in range(21)
    }

    assert sorted([
        'keep_1', 'keep_2', 'keep_3', 'keep_4', 'keep_5', 'keep_6', 'keep_7', 'keep_8', 'keep_9',
        'keep_10', 'keep_11', 'keep_12', 'keep_13', 'keep_14', 'keep_15', 'keep_16', 'keep_17',
        'keep_18', 'keep_19', 'keep_20'
    ]) == sorted(userdb._cleanup_old_sessions(sessions).keys())


def test_create_session_id_is_correct_type():
    id1 = userdb._create_session_id()
    assert isinstance(id1, str)


def test_create_session_id_changes():
    assert userdb._create_session_id() != userdb._create_session_id()


def test_refresh_session_success(user_id, session_valid):
    session_infos = userdb._load_session_infos(user_id)
    assert session_infos
    old_session = userdb.SessionInfo(**asdict(session_infos[session_valid]))

    with on_time("2019-09-05 00:00:30", "UTC"):
        userdb._set_session(user_id, session_infos[session_valid])
        userdb._refresh_session(user_id, session_infos[session_valid])
        userdb.on_end_of_request(user_id)

        new_session_infos = userdb._load_session_infos(user_id)

        new_session = new_session_infos[session_valid]
        assert old_session.session_id == new_session.session_id
        assert new_session.last_activity > old_session.last_activity


def test_invalidate_session(user_id, session_valid):
    assert session_valid in userdb._load_session_infos(user_id)
    userdb._invalidate_session(user_id, session_valid)
    assert not userdb._load_session_infos(user_id)


def test_get_last_activity(with_user, session_valid):
    user_id = with_user[0]
    user = _load_users_uncached(lock=False)[user_id]
    assert "session_info" not in user
    assert userdb.get_last_activity(user_id, user) == 0

    userdb.on_access(user_id, session_valid)
    userdb.on_end_of_request(user_id)

    user = _load_users_uncached(lock=False)[user_id]
    assert "session_info" in user
    assert userdb.get_last_activity(user_id, user) == time.time()


def test_user_attribute_sync_plugins(monkeypatch):
    monkeypatch.setattr(config, "wato_user_attrs", [{
        'add_custom_macro': False,
        'help': u'VIP attribute',
        'name': 'vip',
        'show_in_table': False,
        'title': u'VIP',
        'topic': 'ident',
        'type': 'TextAscii',
        'user_editable': True
    }])

    monkeypatch.setattr(utils, "user_attribute_registry", utils.UserAttributeRegistry())
    monkeypatch.setattr(userdb, "user_attribute_registry", utils.user_attribute_registry)
    monkeypatch.setattr(ldap, "ldap_attribute_plugin_registry", ldap.LDAPAttributePluginRegistry())

    assert "vip" not in utils.user_attribute_registry
    assert "vip" not in ldap.ldap_attribute_plugin_registry

    userdb.update_config_based_user_attributes()

    assert "vip" in utils.user_attribute_registry
    assert "vip" in ldap.ldap_attribute_plugin_registry

    connection = ldap.LDAPUserConnector({
        "id": "ldp",
        "directory_type": ("ad", {
            "connect_to": ("fixed_list", {
                "server": "127.0.0.1",
            })
        })
    })

    ldap_plugin = ldap.ldap_attribute_plugin_registry["vip"]()
    assert ldap_plugin.title == "VIP"
    assert ldap_plugin.help == "VIP attribute"
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert isinstance(ldap_plugin.parameters(connection), Dictionary)

    # Test removing previously registered ones
    monkeypatch.setattr(config, "wato_user_attrs", [])
    userdb.update_config_based_user_attributes()

    assert "vip" not in utils.user_attribute_registry
    assert "vip" not in ldap.ldap_attribute_plugin_registry


def test_check_credentials_local_user(with_user):
    username, password = with_user
    assert userdb.check_credentials(username, password) == username


@pytest.mark.usefixtures("register_builtin_html")
def test_check_credentials_local_user_create_htpasswd_user_ad_hoc():
    user_id = UserId("sha256user")
    assert userdb.user_exists(user_id) is False
    assert userdb._user_exists_according_to_profile(user_id) is False
    assert user_id not in _load_users_uncached(lock=False)

    htpasswd.Htpasswd(Path(cmk.utils.paths.htpasswd_file)).save(
        {"sha256user": htpasswd.hash_password("cmk")})
    # Once a user exists in the htpasswd, the GUI treats the user as existing user and will
    # automatically initialize the missing data structures
    assert userdb.user_exists(user_id) is True
    assert userdb._user_exists_according_to_profile(user_id) is False
    assert str(user_id) in _load_users_uncached(lock=False)

    assert userdb.check_credentials(user_id, "cmk") == user_id

    # Nothing changes during regular access
    assert userdb.user_exists(user_id) is True
    assert userdb._user_exists_according_to_profile(user_id) is False
    assert str(user_id) in _load_users_uncached(lock=False)


def test_check_credentials_local_user_disallow_locked(with_user):
    user_id, password = with_user
    assert userdb.check_credentials(user_id, password) == user_id

    users = _load_users_uncached(lock=True)

    users[user_id]["locked"] = True
    userdb.save_users(users)

    assert userdb.check_credentials(user_id, password) is False


# user_id needs to be used here because it executes a reload of the config and the monkeypatch of
# the config needs to be done after loading the config
@pytest.fixture()
def make_cme(monkeypatch, user_id):
    if not is_managed_repo():
        pytest.skip("not relevant")

    monkeypatch.setattr(cmk.utils.version, "omd_version", lambda: "2.0.0i1.cme")
    assert cmk.utils.version.is_managed_edition()

    monkeypatch.setattr(config, "current_customer", "test-customer")
    # Fix CRE mypy tests that do not have this attribute defined
    assert config.current_customer == "test-customer"  # type: ignore[attr-defined]


@pytest.fixture()
def make_cme_global_user(user_id):
    if not is_managed_repo():
        pytest.skip("not relevant")

    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
    users = _load_users_uncached(lock=True)

    users[user_id]["customer"] = managed.SCOPE_GLOBAL
    userdb.save_users(users)


@pytest.fixture()
def make_cme_customer_user(user_id):
    if not is_managed_repo():
        pytest.skip("not relevant")

    users = _load_users_uncached(lock=True)

    users[user_id]["customer"] = "test-customer"
    userdb.save_users(users)


@pytest.fixture()
def make_cme_wrong_customer_user(user_id):
    if not is_managed_repo():
        pytest.skip("not relevant")

    users = _load_users_uncached(lock=True)

    users[user_id]["customer"] = "wrong-customer"
    userdb.save_users(users)


@pytest.mark.usefixtures("make_cme", "make_cme_global_user")
def test_check_credentials_managed_global_user_is_allowed(with_user):
    if not is_managed_repo():
        pytest.skip("not relevant")

    user_id, password = with_user
    assert userdb.check_credentials(user_id, password) == user_id


@pytest.mark.usefixtures("make_cme", "make_cme_customer_user")
def test_check_credentials_managed_customer_user_is_allowed(with_user):
    if not is_managed_repo():
        pytest.skip("not relevant")

    user_id, password = with_user
    assert userdb.check_credentials(user_id, password) == user_id


@pytest.mark.usefixtures("make_cme", "make_cme_wrong_customer_user")
def test_check_credentials_managed_wrong_customer_user_is_denied(with_user):
    if not is_managed_repo():
        pytest.skip("not relevant")

    user_id, password = with_user
    assert userdb.check_credentials(user_id, password) is False


def test_load_custom_attr_not_existing(user_id):
    assert userdb.load_custom_attr(user_id, "a", conv_func=str) is None


def test_load_custom_attr_not_existing_with_default(user_id):
    assert userdb.load_custom_attr(user_id, "a", conv_func=str, default="deflt") == "deflt"


def test_load_custom_attr_from_file(user_id):
    with Path(userdb.custom_attr_path(user_id, "a")).open("w") as f:
        f.write("xyz\n")
    assert userdb.load_custom_attr(user_id, "a", conv_func=str) == "xyz"


def test_load_custom_attr_convert(user_id):
    with Path(userdb.custom_attr_path(user_id, "a")).open("w") as f:
        f.write("xyz\n")
    assert userdb.load_custom_attr(user_id, "a", conv_func=lambda x: "a"
                                   if x == "xyz" else "b") == "a"


def test_cleanup_user_profiles_keep_recently_updated(user_id):
    (profile := Path(config.config_dir, "profile")).mkdir()
    (profile / "bla.mk").touch()
    userdb.UserProfileCleanupBackgroundJob()._do_cleanup()
    assert profile.exists()


def test_cleanup_user_profiles_remove_empty(user_id):
    (profile := Path(config.config_dir, "profile")).mkdir()
    userdb.UserProfileCleanupBackgroundJob()._do_cleanup()
    assert not profile.exists()


def test_cleanup_user_profiles_remove_abandoned(user_id):
    (profile := Path(config.config_dir, "profile")).mkdir()
    (bla := profile / "bla.mk").touch()
    with on_time('2018-04-15 16:50', 'CET'):
        os.utime(bla, (time.time(), time.time()))
    userdb.UserProfileCleanupBackgroundJob()._do_cleanup()
    assert not profile.exists()


def test_cleanup_user_profiles_keep_active_profile(user_id):
    assert Path(config.config_dir, user_id).exists()
    userdb.UserProfileCleanupBackgroundJob()._do_cleanup()
    assert Path(config.config_dir, user_id).exists()


def test_cleanup_user_profiles_keep_active_profile_old(user_id):
    profile_dir = Path(config.config_dir, user_id)

    assert profile_dir.exists()

    with on_time('2018-04-15 16:50', 'CET'):
        for file_path in profile_dir.glob("*.mk"):
            os.utime(file_path, (time.time(), time.time()))

    userdb.UserProfileCleanupBackgroundJob()._do_cleanup()
    assert Path(config.config_dir, user_id).exists()
