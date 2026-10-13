#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""On-demand object lookups the Maps SPA's drawer and editor pickers need.

Thin wrappers around :mod:`cmk.maps.gui._object_queries`, which owns the
livestatus/Setup reads (this layer may not talk to livestatus itself).
"""

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href, object_href
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.maps.gui._object_queries import (
    dyngroup_members,
    folder_choices,
    group_members,
    host_geo,
    Member,
    perf_metrics,
    site_choices,
)
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.response_models import (
    MapsFolder,
    MapsFoldersResponse,
    MapsGeoCoordinates,
    MapsHostGeoResponse,
    MapsMember,
    MapsMembersResponse,
    MapsPerfMetricsResponse,
    MapsSite,
    MapsSitesResponse,
)
from cmk.maps.rest_api.utils import LIVESTATUS_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

_LIVESTATUS_LOOKUP_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), *LIVESTATUS_PERMISSIONS]
)
# The folder list widens to every folder with ``wato.see_all_folders``.
_FOLDER_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), permissions.Optional(permissions.Perm("wato.see_all_folders"))]
)


def _members_response(members: list[Member]) -> MapsMembersResponse:
    return MapsMembersResponse(
        members=[
            MapsMember(
                host=member.host,
                service=member.service,
                state=member.state,
                output=member.output,
                acknowledged=member.acknowledged,
                in_downtime=member.in_downtime,
                notifications_enabled=member.notifications_enabled,
                last_state_change=member.last_state_change,
            )
            for member in members
        ]
    )


def show_host_geo_v1(
    host_name: Annotated[
        str,
        PathParam(description="The host to resolve coordinates for.", example="heute"),
    ],
) -> MapsHostGeoResponse:
    """Show a host's map coordinates"""
    user.need_permission("maps.use")
    coords = host_geo(host_name)
    return MapsHostGeoResponse(
        geo=None if coords is None else MapsGeoCoordinates(lat=coords.lat, lng=coords.lng)
    )


def show_perf_metrics_v1(
    host_name: Annotated[
        str,
        QueryParam(description="The host the perfdata belongs to.", example="heute"),
    ],
    service_description: Annotated[
        str | None,
        QueryParam(
            description="The service to read perfdata from; omit for host perfdata.",
            example="CPU load",
        ),
    ] = None,
) -> MapsPerfMetricsResponse:
    """Show an object's raw perfdata"""
    user.need_permission("maps.use")
    source = perf_metrics(host_name, service_description)
    return MapsPerfMetricsResponse(
        perf_data=source.perf_data,
        check_command=source.check_command,
        metrics=source.metrics,
    )


def list_group_members_v1(
    group_type: Annotated[
        str,
        QueryParam(description="Either hostgroup or servicegroup.", example="hostgroup"),
    ],
    group_name: Annotated[
        str,
        QueryParam(description="The group to list members of.", example="linux"),
    ],
) -> MapsMembersResponse:
    """Show a group's members"""
    user.need_permission("maps.use")
    return _members_response(group_members(group_type, group_name))


def list_dyngroup_members_v1(
    object_filter: Annotated[
        str,
        QueryParam(
            description="One or more Livestatus ``Filter:`` lines defining the dyngroup.",
            example="Filter: name ~~ web\n",
        ),
    ],
    object_types: Annotated[
        str,
        QueryParam(description="Either host or service.", example="host"),
    ] = "host",
) -> MapsMembersResponse:
    """Show a dyngroup's members"""
    user.need_permission("maps.use")
    return _members_response(dyngroup_members(object_types, object_filter))


def list_folders_v1(api_context: ApiContext) -> MapsFoldersResponse:
    """Show the Setup folders"""
    user.need_permission("maps.use")
    return MapsFoldersResponse(
        folders=[
            MapsFolder(path=choice.path, title=choice.title)
            for choice in folder_choices(make_folder_tree(api_context.config))
        ]
    )


def list_sites_v1() -> MapsSitesResponse:
    """Show the monitoring sites"""
    user.need_permission("maps.use")
    return MapsSitesResponse(
        sites=[MapsSite(site_id=choice.site_id, alias=choice.alias) for choice in site_choices()]
    )


ENDPOINT_SHOW_HOST_GEO = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("maps_host_geo", "{host_name}"),
        link_relation="cmk/show_maps_host_geo",
        method="get",
    ),
    permissions=EndpointPermissions(required=_LIVESTATUS_LOOKUP_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_host_geo_v1)},
)

ENDPOINT_SHOW_PERF_METRICS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_perf_metrics"),
        link_relation="cmk/show_maps_perf_metrics",
        method="get",
    ),
    permissions=EndpointPermissions(required=_LIVESTATUS_LOOKUP_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_perf_metrics_v1)},
)

# Two collections of the same domain type: the members are the same shape, only
# the way of naming the set differs (a configured group vs. an ad-hoc filter).
ENDPOINT_LIST_GROUP_MEMBERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_member", "group"),
        link_relation="cmk/list_maps_group_members",
        method="get",
    ),
    permissions=EndpointPermissions(required=_LIVESTATUS_LOOKUP_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_group_members_v1)},
)

ENDPOINT_LIST_DYNGROUP_MEMBERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_member", "dyngroup"),
        link_relation="cmk/list_maps_dyngroup_members",
        method="get",
    ),
    permissions=EndpointPermissions(required=_LIVESTATUS_LOOKUP_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_dyngroup_members_v1)},
)

ENDPOINT_LIST_FOLDERS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_folder"),
        link_relation="cmk/list_maps_folders",
        method="get",
    ),
    permissions=EndpointPermissions(required=_FOLDER_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_folders_v1)},
)

ENDPOINT_LIST_SITES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_site"),
        link_relation="cmk/list_maps_sites",
        method="get",
    ),
    permissions=EndpointPermissions(required=permissions.Perm("maps.use")),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_sites_v1)},
)
