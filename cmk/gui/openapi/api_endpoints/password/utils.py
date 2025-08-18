#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.api_endpoints.password.models.response_models import (
    PasswordExtension,
    PasswordObject,
)
from cmk.gui.openapi.endpoints.utils import complement_customer
from cmk.gui.openapi.framework import ETag
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.utils import permission_verification as permissions
from cmk.utils.password_store import Password

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.passwords"),
        permissions.Optional(permissions.Perm("wato.edit_all_passwords")),
    ]
)

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.passwords"),
        permissions.Optional(permissions.Perm("wato.edit_all_passwords")),
    ]
)


def serialize_password(ident: str, details: Password) -> PasswordObject:
    details = complement_customer(details)
    return PasswordObject(
        domainType="password",
        id=ident,
        title=details["title"],
        extensions=PasswordExtension(
            comment=details.get("comment", ApiOmitted()),
            documentation_url=details.get("docu_url", ApiOmitted()),
            editable_by=details.get("owned_by") or ApiOmitted(),
            owned_by=details.get("owned_by") or ApiOmitted(),
            shared_with=details.get("shared_with", ApiOmitted()),
            customer=details.get("customer") or ApiOmitted(),
        ),
        links=[LinkModel.create("self", object_href("password", "{name}"))],
    )


def password_etag(ident: str, password: Password) -> ETag:
    return ETag(
        {
            "id": ident,
            "title": password["title"],
            "comment": password["comment"],
            "docu_url": password["docu_url"],
            "password": password["password"],
            "owned_by": password["owned_by"],
            "shared_with": password["shared_with"],
            "customer": password.get("customer"),
            "locked_by": password.get("locked_by"),
        }
    )
