#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import pytest

from testlib import on_time

from cmk.utils.type_defs import UserId

from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Dictionary
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.plugins.userdb.utils as utils
import cmk.gui.plugins.userdb.ldap_connector as ldap


@pytest.fixture(name="fix_time", autouse=True)
def fixture_time():
    with on_time("2019-09-05 00:00:00", "UTC"):
        yield


@pytest.fixture()
def single_user_session_enabled(monkeypatch):
    monkeypatch.setattr(config, "single_user_session", 10)
    assert config.single_user_session == 10


@pytest.fixture(name="user_id")
def fixture_user_id():
    return UserId("ted")


@pytest.fixture(name="session_timed_out")
def fixture_session_timed_out(monkeypatch, user_id, fix_time):
    session_id = "sess1"
    userdb.save_custom_attr(user_id, "session_info", "%s|%s" % (session_id, int(time.time() - 20)))
    return session_id


@pytest.fixture(name="session_valid")
def fixture_session_valid(monkeypatch, user_id, fix_time):
    session_id = "sess2"
    userdb.save_custom_attr(user_id, "session_info", "%s|%s" % (session_id, int(time.time() - 5)))
    return session_id


def test_is_valid_user_session_single_user_session_disabled(user_id):
    assert config.single_user_session is None
    assert userdb.is_valid_user_session(user_id, "session1") is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_not_existing(user_id):
    assert userdb.is_valid_user_session(user_id, "not-existing-session") is False


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_still_valid_when_last_activity_extends_timeout(
        user_id, session_timed_out):
    assert userdb.is_valid_user_session(user_id, session_timed_out) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_is_valid_user_session_valid(user_id, session_valid):
    assert userdb.is_valid_user_session(user_id, session_valid) is True


def test_ensure_user_can_init_no_single_user_session(user_id):
    assert config.single_user_session is None
    assert userdb.ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_no_previous_session(user_id):
    assert userdb.ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_init_with_previous_session_timeout(monkeypatch, user_id):
    assert userdb.ensure_user_can_init_session(user_id) is True


@pytest.mark.usefixtures("single_user_session_enabled")
def test_ensure_user_can_not_init_with_previous_session(monkeypatch, user_id):
    monkeypatch.setattr(userdb, "load_session_info", lambda u: ("a", time.time() - 5))

    with pytest.raises(MKUserError, match="Another session"):
        assert userdb.ensure_user_can_init_session(user_id) is False


def test_initialize_session_single_user_session_not_enabled(user_id):
    assert userdb.initialize_session(user_id) == ""


@pytest.mark.usefixtures("single_user_session_enabled")
def test_initialize_session_single_user_session(user_id):
    session_id = userdb.initialize_session(user_id)
    assert session_id != ""
    assert userdb.load_session_info(user_id) == (session_id, int(time.time()))


@pytest.mark.usefixtures("single_user_session_enabled")
def test_create_session_id_is_correct_type():
    id1 = userdb.create_session_id()
    assert isinstance(id1, str)


@pytest.mark.usefixtures("single_user_session_enabled")
def test_create_session_id_changes():
    assert userdb.create_session_id() != userdb.create_session_id()


def test_refresh_session_single_user_session_not_enabled(user_id):
    assert config.single_user_session is None
    userdb.refresh_session(user_id)
    assert userdb.load_session_info(user_id) is None


@pytest.mark.usefixtures("single_user_session_enabled")
def test_refresh_session_success(user_id, session_valid):
    session_info = userdb.load_session_info(user_id)
    assert session_info is not None
    old_session_id, old_last_activity = session_info

    with on_time("2019-09-05 00:00:30", "UTC"):
        userdb.refresh_session(user_id)

        new_session_info = userdb.load_session_info(user_id)
        assert new_session_info is not None
        new_session_id, new_last_activity = new_session_info
        assert old_session_id == new_session_id
        assert new_last_activity > old_last_activity


def test_invalidate_session_single_user_session_disabled(user_id, session_valid):
    assert userdb.load_session_info(user_id) is not None
    userdb.invalidate_session(user_id)
    assert userdb.load_session_info(user_id) is None


@pytest.mark.usefixtures("single_user_session_enabled")
def test_invalidate_session(user_id, session_valid):
    assert userdb.load_session_info(user_id) is not None
    userdb.invalidate_session(user_id)
    assert userdb.load_session_info(user_id) is None


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
