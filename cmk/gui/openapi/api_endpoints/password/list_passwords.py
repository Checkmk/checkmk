#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.passwords import load_passwords

from .endpoint_family import PASSWORD_FAMILY
from .models.response_models import PasswordCollection
from .utils import PERMISSIONS, serialize_password


def list_passwords_v1() -> PasswordCollection:
    """Show all passwords"""
    user.need_permission("wato.passwords")
    return PasswordCollection(
        id="password",
        domainType="password",
        value=[serialize_password(ident, details) for ident, details in load_passwords().items()],
        links=[LinkModel.create("self", collection_href("password"))],
    )


ENDPOINT_LIST_PASSWORDS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("password"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=PASSWORD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_passwords_v1)},
)
