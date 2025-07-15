#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.gui.userdb import (
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
    UserConnectionConfigFile,
)
from cmk.gui.utils.script_helpers import gui_context

from cmk.update_config.plugins.actions.ldap_connections import UpdateLDAPConnections


def test_update_ldap_connection_not_changed() -> None:
    connection = LDAPUserConnectionConfig(
        {
            "id": "test",
            "description": "",
            "comment": "",
            "docu_url": "",
            "disabled": False,
            "directory_type": (
                "ad",
                LDAPConnectionConfigFixed(
                    {
                        "connect_to": (
                            "fixed_list",
                            {
                                "server": "10.1.1.1",
                                "failover_servers": ["10.1.1.3"],
                            },
                        )
                    }
                ),
            ),
            "bind": ("cn=schnief,ou=ding,dc=lala", ("password", "hugo")),
            "user_dn": "ou=ding,dc=lala",
            "user_scope": "sub",
            "user_id_umlauts": "keep",
            "group_dn": "ou=ding,dc=lala",
            "group_scope": "sub",
            "active_plugins": {},
            "cache_livetime": 300,
            "type": "ldap",
        }
    )
    UserConnectionConfigFile().save([connection], pprint_value=False)

    UpdateLDAPConnections(
        name="update_ldap_connections",
        title="Update LDAP connections",
        sort_index=100,  # can run whenever
    )(logging.getLogger())

    assert UserConnectionConfigFile().load_for_reading() == [connection]


def test_update_ldap_connection_directory_type() -> None:
    connection = {
        "id": "test",
        "description": "",
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "server": "bla.domain",
        "directory_type": (
            "ad",
            {
                "discover_nearest_dc": True,
            },
        ),
        "bind": ("cn=schnief,ou=ding,dc=lala", ("password", "hugo")),
        "user_dn": "ou=ding,dc=lala",
        "user_scope": "sub",
        "user_id_umlauts": "keep",
        "group_dn": "ou=ding,dc=lala",
        "group_scope": "sub",
        "active_plugins": {},
        "cache_livetime": 300,
        "type": "ldap",
    }
    UserConnectionConfigFile().save([connection], pprint_value=False)  # type: ignore[list-item]
    with gui_context():
        UpdateLDAPConnections(
            name="update_ldap_connections",
            title="Update LDAP connections",
            sort_index=100,  # can run whenever
        )(logging.getLogger())

    loaded_connection = UserConnectionConfigFile().load_for_reading()[0]
    assert loaded_connection["type"] == "ldap"
    assert loaded_connection["directory_type"] == (
        "ad",
        {"connect_to": ("discover", {"domain": "bla.domain"})},
    )


def test_update_ldap_connection_separate_server_and_directory_type() -> None:
    connection = {
        "id": "test",
        "description": "",
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "server": "bla.domain",
        "directory_type": "ad",
        "bind": ("cn=schnief,ou=ding,dc=lala", ("password", "hugo")),
        "user_dn": "ou=ding,dc=lala",
        "user_scope": "sub",
        "user_id_umlauts": "keep",
        "group_dn": "ou=ding,dc=lala",
        "group_scope": "sub",
        "active_plugins": {},
        "cache_livetime": 300,
        "type": "ldap",
    }
    UserConnectionConfigFile().save([connection], pprint_value=False)  # type: ignore[list-item]
    with gui_context():
        UpdateLDAPConnections(
            name="update_ldap_connections",
            title="Update LDAP connections",
            sort_index=100,  # can run whenever
        )(logging.getLogger())

    loaded_connection = UserConnectionConfigFile().load_for_reading()[0]
    assert loaded_connection["type"] == "ldap"
    assert loaded_connection["directory_type"] == (
        "ad",
        {"connect_to": ("fixed_list", {"server": "bla.domain"})},
    )
