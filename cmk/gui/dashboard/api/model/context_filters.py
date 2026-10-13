#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from pydantic import Discriminator, TypeAdapter

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class SiteContextFilter:
    filter_id: Literal["siteopt"] = api_field(description="The site of the clicked element.")


@api_model
class WatoFolderContextFilter:
    filter_id: Literal["wato_folder"] = api_field(description="The folder of the clicked element.")


@api_model
class HostStateContextFilter:
    filter_id: Literal["hoststate"] = api_field(
        description="The host state of the clicked element."
    )


@api_model
class HostGroupContextFilter:
    filter_id: Literal["opthostgroup"] = api_field(
        description="The host group of the clicked element."
    )


@api_model
class HostNameContextFilter:
    filter_id: Literal["host"] = api_field(description="The name of the clicked host.")


@api_model
class ServiceNameContextFilter:
    filter_id: Literal["service"] = api_field(description="The name of the clicked service.")


@api_model
class ServiceStateContextFilter:
    filter_id: Literal["svcstate"] = api_field(
        description="The service state of the clicked element."
    )


@api_model
class ServiceGroupContextFilter:
    filter_id: Literal["optservicegroup"] = api_field(
        description="The service group of the clicked element."
    )


# Plain unions, so that a set built on another one still lists its members flat.
_AggregateHostFilters = (
    SiteContextFilter | WatoFolderContextFilter | HostStateContextFilter | HostGroupContextFilter
)
_AggregateServiceFilters = (
    _AggregateHostFilters | ServiceStateContextFilter | ServiceGroupContextFilter
)

# A click that yields a set of hosts: nothing that names one host.
type AggregateHostContextFilter = Annotated[_AggregateHostFilters, Discriminator("filter_id")]

# A click that yields a set of services, which also carry their hosts' filters.
type AggregateServiceContextFilter = Annotated[_AggregateServiceFilters, Discriminator("filter_id")]

# A click that yields one host: every aggregate member, plus the host itself.
type ObjectHostContextFilter = Annotated[
    _AggregateHostFilters | HostNameContextFilter, Discriminator("filter_id")
]

# A click that yields one service, which also carries its host's filters.
type ObjectServiceContextFilter = Annotated[
    _AggregateServiceFilters | HostNameContextFilter | ServiceNameContextFilter,
    Discriminator("filter_id"),
]


# The stored form of a filter is its API form, so each set reads back through its own union.
AGGREGATE_HOST_FILTER_ADAPTER: TypeAdapter[AggregateHostContextFilter] = TypeAdapter(
    AggregateHostContextFilter
)
AGGREGATE_SERVICE_FILTER_ADAPTER: TypeAdapter[AggregateServiceContextFilter] = TypeAdapter(
    AggregateServiceContextFilter
)
OBJECT_HOST_FILTER_ADAPTER: TypeAdapter[ObjectHostContextFilter] = TypeAdapter(
    ObjectHostContextFilter
)
OBJECT_SERVICE_FILTER_ADAPTER: TypeAdapter[ObjectServiceContextFilter] = TypeAdapter(
    ObjectServiceContextFilter
)
