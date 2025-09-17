#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.data_source.registry import data_source_registry
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

from ._family import DATA_SOURCE_FAMILY


@api_model
class DataSourceExtensions:
    infos: list[str] = api_field(description="List of infos provided by the data source.")


@api_model
class DataSourceModel(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")
    extensions: DataSourceExtensions = api_field(
        description="The configuration of this data source."
    )


@api_model
class DataSourceCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["constant"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[DataSourceModel] = api_field(description="A list of host objects", example="")


def list_data_sources_v1() -> DataSourceCollectionModel:
    """List data sources."""
    data_sources = []
    for data_source_id, data_source_class in data_source_registry.items():
        data_source = data_source_class()
        data_source_model = DataSourceModel(
            id=data_source_id,
            domainType="constant",
            title=data_source.title,
            extensions=DataSourceExtensions(infos=list(data_source.infos)),
            links=[],
        )

        data_sources.append(data_source_model)

    return DataSourceCollectionModel(
        id="data_sources", domainType="constant", links=[], value=data_sources
    )


ENDPOINT_LIST_DATA_SOURCES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_object_collection_href("constant", "data_source", "all"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=DATA_SOURCE_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_data_sources_v1)},
)
