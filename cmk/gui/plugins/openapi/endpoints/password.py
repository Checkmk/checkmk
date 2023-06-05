#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Passwords

Passwords intended for authentication of certain checks can be stored in the Checkmk
password store. You can use in a rule a password stored in the password store without knowing or
entering the password.
"""

from collections.abc import Mapping
from typing import Any, cast

from cmk.utils import version

from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer, update_customer_info
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_ID_FIELD
from cmk.gui.plugins.openapi.utils import problem, serve_json
from cmk.gui.watolib.passwords import (
    load_password,
    load_password_to_modify,
    load_passwords,
    Password,
    remove_password,
    save_password,
)

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


@Endpoint(
    constructors.collection_href("password"),
    "cmk/create",
    method="post",
    request_schema=request_schemas.InputPassword,
    etag="output",
    response_schema=response_schemas.PasswordObject,
    permissions_required=RW_PERMISSIONS,
)
def create_password(params: Mapping[str, Any]) -> Response:
    """Create a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    body = params["body"]
    ident = body["ident"]
    password_details = cast(
        Password,
        {
            k: v
            for k, v in body.items()
            if k
            not in (
                "ident",
                "owned_by",
                "customer",
            )
        },
    )
    if version.is_managed_edition():
        password_details = update_customer_info(password_details, body["customer"])
    password_details["owned_by"] = None if body["owned_by"] == "admin" else body["owned_by"]
    save_password(ident, password_details, new_password=True)
    return _serve_password(ident, load_password(ident))


@Endpoint(
    constructors.object_href("password", "{name}"),
    ".../update",
    method="put",
    path_params=[NAME_ID_FIELD],
    request_schema=request_schemas.UpdatePassword,
    etag="both",
    response_schema=response_schemas.PasswordObject,
    permissions_required=RW_PERMISSIONS,
)
def update_password(params: Mapping[str, Any]) -> Response:
    """Update a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    body = params["body"]
    ident = params["name"]
    try:
        password_details = load_password_to_modify(ident)
    except KeyError:
        return problem(
            status=404,
            title=f'Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details.update(body)
    save_password(ident, password_details)
    return _serve_password(ident, load_password(ident))


@Endpoint(
    constructors.object_href("password", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_ID_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_password(params: Mapping[str, Any]) -> Response:
    """Delete a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    ident = params["name"]
    if ident not in load_passwords():
        return problem(
            status=404,
            title='Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    remove_password(ident)
    return Response(status=204)


@Endpoint(
    constructors.object_href("password", "{name}"),
    "cmk/show",
    method="get",
    path_params=[NAME_ID_FIELD],
    response_schema=response_schemas.PasswordObject,
    permissions_required=PERMISSIONS,
)
def show_password(params: Mapping[str, Any]) -> Response:
    """Show a password"""
    user.need_permission("wato.passwords")
    ident = params["name"]
    passwords = load_passwords()
    if ident not in passwords:
        return problem(
            status=404,
            title=f'Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details = passwords[ident]
    return _serve_password(ident, password_details)


@Endpoint(
    constructors.collection_href("password"),
    ".../collection",
    method="get",
    response_schema=response_schemas.PasswordCollection,
    permissions_required=PERMISSIONS,
)
def list_passwords(params: Mapping[str, Any]) -> Response:
    """Show all passwords"""
    user.need_permission("wato.passwords")
    return serve_json(
        constructors.collection_object(
            domain_type="password",
            value=[
                serialize_password(ident, details) for ident, details in load_passwords().items()
            ],
        )
    )


def _serve_password(ident, password_details):
    response = serve_json(serialize_password(ident, complement_customer(password_details)))
    return constructors.response_with_etag_created_from_dict(response, password_details)


def serialize_password(ident, details):
    if details["owned_by"] is None:
        details["owned_by"] = "admin"
    return constructors.domain_object(
        domain_type="password",
        identifier=ident,
        title=details["title"],
        members={
            "title": constructors.object_property(
                name="title",
                value=details["title"],
                prop_format="string",
                base=constructors.object_href("password", ident),
            )
        },
        extensions={
            k: v
            for k, v in complement_customer(details).items()
            if k
            in (
                "comment",
                "docu_url",
                "owned_by",
                "shared_with",
                "customer",
            )
        },
        editable=True,
        deletable=True,
    )
