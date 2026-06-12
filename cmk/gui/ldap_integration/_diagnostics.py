#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Diagnostic tests for LDAP connections."""

from collections.abc import Callable
from typing import Any, cast

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.ldap_integration.ldap_connector import (
    LDAPAttributePluginGroupsToRoles,
    LDAPUserConnector,
)
from cmk.gui.userdb import get_user_attributes
from cmk.gui.utils.escaping import strip_tags

LDAPDiagnosticTest = Callable[[LDAPUserConnector, str], tuple[bool, str | None]]


def diagnostic_tests() -> list[tuple[str, LDAPDiagnosticTest]]:
    return [
        (_("Connection"), _test_connect),
        (_("User Base-DN"), _test_user_base_dn),
        (_("Count Users"), _test_user_count),
        (_("Group Base-DN"), _test_group_base_dn),
        (_("Count Groups"), _test_group_count),
        (_("Sync-plug-in: Roles"), _test_groups_to_roles),
    ]


def _test_connect(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    conn, msg = connection.connect_server(address)
    if conn:
        return (True, _("Connection established. The connection settings seem to be OK."))
    return (False, msg)


def _test_user_base_dn(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    if not connection.has_user_base_dn_configured():
        return (False, _("The User Base DN is not configured."))
    connection.connect(enforce_new=True, enforce_server=address)
    if connection.user_base_dn_exists():
        return (True, _("The User Base DN could be found."))
    if connection.has_bind_credentials_configured():
        return (
            False,
            _(
                "The User Base DN could not be found. Maybe the provided "
                "user (provided via bind credentials) has no permission to "
                "access the Base DN or the credentials are wrong."
            ),
        )
    return (
        False,
        _(
            "The User Base DN could not be found. Seems you need "
            "to configure proper bind credentials."
        ),
    )


def _test_user_count(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    if not connection.has_user_base_dn_configured():
        return (False, _("The User Base DN is not configured."))
    connection.connect(enforce_new=True, enforce_server=address)
    try:
        ldap_users = connection.get_users(get_user_attributes(active_config.wato_user_attrs))
        msg = _("Found no user object for synchronization. Please check your filter settings.")
    except Exception as e:
        ldap_users = None
        msg = "%s" % e
        if "successful bind must be completed" in msg:
            if not connection.has_bind_credentials_configured():
                return (False, _("Please configure proper bind credentials."))
            return (
                False,
                _(
                    "Maybe the provided user (provided via bind credentials) has not "
                    "enough permissions or the credentials are wrong."
                ),
            )

    if ldap_users and len(ldap_users) > 0:
        return (True, _("Found %d users for synchronization.") % len(ldap_users))
    return (False, msg)


def _test_group_base_dn(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    if not connection.has_group_base_dn_configured():
        return (False, _("The Group Base DN is not configured, not fetching any groups."))
    connection.connect(enforce_new=True, enforce_server=address)
    if connection.group_base_dn_exists():
        return (True, _("The Group Base DN could be found."))
    return (False, _("The Group Base DN could not be found."))


def _test_group_count(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    if not connection.has_group_base_dn_configured():
        return (False, _("The Group Base DN is not configured, not fetching any groups."))
    connection.connect(enforce_new=True, enforce_server=address)
    try:
        ldap_groups = connection.get_groups()
        msg = _("Found no group object for synchronization. Please check your filter settings.")
    except Exception as e:
        ldap_groups = None
        msg = "%s" % e
        if "successful bind must be completed" in msg:
            if not connection.has_bind_credentials_configured():
                return (False, _("Please configure proper bind credentials."))
            return (
                False,
                _(
                    "Maybe the provided user (provided via bind credentials) has not "
                    "enough permissions or the credentials are wrong."
                ),
            )
    if ldap_groups and len(ldap_groups) > 0:
        return (True, _("Found %d groups for synchronization.") % len(ldap_groups))
    return (False, msg)


def _test_groups_to_roles(connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
    active_plugins = connection.active_plugins()
    if "groups_to_roles" not in active_plugins:
        return True, _("Skipping this test (plug-in is not enabled)")

    params = active_plugins["groups_to_roles"]
    connection.connect(enforce_new=True, enforce_server=address)

    plugin = LDAPAttributePluginGroupsToRoles()
    ldap_groups = plugin.fetch_needed_groups_for_groups_to_roles(connection, params)

    num_groups = 0

    for role_id, value in active_plugins["groups_to_roles"].items():
        if value is True:
            continue

        # We have typing for active_plugins["groups_to_roles"], however it doesn't
        # take into account the old config mentioned below.
        group_specs = cast(list[Any], value)

        for group_spec in group_specs:
            if isinstance(group_spec, str):
                dn = group_spec  # be compatible to old config without connection spec
            elif not isinstance(group_spec, tuple):
                continue  # skip non configured ones (old valuespecs allowed None)
            else:
                dn = group_spec[0]

            if dn.lower() not in ldap_groups:
                return False, _('Could not find the group "%s" specified for role %s') % (
                    strip_tags(dn),
                    role_id,
                )

            num_groups += 1
    return True, _("Found all %d groups.") % num_groups
