#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.restful_objects.constructors import domain_object_collection_href
from cmk.gui.visuals.filter.api import filter_component_from_internal, FilterComponentModel

from .._registry import visual_info_registry
from ._family import VISUAL_INFO_FAMILY


@api_model
class VisualInfoExtensions:
    sort_index: int = api_field(
        description="The sort index of this info. Infos are sorted ascending by this index."
    )
    single_filter: list[FilterComponentModel] = api_field(
        description="Filter components to use when filtering for one item."
    )


@api_model
class VisualInfoModel(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")
    extensions: VisualInfoExtensions = api_field(description="The configuration of this info.")


@api_model
class VisualInfoCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["constant"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[VisualInfoModel] = api_field(description="A list of info objects", example="")


def list_infos_v1() -> VisualInfoCollectionModel:
    """List infos."""
    infos = []
    for info_id, info_class in visual_info_registry.items():
        info = info_class()
        data_source_model = VisualInfoModel(
            id=info_id,
            domainType="constant",
            title=info.title,
            extensions=VisualInfoExtensions(
                sort_index=info.sort_index,
                single_filter=[
                    filter_component_from_internal(component)
                    for component in info.single_spec_components()
                ],
            ),
            links=[],
        )

        infos.append(data_source_model)

    return VisualInfoCollectionModel(
        id="visual_infos", domainType="constant", links=[], value=infos
    )


ENDPOINT_LIST_INFOS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_object_collection_href("constant", "visual_info", "all"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=VISUAL_INFO_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_infos_v1)},
)
