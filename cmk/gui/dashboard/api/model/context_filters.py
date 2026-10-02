#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from pydantic import Discriminator

from cmk.gui.dashboard.type_defs import ContextFilterConfig
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


def host_filter_from_internal(config: ContextFilterConfig) -> AggregateHostContextFilter:
    match config["filter_id"]:
        case "siteopt":
            return SiteContextFilter(filter_id="siteopt")
        case "wato_folder":
            return WatoFolderContextFilter(filter_id="wato_folder")
        case "hoststate":
            return HostStateContextFilter(filter_id="hoststate")
        case "opthostgroup":
            return HostGroupContextFilter(filter_id="opthostgroup")
        case other:
            raise ValueError(f"Not a host context filter: {other!r}")


def service_filter_from_internal(config: ContextFilterConfig) -> AggregateServiceContextFilter:
    match config["filter_id"]:
        case "svcstate":
            return ServiceStateContextFilter(filter_id="svcstate")
        case "optservicegroup":
            return ServiceGroupContextFilter(filter_id="optservicegroup")
        case _:
            return host_filter_from_internal(config)
