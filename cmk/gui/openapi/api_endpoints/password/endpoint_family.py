#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

PASSWORD_FAMILY = EndpointFamily(
    name="Passwords",
    description=(
        """
Passwords intended for authentication of certain checks can be stored in the Checkmk
password store. You can use a stored password in a rule without knowing or entering
the password.

These endpoints provide a way to manage stored passwords via the REST-API in the
same way the user interface does. This includes being able to create, update and delete
stored passwords. You are also able to fetch a list of passwords or individual passwords,
however, the password itself is not returned for security reasons.
"""
    ),
    doc_group="Setup",
)
