#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from pydantic import Discriminator, StringConstraints, TypeAdapter

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.type_defs import ContextFilterConfig


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


@api_model
class HostAttributeContextFilter:
    filter_id: Literal[
        "site",
        "host_check_command_exact",
        "host_ctc",
        "opthost_contactgroup",
        "host_address",
        "host_ipv4_address",
        "host_ipv6_address",
        "hst_service_level",
        "kubernetes_cluster",
        "kubernetes_namespace",
        "kubernetes_node",
        "kubernetes_deployment",
        "kubernetes_daemonset",
        "kubernetes_statefulset",
        "azure_resource_group",
        "azure_subscription_name",
        "azure_subscription",
    ] = api_field(description="An attribute of the clicked host, carried by this filter.")


@api_model
class ServiceAttributeContextFilter:
    filter_id: Literal[
        "svchardstate",
        "service_state_type",
        "service_staleness",
        "check_command_exact",
        "service_ctc",
        "optservice_contactgroup",
        "svc_service_level",
    ] = api_field(description="An attribute of the clicked service, carried by this filter.")


_Key = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@api_model
class _KeyedContextFilter:
    key: _Key = api_field(
        description="The label key, tag group or auxiliary tag whose value the link carries."
    )


@api_model
class HostLabelContextFilter(_KeyedContextFilter):
    filter_id: Literal["host_labels"] = api_field(description="A label of the clicked host.")


@api_model
class HostTagContextFilter(_KeyedContextFilter):
    filter_id: Literal["host_tags"] = api_field(description="A tag of the clicked host.")


@api_model
class HostAuxTagContextFilter(_KeyedContextFilter):
    filter_id: Literal["host_auxtags"] = api_field(
        description="An auxiliary tag the clicked host has."
    )


@api_model
class ServiceLabelContextFilter(_KeyedContextFilter):
    filter_id: Literal["service_labels"] = api_field(description="A label of the clicked service.")


@api_model
class ServiceTagContextFilter(_KeyedContextFilter):
    filter_id: Literal["service_tags"] = api_field(description="A tag of the clicked service.")


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

_ObjectHostFilters = (
    _AggregateHostFilters
    | HostNameContextFilter
    | HostAttributeContextFilter
    | HostLabelContextFilter
    | HostTagContextFilter
    | HostAuxTagContextFilter
)

# A click that yields one host: every aggregate member, plus the host's name, attributes, labels
# and tags.
type ObjectHostContextFilter = Annotated[_ObjectHostFilters, Discriminator("filter_id")]

# A click that yields one service, which also carries its host's filters.
type ObjectServiceContextFilter = Annotated[
    _ObjectHostFilters
    | ServiceStateContextFilter
    | ServiceGroupContextFilter
    | ServiceNameContextFilter
    | ServiceAttributeContextFilter
    | ServiceLabelContextFilter
    | ServiceTagContextFilter,
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


def context_filter_to_internal(context_filter: ObjectServiceContextFilter) -> ContextFilterConfig:
    """The stored form of a filter of any set. Typed as the service object's filters, which
    hold every other set's."""
    if isinstance(context_filter, _KeyedContextFilter):
        return ContextFilterConfig(filter_id=context_filter.filter_id, key=context_filter.key)
    return ContextFilterConfig(filter_id=context_filter.filter_id)
