#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc import version
from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.config import active_config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.type_defs import UserSpec
from cmk.gui.user_connection_config_types import (
    Fixed,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
)
from cmk.gui.userdb import get_user_attributes, UserConnectionConfigFile
from cmk.gui.watolib.users import create_user, default_sites
from cmk.utils import paths
from tests.testlib.unit.rest_api_client import ClientRegistry

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@managedtest
def test_edit_ldap_user_with_locked_attributes(clients: ClientRegistry) -> None:
    name = UserId("foo")
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

    UserConnectionConfigFile().save([ldap_config], pprint_value=False)
    # Hope that this is not needed anymore soon
    active_config.user_connections = [ldap_config]

    user_object: UserSpec = {
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
    }
    create_user(
        name,
        user_object,
        default_sites,
        get_user_attributes([]),
        user_connections=[ldap_config],
        use_git=False,
        acting_user=LoggedInSuperUser(),
    )

    clients.User.edit(
        username=name,
        roles=["admin"],
        expect_ok=False,
    ).assert_status_code(403)
