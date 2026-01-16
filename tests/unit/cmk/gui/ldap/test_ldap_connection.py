#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.ldap_integration.ldap_connector import LDAPUserConnector
from tests.testlib.unit.rest_api_client import ClientRegistry

# mypy: disable-error-code="type-arg"


# LDAP API Schema Example
# Hint: the alias is always added to the response, so we need to add it for response testing, but not for request schema
# TODO: DEPRECATED(18295) remove "mega_menu_icons"
def ldap_api_schema(ldap_id: str, include_mega_menu_icons: bool = False) -> dict:
    return {
        "general_properties": {
            "id": ldap_id,
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
            "connection_suffix": {"state": "enabled", "suffix": f"suffix_{ldap_id}"},
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
            "disable_notifications": {
                "state": "enabled",
                "attribute_to_sync": "disable_notifications",
            },
            "email_address": {"state": "enabled", "attribute_to_sync": "mail"},
            "main_menu_icons": {"state": "enabled", "attribute_to_sync": "icons_per_item"},
            # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            **(
                {"mega_menu_icons": {"state": "enabled", "attribute_to_sync": "icons_per_item"}}
                if include_mega_menu_icons
                else {}
            ),
            "navigation_bar_icons": {
                "state": "enabled",
                "attribute_to_sync": "nav_hide_icons_title",
            },
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
                "sync_from_other_connections": ["LDAP_1", "LDAP_2"],
            },
            "groups_to_custom_user_attributes": {
                "state": "enabled",
                "handle_nested": True,
                "sync_from_other_connections": ["LDAP_1", "LDAP_2"],
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
                        "attribute_to_set": "main_menu_icons",
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
                        "value": "default_start_url",
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
                "admin": [
                    {
                        "group_dn": "CN=cmk_AD_admins,ou=Gruppen,dc=corp,dc=de",
                        "search_in": "this_connection",
                    }
                ],
                "user": [
                    {"group_dn": "CN=cmk_AD_users,ou=Gruppen,dc=corp,dc=de", "search_in": "LDAP_1"}
                ],
                "handle_nested": True,
            },
        },
        "other": {
            "sync_interval": {"days": 3, "hours": 9, "minutes": 5},
        },
    }


# LDAP API Schema Example
def create_ldap_connections(clients: ClientRegistry) -> None:
    for n in range(1, 4):
        clients.LdapConnection.create(
            ldap_data={
                "general_properties": {"id": f"LDAP_{n}"},
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": "10.200.3.32",
                    },
                },
            }
        )


