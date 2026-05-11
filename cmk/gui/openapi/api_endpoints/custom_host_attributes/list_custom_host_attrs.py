#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.custom_host_attributes._family import CUSTOM_HOST_ATTR_FAMILY
from cmk.gui.openapi.api_endpoints.custom_host_attributes._utils import (
    DOMAIN_TYPE,
    PERMISSIONS,
    serialize_attr,
)
from cmk.gui.openapi.api_endpoints.custom_host_attributes.models.response_models import (
    CustomHostAttrCollection,
)
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
from cmk.gui.watolib.custom_attributes import load_custom_attrs_from_mk_file


def list_custom_host_attrs_v1() -> CustomHostAttrCollection:
    """List all custom host attributes"""
    user.need_permission("wato.custom_attributes")
    all_attrs = load_custom_attrs_from_mk_file(lock=False)
    return CustomHostAttrCollection(
        id=DOMAIN_TYPE,
        domainType=DOMAIN_TYPE,
        value=[serialize_attr(attr) for attr in all_attrs["host"]],
        links=[LinkModel.create("self", collection_href(DOMAIN_TYPE))],
    )


ENDPOINT_LIST_CUSTOM_HOST_ATTRS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href(DOMAIN_TYPE),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=CUSTOM_HOST_ATTR_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_custom_host_attrs_v1)},
)
