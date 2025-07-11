#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

USER_ROLE_FAMILY = EndpointFamily(
    name="User Roles",
    description=(
        """

User Roles

Checkmk always assigns permissions to users via roles — never directly. A role is nothing more than a list of permissions.
It is important that you understand that roles define the level of permissions and not the reference to any hosts or services.
That is what contact groups are for.

As standard Checkmk comes with the following three predefined roles, which can never be deleted, but can be customised at will:

When adding a new custom role, it will be a clone of one of the default roles, i.e it will automatically inherit all of the
permissions of that default role.  Also, when new permissions are added, built-in roles will automatically be permitted or not
permitted and the custom roles will also inherit those permission settings.

* Role: admin
Permissions:  All permissions - especially the right to change permissions.
Function: The Checkmk administrator who is in charge of the monitoring system itself.

* Role: user
Permissions: May only see their own hosts and services, may only make changes in the web interface in folders
authorized for them and generally may not do anything that affects other users.
Function: The normal Checkmk user who uses monitoring and responds to notifications.

* Role: guest
Permissions: May see everything but not change anything.
Function: 'Guest' is intended simply for 'watching', with all guests sharing a common account.
For example, useful for public status monitors hanging on a wall.


"""
    ),
    doc_group="Setup",
)
