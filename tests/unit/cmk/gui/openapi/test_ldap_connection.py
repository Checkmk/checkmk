#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from tests.testlib.rest_api_client import ClientRegistry

from cmk.gui.userdb._connections import ACTIVE_DIR

# LDAPConnection (Internal representation)
active_directory: ACTIVE_DIR = ("ad", {"connect_to": ("fixed_list", {"server": "10.200.3.32"})})

# groups_to_sync: list[GroupsToSync] = [
groups_to_sync = [
    {
        "cn": "groupcn1",
        "attribute": (
            "disable_notifications",
            {"disable": True, "timerange": (1707811999.0, 1707812555.0)},
        ),
    },
    {
        "cn": "groupcn2",
        "attribute": ("icons_per_item", "entry"),
    },
    {
        "cn": "groupcn3",
        "attribute": ("nav_hide_icons_title", "hide"),
    },
    {
        "cn": "groupcn4",
        "attribute": ("show_mode", "enforce_show_more"),
    },
    {
        "cn": "groupcn5",
        "attribute": ("ui_sidebar_position", "left"),
    },
    {
        "cn": "groupcn6",
        "attribute": ("start_url", "dashboard.py"),
    },
    {
        "cn": "groupcn7",
        "attribute": ("temperature_unit", "fahrenheit"),
    },
    {
        "cn": "groupcn8",
        "attribute": ("ui_theme", "facelift"),
    },
    {
        "cn": "groupcn9",
        "attribute": ("force_authuser", True),
    },
    {
        "cn": "groupcn10",
        "attribute": ("custom_usr_attr", "its_alive"),
    },
]


# test_ldap_connection: LDAPConnectionTypedDict = {
test_ldap_connection = {
    "id": "LDAP_1",
    "description": "1st ldap connection",
    "comment": "test_comment",
    "docu_url": "https://checkmk.com/doc/ldap_connection.html",
    "disabled": False,
    "cache_livetime": 291900,
    "directory_type": active_directory,
    "bind": ("cn=ldap,ou=Benutzer,dc=corp,dc=de", ("password", "ldap")),
    "port": 389,
    "use_ssl": True,
    "connect_timeout": 5.0,
    "version": 3,
    "page_size": 1000,
    "response_timeout": 60,
    "suffix": "dc=corp,dc=de",
    "user_dn": "ou=Benutzer,dc=corp,dc=de",
    "user_scope": "base",
    "user_filter": "(&(objectclass=user)(objectcategory=person))",
    "user_filter_group": "filtergroupexample",
    "user_id": "userattributeexample",
    "lower_user_ids": True,
    "user_id_umlauts": "keep",
    "create_only_on_login": True,
    "group_dn": "ou=Gruppen,dc=corp,dc=de",
    "group_scope": "sub",
    "group_filter": "(objectclass=group)",
    "group_member": "member",
    "active_plugins": {
        "alias": {"attr": "cn"},
        "auth_expire": {"attr": "pwdlastset"},
        "disable_notifications": {"attr": "disable_notifications"},
        "email": {"attr": "mail"},
        "icons_per_item": {"attr": "icons_per_item"},
        "nav_hide_icons_title": {"attr": "nav_hide_icons_title"},
        "pager": {"attr": "mobile"},
        "show_mode": {"attr": "show_mode"},
        "ui_sidebar_position": {"attr": "ui_sidebar_position"},
        "start_url": {"attr": "some_url"},
        "temperature_unit": {"attr": "temperature_unit"},
        "ui_theme": {"attr": "ui_theme"},
        "force_authuser": {"attr": "force_authuser"},
        "groups_to_contactgroups": {"nested": True, "other_connections": ["TEST"]},
        "groups_to_attributes": {
            "nested": True,
            "other_connections": ["TEST"],
            "groups": groups_to_sync,
        },
        "groups_to_roles": {
            "admin": [("groupdn1", None)],  # None means this connection
            "user": [("groupdn1", "LDAP1")],
        },
    },
    "type": "ldap",
}

