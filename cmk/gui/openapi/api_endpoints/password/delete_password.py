#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import AfterValidator

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import PasswordConverter
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.passwords import load_password_to_modify, remove_password

from .endpoint_family import PASSWORD_FAMILY
from .utils import password_etag, RW_PERMISSIONS


def delete_password_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        AfterValidator(PasswordConverter.exists),
        PathParam(
            description="A name used as an identifier. Can be of arbitrary (sensible) length.",
            example="pathname",
        ),
    ],
) -> None:
    """Delete a password"""
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")
    password = load_password_to_modify(name)
    if api_context.etag.enabled:
        api_context.etag.verify(password_etag(name, password))

    if is_locked_by_quick_setup(password.get("locked_by")):
        raise RestAPIRequestGeneralException(
            status=400,
            title=f'The password "{name}" is locked by Quick setup.',
            detail="Locked passwords cannot be removed.",
        )

    remove_password(
        name,
        user_id=user.id,
        pprint_value=api_context.config.wato_pprint_config,
        use_git=api_context.config.wato_use_git,
    )


ENDPOINT_DELETE_PASSWORD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("password", "{name}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=PASSWORD_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=delete_password_v1)},
    behavior=EndpointBehavior(etag="input"),
)
