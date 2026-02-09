#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
    LinkModel,
)
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.utils import permission_verification as permissions

from .._base import FilterGroup
from ._family import VISUAL_FILTER_FAMILY

_FILTER_GROUP_TITLES: Mapping[FilterGroup, str] = {
    FilterGroup.INVENTORY: "Inventory",
    FilterGroup.FOLDER: "Folder",
    FilterGroup.HOST_HAS: "Host has",
    FilterGroup.HOST_ADDRESS: "Host address",
    FilterGroup.HOST_CHECK_COMMAND: "Host check command",
    FilterGroup.HOST_CONTACT: "Host contact",
    FilterGroup.HOST_IN: "Host in",
    FilterGroup.HOST_IS: "Host is",
    FilterGroup.HOST_NAME: "Host name",
    FilterGroup.HOST_STATE: "Host state",
    FilterGroup.KUBERNETES: "Kubernetes",
    FilterGroup.SITE: "Site",
    FilterGroup.TOPOLOGY: "Topology",
    FilterGroup.SERVICE_NAME: "Service name",
    FilterGroup.SERVICE_CHECK_COMMAND: "Service check command",
    FilterGroup.SERVICE_CONTACT: "Service contact",
    FilterGroup.SERVICE_IN: "Service in",
    FilterGroup.SERVICE_IS: "Service is",
    FilterGroup.SERVICE_STATE: "Service state",
}


@dataclass(kw_only=True, slots=True)
class FilterGroupDomainObject(DomainObjectModel):
    domainType: Literal["visual_filter_group"] = api_field(
        description="The domain type of the object."
    )


@dataclass(kw_only=True, slots=True)
class FilterGroupCollection(DomainObjectCollectionModel):
    domainType: Literal["visual_filter_group"] = api_field(
        description="The domain type of the objects in the collection.",
        example="visual_filter_group",
    )
    value: list[FilterGroupDomainObject] = api_field(
        description="A list of filter groups.", example=[{}]
    )


def list_filter_groups_v1() -> FilterGroupCollection:
    """Show all filter groups."""
    return FilterGroupCollection(
        domainType="visual_filter_group",
        id="all",
        extensions=ApiOmitted(),
        links=[LinkModel.create("self", collection_href("visual_filter_group"))],
        value=[
            FilterGroupDomainObject(
                domainType="visual_filter_group",
                id=group.value,
                title=title,
                links=[],
            )
            for group, title in _FILTER_GROUP_TITLES.items()
        ],
    )


ENDPOINT_LIST_FILTER_GROUPS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("visual_filter_group"),
        link_relation="cmk/list_filter_groups",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(permissions.Perm("general.see_all"))
    ),
    doc=EndpointDoc(family=VISUAL_FILTER_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_filter_groups_v1)},
)