test_api_data = {
    "general_properties": {
        "id": "LDAP_1",
        "description": "1st ldap connection",
        "comment": "test_comment",
        "documentation_url": "https://checkmk.com/doc/ldap_connection.html",
        "rule_activation": "activated",
    },
    "ldap_connection": {
        "directory_type": {
            "type": "active_directory_manual",
            "ldap_server": "10.200.3.32",
            "failover_servers": [],
        },
        "bind_credentials": {
            "state": "enabled",
            "type": "explicit",
            "bind_dn": "cn=ldap,ou=Benutzer,dc=corp,dc=de",
            "explicit_password": "ldap",
        },
        "tcp_port": {"state": "enabled", "port": 389},
        "ssl_encryption": "enable_ssl",
        "connect_timeout": {"state": "enabled", "seconds": 5.0},
        "ldap_version": {"state": "enabled", "version": 3},
        "page_size": {"state": "enabled", "size": 1000},
        "response_timeout": {"state": "enabled", "seconds": 60},
        "connection_suffix": {"state": "enabled", "suffix": "dc=corp,dc=de"},
    },
    "users": {
        "user_base_dn": "ou=Benutzer,dc=corp,dc=de",
        "search_scope": "search_only_base_dn_entry",
        "search_filter": {
            "state": "enabled",
            "filter": "(&(objectclass=user)(objectcategory=person))",
        },
        "filter_group": {"state": "enabled", "filter": "filtergroupexample"},
        "user_id_attribute": {"state": "enabled", "attribute": "userattributeexample"},
        "user_id_case": "convert_to_lowercase",
        "umlauts_in_user_ids": "keep_umlauts",
        "create_users": "on_login",
    },
    "groups": {
        "group_base_dn": "ou=Gruppen,dc=corp,dc=de",
        "search_scope": "search_whole_subtree",
        "search_filter": {"state": "enabled", "filter": "(objectclass=group)"},
        "member_attribute": {"state": "enabled", "attribute": "member"},
    },
    "sync_plugins": {
        "alias": {"state": "enabled", "attribute_to_sync": "cn"},
        "authentication_expiration": {"state": "enabled", "attribute_to_sync": "pwdlastset"},
        "disable_notifications": {"state": "enabled", "attribute_to_sync": "disable_notifications"},
        "email_address": {"state": "enabled", "attribute_to_sync": "mail"},
        "mega_menu_icons": {"state": "enabled", "attribute_to_sync": "icons_per_item"},
        "navigation_bar_icons": {"state": "enabled", "attribute_to_sync": "nav_hide_icons_title"},
        "pager": {"state": "enabled", "attribute_to_sync": "mobile"},
        "show_mode": {"state": "enabled", "attribute_to_sync": "show_mode"},
        "ui_sidebar_position": {"state": "enabled", "attribute_to_sync": "ui_sidebar_position"},
        "start_url": {"state": "enabled", "attribute_to_sync": "some_url"},
        "temperature_unit": {"state": "enabled", "attribute_to_sync": "temperature_unit"},
        "ui_theme": {"state": "enabled", "attribute_to_sync": "ui_theme"},
        "visibility_of_hosts_or_services": {
            "state": "enabled",
            "attribute_to_sync": "force_authuser",
        },
        "contact_group_membership": {
            "state": "enabled",
            "handle_nested": True,
            "sync_from_other_connections": ["TEST"],
        },
        "groups_to_custom_user_attributes": {
            "state": "enabled",
            "handle_nested": True,
            "sync_from_other_connections": ["TEST"],
            "groups_to_sync": [
                {
                    "group_cn": "groupcn1",
                    "attribute_to_set": "disable_notifications",
                    "value": {
                        "temporarily_disable_all_notifications": True,
                        "custom_time_range": {
                            "state": "enabled",
                            "from_time": "2024-02-13T08:13:19+00:00",
                            "to_time": "2024-02-13T08:22:35+00:00",
                        },
                    },
                },
                {
                    "group_cn": "groupcn2",
                    "attribute_to_set": "mega_menu_icons",
                    "value": "per_entry",
                },
                {
                    "group_cn": "groupcn3",
                    "attribute_to_set": "navigation_bar_icons",
                    "value": "do_not_show_title",
                },
                {
                    "group_cn": "groupcn4",
                    "attribute_to_set": "show_mode",
                    "value": "enforce_show_more",
                },
                {
                    "group_cn": "groupcn5",
                    "attribute_to_set": "ui_sidebar_position",
                    "value": "left",
                },
                {
                    "group_cn": "groupcn6",
                    "attribute_to_set": "start_url",
                    "value": "dashboard.py",
                },
                {
                    "group_cn": "groupcn7",
                    "attribute_to_set": "temperature_unit",
                    "value": "fahrenheit",
                },
                {
                    "group_cn": "groupcn8",
                    "attribute_to_set": "ui_theme",
                    "value": "light",
                },
                {
                    "group_cn": "groupcn9",
                    "attribute_to_set": "visibility_of_hosts_or_services",
                    "value": "show_for_user_contacts_only",
                },
                {
                    "group_cn": "groupcn10",
                    "attribute_to_set": "custom_usr_attr",
                    "value": "its_alive",
                },
            ],
        },
        "groups_to_roles": {
            "state": "enabled",
            "admin": [{"group_dn": "groupdn1", "search_in": "this_connection"}],
            "user": [{"group_dn": "groupdn1", "search_in": "LDAP1"}],
        },
    },
    "other": {
        "sync_interval": {"days": 3, "hours": 9, "minutes": 5},
    },
}


@pytest.fixture(name="mock_ldap_connections_config")
def fixture_mock_users_config(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.openapi.endpoints.ldap_connection.internal_to_restapi_interface.get_ldap_connections",
        return_value={"LDAP_1": test_ldap_connection},
    )


@pytest.fixture(name="mock_ldap_connection_field")
def fixture_mock_ldap_field(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.fields.custom_fields.connection_choices",
        return_value=[("LDAP_1", "")],
    )


@pytest.mark.usefixtures("mock_ldap_connection_field")
@pytest.mark.usefixtures("mock_ldap_connections_config")
def test_get_ldap_connection(clients: ClientRegistry) -> None:
    resp = clients.LdapConnection.get(ldap_connection_id="LDAP_1")
    assert "ETag" in resp.headers
    assert resp.json["extensions"] == test_api_data


def test_get_ldap_connection_doesnt_exist(clients: ClientRegistry) -> None:
    clients.LdapConnection.get(
        ldap_connection_id="LDAP_1",
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.usefixtures("mock_ldap_connections_config")
def test_get_ldap_connections(clients: ClientRegistry) -> None:
    resp = clients.LdapConnection.get_all()
    assert resp.json["value"][0]["extensions"] == test_api_data
