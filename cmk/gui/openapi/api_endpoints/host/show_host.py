#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui import sites
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName, columns_validator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts
from cmk.livestatus_client.types import Column

from ._family import HOST_STATUS_FAMILY
from ._utils import (
    contains_inventory_column,
    fixup_inventory_row,
    host_object,
    PERMISSIONS,
)
from .models.response_models import HostStatusObjectModel


def show_host_v1(
    host_name: Annotated[
        AnnotatedHostName,
        PathParam(description="The host name", example="example.com"),
    ],
    columns: Annotated[
        Annotated[list[Column], columns_validator(Hosts, mandatory=[Hosts.name])] | None,
        QueryParam(
            description="The list of columns to include in the response. The `name` column is always included.",
            example="name",
            is_list=True,
        ),
    ] = None,
) -> HostStatusObjectModel:
    """Show host"""
    live = sites.live()

    resolved_columns = columns if columns is not None else [Hosts.name, Hosts.alias, Hosts.address]

    q = Query(
        columns=resolved_columns,
        filter_expr=Hosts.name.op("=", host_name),
    )

    try:
        host = q.fetchone(live)
    except ValueError:
        raise ProblemException(
            status=404,
            title="The requested host was not found",
            detail=f"The host name {host_name} did not match any host",
        )

    if contains_inventory_column(resolved_columns):
        host = fixup_inventory_row(host)

    return host_object(host_name, host)


ENDPOINT_SHOW_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host", "{host_name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(
        family=HOST_STATUS_FAMILY.name,
        exclude_in_targets={"swagger-ui"},
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=show_host_v1)},
)
