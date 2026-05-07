#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import sites
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts
from cmk.livestatus_client.types import Column

from ._family import HOST_STATUS_FAMILY
from ._utils import (
    contains_inventory_column,
    fixup_inventory_column,
    host_object,
    PERMISSIONS,
)
from .models.request_models import ListHostsBody
from .models.response_models import HostStatusCollectionModel


def list_hosts_v1(
    body: ListHostsBody,
) -> HostStatusCollectionModel:
    """Show hosts of specific condition"""
    live = sites.live()
    if body.sites:
        live.only_sites = body.sites

    columns: list[Column] = body.columns if body.columns is not None else [Hosts.name]
    q = Query(columns)

    if body.query is not None:
        q = q.filter(body.query)

    result = q.iterate(live)

    if contains_inventory_column(columns):
        result = fixup_inventory_column(result)

    return HostStatusCollectionModel(
        domainType="host",
        id="host",
        links=[
            LinkModel(
                rel="self",
                href=collection_href("host"),
                domainType="link",
                method="GET",
                type="application/json",
            )
        ],
        value=[host_object(entry["name"], entry) for entry in result],
    )


ENDPOINT_LIST_HOSTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("host"),
        link_relation="cmk/list",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(
        family=HOST_STATUS_FAMILY.name,
        exclude_in_targets={"swagger-ui"},
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=list_hosts_v1)},
)