def test_get_ldap_connection_min_config(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    resp = clients.LdapConnection.get(ldap_connection_id="LDAP_1")
    assert "ETag" in resp.headers
    assert resp.json["extensions"] == {
        "general_properties": {
            "id": "LDAP_1",
            "description": "",
            "comment": "",
            "documentation_url": "",
            "rule_activation": "activated",
        },
        "ldap_connection": {
            "directory_type": {
                "type": "active_directory_manual",
                "ldap_server": "10.200.3.32",
                "failover_servers": [],
            },
            "bind_credentials": {"state": "disabled"},
            "tcp_port": {"state": "disabled"},
            "ssl_encryption": "disable_ssl",
            "connect_timeout": {"state": "disabled"},
            "ldap_version": {"state": "disabled"},
            "page_size": {"state": "disabled"},
            "response_timeout": {"state": "disabled"},
            "connection_suffix": {"state": "disabled"},
        },
        "users": {
            "user_base_dn": "",
            "search_scope": "search_only_base_dn_entry",
            "search_filter": {"state": "disabled"},
            "filter_group": {"state": "disabled"},
            "user_id_attribute": {"state": "disabled"},
            "user_id_case": "dont_convert_to_lowercase",
            "umlauts_in_user_ids": "keep_umlauts",
            "create_users": "on_login",
        },
        "groups": {
            "group_base_dn": "",
            "search_scope": "search_whole_subtree",
            "search_filter": {"state": "disabled"},
            "member_attribute": {"state": "disabled"},
        },
        "sync_plugins": {
            "alias": {"state": "disabled"},
            "authentication_expiration": {"state": "disabled"},
            "disable_notifications": {"state": "disabled"},
            "email_address": {"state": "disabled"},
            "main_menu_icons": {"state": "disabled"},
            "mega_menu_icons": {
                "state": "disabled"
            },  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            "navigation_bar_icons": {"state": "disabled"},
            "pager": {"state": "disabled"},
            "show_mode": {"state": "disabled"},
            "ui_sidebar_position": {"state": "disabled"},
            "start_url": {"state": "disabled"},
            "temperature_unit": {"state": "disabled"},
            "ui_theme": {"state": "disabled"},
            "visibility_of_hosts_or_services": {"state": "disabled"},
            "contact_group_membership": {"state": "disabled"},
            "groups_to_custom_user_attributes": {"state": "disabled"},
            "groups_to_roles": {"state": "disabled"},
        },
        "other": {"sync_interval": {"days": 0, "hours": 0, "minutes": 5}},
    }


def test_get_ldap_connection_doesnt_exist(clients: ClientRegistry) -> None:
    clients.LdapConnection.get(
        ldap_connection_id="LDAP_1",
        expect_ok=False,
    ).assert_status_code(404)


def test_get_ldap_connections(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    cnx4 = ldap_api_schema(ldap_id="LDAP_4")
    clients.LdapConnection.create(ldap_data=cnx4)
    resp = clients.LdapConnection.get_all()
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    assert resp.json["value"][3]["extensions"] == ldap_api_schema(
        ldap_id="LDAP_4", include_mega_menu_icons=True
    )


# TODO: DEPRECATED(18295) remove "mega_menu_icons"
def test_create_ldap_connection_with_field_and_alias_in_request(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.create(
        ldap_data=ldap_api_schema(ldap_id="LDAP_1", include_mega_menu_icons=True),
        expect_ok=False,
    ).assert_status_code(400)


def test_create_ldap_connection_existing_id(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.create(
        ldap_data=ldap_api_schema(ldap_id="LDAP_1"),
        expect_ok=False,
    ).assert_status_code(400)


def test_create_ldap_connection_existing_non_sync_connection(clients: ClientRegistry) -> None:
    clients.LdapConnection.create(
        ldap_data=ldap_api_schema(ldap_id="LDAP_1"),
        expect_ok=False,
    ).assert_status_code(400)


def test_delete_ldap_connection(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    resp = clients.LdapConnection.get_all()
    assert len(resp.json["value"]) == 3
    clients.LdapConnection.delete(ldap_connection_id="LDAP_1").assert_status_code(204)
    resp = clients.LdapConnection.get_all()
    assert len(resp.json["value"]) == 2


def test_delete_ldap_connection_valid_etag(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.delete(
        ldap_connection_id="LDAP_1",
        etag="valid_etag",
    )


def test_delete_ldap_connection_invalid_etag(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.delete(
        ldap_connection_id="LDAP_1",
        etag="invalid_etag",
        expect_ok=False,
    ).assert_status_code(412)


def test_edit_ldap_connection(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    edited_ldap_3 = ldap_api_schema(ldap_id="LDAP_3")
    clients.LdapConnection.edit(ldap_connection_id="LDAP_3", ldap_data=edited_ldap_3)
    resp = clients.LdapConnection.get_all()

    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    assert resp.json["value"][2]["extensions"] == ldap_api_schema(
        ldap_id="LDAP_3", include_mega_menu_icons=True
    )


# TODO: DEPRECATED(18295) remove "mega_menu_icons"
def test_edit_ldap_connection_using_mega_menu_icons_alias(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    request = ldap_api_schema(ldap_id="LDAP_3")
    # Use the alias "mega_menu_icons" instead of "main_menu_icons"
    request["sync_plugins"]["mega_menu_icons"] = request["sync_plugins"].pop("main_menu_icons")
    clients.LdapConnection.edit(ldap_connection_id="LDAP_3", ldap_data=request)
    resp = clients.LdapConnection.get_all()
    assert resp.json["value"][2]["extensions"] == ldap_api_schema(
        ldap_id="LDAP_3", include_mega_menu_icons=True
    )


def test_edit_ldap_connection_that_doesnt_exist(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.edit(
        ldap_connection_id="LDAP_4",
        ldap_data=ldap_api_schema(ldap_id="LDAP_4"),
        expect_ok=False,
    ).assert_status_code(404)


def test_edit_ldap_connection_valid_etag(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    resp1 = clients.LdapConnection.edit(
        ldap_connection_id="LDAP_3",
        ldap_data=ldap_api_schema(ldap_id="LDAP_3"),
        etag="valid_etag",
    )
    resp2 = clients.LdapConnection.get(ldap_connection_id="LDAP_3")
    assert resp1.headers["ETag"] == resp2.headers["ETag"]


def test_edit_ldap_connection_invalid_etag(clients: ClientRegistry) -> None:
    create_ldap_connections(clients)
    clients.LdapConnection.edit(
        ldap_connection_id="LDAP_3",
        ldap_data=ldap_api_schema(ldap_id="LDAP_3"),
        etag="invalid_etag",
        expect_ok=False,
    ).assert_status_code(412)


def test_cant_create_with_the_same_suffix(clients: ClientRegistry) -> None:
    clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_1"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.32",
                },
                "connection_suffix": {"state": "enabled", "suffix": "suffix_2"},
            },
        }
    )
    clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_2"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.33",
                },
                "connection_suffix": {"state": "enabled", "suffix": "suffix_2"},
            },
        },
        expect_ok=False,
    ).assert_status_code(400)


def test_update_ldap_suffixes_after_delete(clients: ClientRegistry) -> None:
    LDAPUserConnector.connection_suffixes = {}
    clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_1"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.32",
                },
                "connection_suffix": {"state": "enabled", "suffix": "suffix_1"},
            },
        }
    )

    assert LDAPUserConnector.get_connection_suffixes() == {"suffix_1": "LDAP_1"}
    clients.LdapConnection.delete(ldap_connection_id="LDAP_1").assert_status_code(204)
    assert not LDAPUserConnector.get_connection_suffixes()


