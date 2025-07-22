#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cmk.ccc import version
from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.ldap.ldap_connector import LDAPUserConnector
from cmk.gui.session import SuperUserContext
from cmk.gui.type_defs import UserObjectValue
from cmk.gui.userdb._connections import Fixed, LDAPConnectionConfigFixed, LDAPUserConnectionConfig
from cmk.gui.watolib.users import default_sites, edit_users
from cmk.utils import paths
from tests.testlib.unit.rest_api_client import ClientRegistry

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@pytest.fixture(name="mock_ldap_locked_attributes")
def fixture_mock_ldap_locked_attributes(request_context: None, mocker: MockerFixture) -> MagicMock:
    """Mock the locked attributes of a LDAP user"""
    ldap_config = LDAPUserConnectionConfig(
        id="CMKTest",
        description="",
        comment="",
        docu_url="",
        disabled=False,
        directory_type=(
            "ad",
            LDAPConnectionConfigFixed(
                connect_to=(
                    "fixed_list",
                    Fixed(server="some.domain.com"),
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

    return mocker.patch(
        "cmk.gui.openapi.endpoints.user_config.locked_attributes",
        return_value=LDAPUserConnector(ldap_config).locked_attributes(),
    )


@pytest.mark.usefixtures("mock_ldap_locked_attributes")
@managedtest
def test_edit_ldap_user_with_locked_attributes(
    clients: ClientRegistry,
) -> None:
    name = UserId("foo")
    user_object: dict[UserId, UserObjectValue] = {
        name: {
            "attributes": {
                "ui_theme": None,
                "ui_sidebar_position": None,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "start_url": None,
                "force_authuser": False,
                "enforce_pw_change": True,
                "alias": "cmkADAdmin",
                "locked": False,
                "pager": "",
                "roles": ["guest"],
                "contactgroups": [],
                "email": "",
                "fallback_contact": False,
                "password": PasswordHash(
                    "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C"
                ),
                "serial": 1,
                "connector": "CMKTest",
                "disable_notifications": {},
            },
            "is_new_user": True,
        },
    }
    with SuperUserContext():
        edit_users(user_object, default_sites, use_git=False)

    clients.User.edit(
        username=name,
        roles=["admin"],
        expect_ok=False,
    ).assert_status_code(403)


def test_openapi_minimum_configuration(clients: ClientRegistry) -> None:
    create_resp = clients.User.create(username="user", fullname="User Test")
    get_resp = clients.User.get(username="user")

    assert create_resp.json == get_resp.json
    assert create_resp.json["id"] == "user"
    assert create_resp.json["extensions"]["fullname"] == "User Test"
