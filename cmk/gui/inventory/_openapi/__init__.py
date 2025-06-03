#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily, EndpointFamilyRegistry
from cmk.gui.utils import permission_verification as permissions

from ._get_inventory_trees import get_inventory_trees

INVENTORY_FAMILY = EndpointFamily(
    name="HW/SW Inventory",
    description="""
The HW/SW Inventory of a host shows static or dynamic data organized as a tree. The data comes
from different data sources like the Linux agent and is handled by inventory plug-ins.
""",
    doc_group="Monitoring",
)

ENDPOINT_INVENTORY_TREES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("inventory"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.AnyPerm(
            [
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
                permissions.Perm("general.see_all"),
                # only used to check if user can see a host
                permissions.Perm("wato.see_all_folders"),
            ]
        )
    ),
    doc=EndpointDoc(family=INVENTORY_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=get_inventory_trees)},
)


def register(
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    *,
    ignore_duplicates: bool,
) -> None:
    endpoint_family_registry.register(INVENTORY_FAMILY, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(
        ENDPOINT_INVENTORY_TREES, ignore_duplicates=ignore_duplicates
    )