def test_start_url_values(clients: ClientRegistry) -> None:
    assert (
        clients.LdapConnection.create(
            ldap_data={
                "general_properties": {"id": "LDAP_1"},
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": "10.200.3.32",
                    },
                },
                "sync_plugins": {
                    "groups_to_custom_user_attributes": {
                        "state": "enabled",
                        "groups_to_sync": [
                            {
                                "group_cn": "groupcn6",
                                "attribute_to_set": "start_url",
                                "value": "default_start_url",
                            },
                        ],
                    },
                },
            }
        ).json["extensions"]["sync_plugins"]["groups_to_custom_user_attributes"]["groups_to_sync"][
            0
        ]["value"]
        == "default_start_url"
    )

    assert (
        clients.LdapConnection.edit(
            ldap_connection_id="LDAP_1",
            ldap_data={
                "general_properties": {"id": "LDAP_1"},
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": "10.200.3.32",
                    },
                },
                "sync_plugins": {
                    "groups_to_custom_user_attributes": {
                        "state": "enabled",
                        "groups_to_sync": [
                            {
                                "group_cn": "groupcn6",
                                "attribute_to_set": "start_url",
                                "value": "welcome_page",
                            },
                        ],
                    },
                },
            },
        ).json["extensions"]["sync_plugins"]["groups_to_custom_user_attributes"]["groups_to_sync"][
            0
        ]["value"]
        == "welcome_page"
    )

    assert (
        clients.LdapConnection.edit(
            ldap_connection_id="LDAP_1",
            ldap_data={
                "general_properties": {"id": "LDAP_1"},
                "ldap_connection": {
                    "directory_type": {
                        "type": "active_directory_manual",
                        "ldap_server": "10.200.3.32",
                    },
                },
                "sync_plugins": {
                    "groups_to_custom_user_attributes": {
                        "state": "enabled",
                        "groups_to_sync": [
                            {
                                "group_cn": "groupcn6",
                                "attribute_to_set": "start_url",
                                "value": "custom_url",
                            },
                        ],
                    },
                },
            },
        ).json["extensions"]["sync_plugins"]["groups_to_custom_user_attributes"]["groups_to_sync"][
            0
        ]["value"]
        == "custom_url"
    )


def test_create_with_custom_user_role(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.LdapConnection.create(
        ldap_data={
            "general_properties": {"id": "LDAP_1"},
            "ldap_connection": {
                "directory_type": {
                    "type": "active_directory_manual",
                    "ldap_server": "10.200.3.32",
                },
                "connection_suffix": {"state": "enabled", "suffix": "suffix_3"},
            },
            "sync_plugins": {
                "groups_to_roles": {
                    "state": "enabled",
                    "admin": [
                        {
                            "group_dn": "CN=cmk_AD_admins,ou=Gruppen,dc=corp,dc=de",
                            "search_in": "this_connection",
                        }
                    ],
                    "user": [
                        {
                            "group_dn": "CN=cmk_AD_users,ou=Gruppen,dc=corp,dc=de",
                            "search_in": "this_connection",
                        }
                    ],
                    "adminx": [
                        {
                            "group_dn": "CN=cmk_AD_admins,ou=Gruppen,dc=corp,dc=de",
                            "search_in": "this_connection",
                        }
                    ],
                    "handle_nested": True,
                },
            },
        }
    )

    assert resp.json["extensions"]["sync_plugins"]["groups_to_roles"]["adminx"] == [
        {
            "group_dn": "CN=cmk_AD_admins,ou=Gruppen,dc=corp,dc=de",
            "search_in": "this_connection",
        }
    ]
