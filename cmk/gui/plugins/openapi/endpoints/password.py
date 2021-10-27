#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Passwords

Passwords intended for authentication of certain checks can be stored in the Checkmk
password store. You can use in a rule a password stored in the password store without knowing or
entering the password.
"""

import json
from typing import cast

from cmk.utils import version

from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer, update_customer_info
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.watolib.passwords import (
    load_password,
    load_password_to_modify,
    load_passwords,
    Password,
    remove_password,
    save_password,
)


@Endpoint(
    constructors.collection_href("password"),
    "cmk/create",
    method="post",
    request_schema=request_schemas.InputPassword,
    etag="output",
    response_schema=response_schemas.PasswordObject,
)
def create_password(params):
    """Create a password"""
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
    path_params=[NAME_FIELD],
    request_schema=request_schemas.UpdatePassword,
    etag="both",
    response_schema=response_schemas.PasswordObject,
)
def update_password(params):
    """Update a password"""
    body = params["body"]
    ident = params["name"]
    try:
        password_details = load_password_to_modify(ident)
    except KeyError:
        return problem(
            404,
            f'Password "{ident}" is not known.',
            "The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details.update(body)
    save_password(ident, password_details)
    return _serve_password(ident, load_password(ident))


@Endpoint(
    constructors.object_href("password", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_FIELD],
    output_empty=True,
)
def delete_password(params):
    """Delete a password"""
    ident = params["name"]
    if ident not in load_passwords():
        return problem(
            404,
            f'Password "{ident}" is not known.',
            "The password you asked for is not known. Please check for eventual misspellings.",
        )
    remove_password(ident)
    return Response(status=204)


@Endpoint(
    constructors.object_href("password", "{name}"),
    "cmk/show",
    method="get",
    path_params=[NAME_FIELD],
    response_schema=response_schemas.PasswordObject,
)
def show_password(params):
    """Show a password"""
    ident = params["name"]
    passwords = load_passwords()
    if ident not in passwords:
        return problem(
            404,
            f'Password "{ident}" is not known.',
            "The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details = passwords[ident]
    return _serve_password(ident, password_details)


@Endpoint(
    constructors.collection_href("password"),
    ".../collection",
    method="get",
    response_schema=response_schemas.DomainObjectCollection,
)
def list_passwords(params):
    """Show all passwords"""
    password_collection = {
        "id": "password",
        "domainType": "password",
        "value": [
            constructors.collection_item(
                domain_type="password",
                title=details["title"],
                identifier=password_id,
            )
            for password_id, details in load_passwords().items()
        ],
        "links": [constructors.link_rel("self", constructors.collection_href("password"))],
    }
    return constructors.serve_json(password_collection)


def _serve_password(ident, password_details):
    response = Response()
    response.set_data(json.dumps(serialize_password(ident, complement_customer(password_details))))
    response.set_content_type("application/json")
    response.headers.add("ETag", constructors.etag_of_dict(password_details).to_header())
    return response


def serialize_password(ident, details):
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
                "password",
                "owned_by",
                "shared_with",
                "customer",
            )
        },
    )
