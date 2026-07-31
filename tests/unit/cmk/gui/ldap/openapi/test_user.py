#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc.site import SiteId
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
from cmk.gui.userdb import get_user_attributes, load_users, UserConnectionConfigFile
from cmk.gui.watolib.pending_changes import PendingChanges, PendingChangesStore
from cmk.gui.watolib.users import create_user, default_sites
from tests.testlib.rest_api_client import ClientRegistry

LDAP_CONNECTION_ID = "CMKTest"


def _test_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=active_config.sites,
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=PendingChangesStore(),
        hooks=(),
    )


def _ldap_owned_user(name: UserId) -> None:
    """Register an LDAP connection and create a user it owns.

    The connection's ``groups_to_roles`` plug-in makes ``roles`` one of its
    locked attributes, so edits touching ``roles`` must be refused.
    """
    ldap_config = _ldap_connection_config()
    UserConnectionConfigFile().save([ldap_config], pprint_value=False)
    # Hope that this is not needed anymore soon
    active_config.user_connections = [ldap_config]
    create_user(
        name,
        _ldap_owned_user_spec(),
        default_sites,
        get_user_attributes([]),
        user_connections=[ldap_config],
        pending_changes=_test_pending_changes(),
        use_git=False,
        acting_user=LoggedInSuperUser(),
        pprint_value=False,
    )


def test_edit_ldap_user_with_locked_attributes(clients: ClientRegistry) -> None:
    name = UserId("foo")
    _ldap_owned_user(name)

    clients.User.edit(
        username=name,
        roles=["admin"],
        expect_ok=False,
        customer=None,
    ).assert_status_code(403)


@pytest.mark.xfail(
    strict=True,
    reason="CMK-37481: an auth_option flips the connector to htpasswd before the "
    "locked-attribute guard reads it, so the guard is skipped entirely",
)
def test_edit_ldap_user_with_auth_option_must_not_bypass_locked_attributes(
    clients: ClientRegistry,
) -> None:
    """Authentication details in the request must not disarm the locked-attribute guard.

    The request below is the ``roles`` change the test above proves is refused,
    with an ``auth_option`` added. That addition must not change the verdict:
    the LDAP connection still owns the user and still locks ``roles``, so the
    edit has to be refused, the user has to stay owned by the connection, and
    ``roles`` has to keep its stored value.
    """
    name = UserId("bar")
    _ldap_owned_user(name)

    clients.User.edit(
        username=name,
        roles=["admin"],
        auth_option={"auth_type": "password", "password": "supersecretpassword123"},
        expect_ok=False,
        customer=None,
    ).assert_status_code(403)

    user_spec = load_users()[name]
    assert user_spec["connector"] == LDAP_CONNECTION_ID, (
        "the edit reassigned the user to local authentication, detaching them from LDAP"
    )
    assert user_spec["roles"] == ["guest"], (
        "the edit wrote a locked attribute the owning connection manages"
    )


def _ldap_owned_user_spec() -> UserSpec:
    return UserSpec(
        ui_theme=None,
        ui_sidebar_position=None,
        nav_hide_icons_title=None,
        icons_per_item=None,
        show_mode=None,
        start_url=None,
        force_authuser=False,
        enforce_pw_change=True,
        alias="cmkADAdmin",
        locked=False,
        pager="",
        roles=["guest"],
        contactgroups=[],
        email="",
        fallback_contact=False,
        password=PasswordHash(
            "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C"
        ),
        serial=1,
        connector=LDAP_CONNECTION_ID,
        disable_notifications={},
    )


def _ldap_connection_config() -> LDAPUserConnectionConfig:
    return LDAPUserConnectionConfig(
        id=LDAP_CONNECTION_ID,
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
