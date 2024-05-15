#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.api_error import ApiError

from cmk import fields


class GETLdapConnection404(ApiError):
    status = fields.Integer(
        description="The HTTP status code.",
        example=404,
    )
    detail = fields.String(
        description="Detailed information on what exactly went wrong.",
        example="The connection id LDAP_1 did not match any LDAP connection",
    )
    title = fields.String(
        description="A summary of the problem.",
        example="The requested LDAP connection was not found",
    )
