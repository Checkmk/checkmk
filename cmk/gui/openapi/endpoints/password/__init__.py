#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, cast

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.password_store import Password

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.password.request_schemas import InputPassword, UpdatePassword
from cmk.gui.openapi.endpoints.password.response_schemas import PasswordCollection, PasswordObject
from cmk.gui.openapi.endpoints.utils import (
    complement_customer,
    mutually_exclusive_fields,
    update_customer_info,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily, EndpointFamilyRegistry
from cmk.gui.openapi.restful_objects.parameters import NAME_ID_FIELD
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.passwords import (
    load_password,
    load_password_to_modify,
    load_passwords,
    remove_password,
    save_password,
)

PASSWORD_FAMILY = EndpointFamily(
    name="Passwords",
    description=(
        """
Passwords intended for authentication of certain checks can be stored in the Checkmk
password store. You can use a stored password in a rule without knowing or entering
the password.

These endpoints provide a way to manage stored passwords via the REST-API in the
same way the user interface does. This includes being able to create, update and delete
stored passwords. You are also able to fetch a list of passwrods or individual passwords,
however, the password itself is not returned for security reasons.
"""
    ),
    doc_group="Setup",
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
    request_schema=InputPassword,
    etag="output",
    response_schema=PasswordObject,
    permissions_required=RW_PERMISSIONS,
    family_name=PASSWORD_FAMILY.name,
)
def create_password(params: Mapping[str, Any]) -> Response:
    """Create a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    body = params["body"]
    ident = body["ident"]
    password_details = {
        k: v
        for k, v in body.items()
        if k
        not in (
            "ident",
            "owned_by",
            "editable_by",
            "customer",
        )
    }
    if version.edition(paths.omd_root) is version.Edition.CME:
        password_details = update_customer_info(password_details, body["customer"])
    password_details["owned_by"] = mutually_exclusive_fields(
        str, body, "owned_by", "editable_by", default="admin"
    )
    save_password(
        ident,
        cast(Password, password_details),
        new_password=True,
        user_id=user.id,
        pprint_value=active_config.wato_pprint_config,
        use_git=active_config.wato_use_git,
    )
    return _serve_password(ident, load_password(ident))


@Endpoint(
    constructors.object_href("password", "{name}"),
    ".../update",
    method="put",
    path_params=[NAME_ID_FIELD],
    request_schema=UpdatePassword,
    etag="both",
    response_schema=PasswordObject,
    permissions_required=RW_PERMISSIONS,
    family_name=PASSWORD_FAMILY.name,
)
def update_password(params: Mapping[str, Any]) -> Response:
    """Update a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    body = params["body"]
    ident = params["name"]

    owned_by = mutually_exclusive_fields(str, body, "owned_by", "editable_by")
    body.pop("editable_by", None)
    if owned_by is not None:
        body["owned_by"] = owned_by
    try:
        password_details = load_password_to_modify(ident)
    except KeyError:
        return problem(
            status=404,
            title=f'Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details.update(body)
    save_password(
        ident,
        password_details,
        new_password=False,
        user_id=user.id,
        pprint_value=active_config.wato_pprint_config,
        use_git=active_config.wato_use_git,
    )
    return _serve_password(ident, load_password(ident))


@Endpoint(
    constructors.object_href("password", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_ID_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[400],
    family_name=PASSWORD_FAMILY.name,
)
def delete_password(params: Mapping[str, Any]) -> Response:
    """Delete a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    ident = params["name"]
    if password := load_passwords().get(ident):
        if is_locked_by_quick_setup(password.get("locked_by")):
            return problem(
                status=400,
                title=f'The password "{ident}" is locked by Quick setup.',
                detail="Locked passwords cannot be removed.",
            )
    else:
        return problem(
            status=404,
            title=f'Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    remove_password(
        ident,
        user_id=user.id,
        pprint_value=active_config.wato_pprint_config,
        use_git=active_config.wato_use_git,
    )
    return Response(status=204)


@Endpoint(
    constructors.object_href("password", "{name}"),
    "cmk/show",
    method="get",
    etag="output",
    path_params=[NAME_ID_FIELD],
    response_schema=PasswordObject,
    permissions_required=PERMISSIONS,
    family_name=PASSWORD_FAMILY.name,
)
def show_password(params: Mapping[str, Any]) -> Response:
    """Show password store entry"""
    user.need_permission("wato.passwords")
    ident = params["name"]
    passwords = load_passwords()
    if ident not in passwords:
        return problem(
            status=404,
            title=f'Password "{ident}" is not known.',
            detail="The password you asked for is not known. Please check for eventual misspellings.",
        )
    password_details: Password = passwords[ident]
    return _serve_password(ident, password_details)


@Endpoint(
    constructors.collection_href("password"),
    ".../collection",
    method="get",
    response_schema=PasswordCollection,
    permissions_required=PERMISSIONS,
    family_name=PASSWORD_FAMILY.name,
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


def _serve_password(ident: str, password_details: Password) -> Response:
    response = serve_json(serialize_password(ident, complement_customer(password_details)))
    password_as_dict = cast(dict[str, Any], password_details)
    return constructors.response_with_etag_created_from_dict(response, password_as_dict)


def serialize_password(ident: str, details: Password) -> DomainObject:
    if details["owned_by"] is None:
        details["owned_by"] = "admin"

    return constructors.domain_object(
        domain_type="password",
        identifier=ident,
        title=details["title"],
        members={},
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


def register(
    endpoint_family_registry: EndpointFamilyRegistry,
    endpoint_registry: EndpointRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(PASSWORD_FAMILY, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_password, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_password, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_password, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_password, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_passwords, ignore_duplicates=ignore_duplicates)
