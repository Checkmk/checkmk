#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
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

from .._base import Filter
from .._registry import filter_registry
from ._family import VISUAL_FILTER_FAMILY
from ._model import filter_component_from_internal, FilterComponentModel


@dataclass(kw_only=True, slots=True)
class FilterExtensions:
    info: str = api_field(
        description="For which type of object this filter is applicable.",
    )
    description: str | ApiOmitted = api_field(
        description="Description for this filter.", default_factory=ApiOmitted
    )
    is_show_more: bool = api_field(description="Whether the filter is normally hidden.")
    components: list[FilterComponentModel] = api_field(
        description="The components of the filter, e.g. dropdowns, checkboxes, etc.",
    )


@dataclass(kw_only=True, slots=True)
class FilterDomainObject(DomainObjectModel):
    domainType: Literal["visual_filter"] = api_field(description="The domain type of the object.")
    extensions: FilterExtensions = api_field(description="All the data and metadata of this host.")


@dataclass(kw_only=True, slots=True)
class FilterCollection(DomainObjectCollectionModel):
    domainType: Literal["visual_filter"] = api_field(
        description="The domain type of the objects in the collection",
        example="visual_filter",
    )
    # TODO: add proper example
    value: list[FilterDomainObject] = api_field(
        description="A list of filter configurations.", example=[{}]
    )


def _filter_sort_key(value: tuple[str, Filter]) -> tuple[int, str]:
    return value[1].sort_index, value[1].title


def _iter_filter_models() -> Iterable[FilterDomainObject]:
    """Iterate over all filter models in the registry, correctly sorted."""
    for filter_name, filter_object in sorted(filter_registry.items(), key=_filter_sort_key):
        try:
            components = filter_object.components()
        except NotImplementedError:
            continue
        yield FilterDomainObject(
            domainType="visual_filter",
            id=filter_name,
            title=filter_object.title,
            extensions=FilterExtensions(
                info=filter_object.info,
                description=ApiOmitted.from_optional(filter_object.description),
                is_show_more=filter_object.is_show_more,
                components=[filter_component_from_internal(component) for component in components],
            ),
            links=[],
        )


def list_filters_v1() -> FilterCollection:
    """Show all filter configurations."""
    return FilterCollection(
        domainType="visual_filter",
        id="all",
        extensions=ApiOmitted(),
        value=list(_iter_filter_models()),
        links=[LinkModel.create("self", collection_href("visual_filter"))],
    )


ENDPOINT_LIST_FILTERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("visual_filter"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(
            permissions.AllPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.Perm("bi.see_all"),
                    permissions.Perm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=VISUAL_FILTER_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_filters_v1)},
)
