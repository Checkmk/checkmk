#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

USER_CONFIG_FAMILY = EndpointFamily(
    name="Users",
    description=(
        """

Checkmk usually manages its own users, but you can also connect to external user management
systems like LDAP. The following endpoints provide a way to manage users and trigger a
synchronization of all configured user connections.

"""
    ),
    doc_group="Setup",
)
