#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

LDAP_CONNECTION_FAMILY = EndpointFamily(
    name="LDAP Connections",
    description=(
        """

Checkmk provides a facility for using LDAP-based services for managing users, automatically
synchronizing users from the home directories, and for assigning contact groups, roles and
other attributes to these users in Checkmk automatically. Checkmk is not restricted to a
single LDAP source, and it can also distribute the users to other connected sites if required.

The following endpoints provide a way to manage LDAP connections via the REST-API in the
same way the user interface does. This includes creating, updating, deleting and listing LDAP
connections as well as testing a configured connection and triggering a user synchronization.

If you need help during configuration or experience problems, please refer to the LDAP
Documentation: https://docs.checkmk.com/latest/en/ldap.html.

"""
    ),
    doc_group="Setup",
)
