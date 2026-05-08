#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import downtimes as downtime_commands
from cmk.gui.livestatus_utils.commands.downtimes import QueryException
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.downtime._utils import RW_PERMISSIONS
from cmk.gui.openapi.api_endpoints.downtime.models.request_models import (
    CreateServiceDowntimeModel,
    CreateServiceGroupDowntimeModel,
    CreateServiceQueryDowntimeModel,
)
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.spec.utils import LIVESTATUS_GENERIC_EXPLANATION
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.queries import detailed_connection, Query
from cmk.livestatus_client.tables import Hosts

from ._family import DOWNTIME_FAMILY


def create_service_related_downtime_v1(
    body: Annotated[
        CreateServiceDowntimeModel
        | CreateServiceGroupDowntimeModel
        | CreateServiceQueryDowntimeModel,
        Discriminator("downtime_type"),
    ],
) -> ApiResponse[None]:
    """Create a service related scheduled downtime"""
    live = sites.live()

    match body:
        case CreateServiceDowntimeModel():
            host_name = body.host_name
            with detailed_connection(live) as conn:
                try:
                    site_id = Query(
                        columns=[Hosts.name], filter_expr=Hosts.name.op("=", host_name)
                    ).value(conn)
                except ValueError:
                    # Request user can't see the host (but may still be able to access the service)
                    site_id = None
            downtime_commands.schedule_service_downtime(
                live,
                site_id,
                host_name=host_name,
                service_description=body.service_descriptions,
                start_time=body.start_time,
                end_time=body.end_time,
                recur=body.recur,
                duration=body.duration,
                user_id=user.ident,
                comment=body.comment
                or f"Downtime for services {', '.join(body.service_descriptions)!r}@{host_name!r}",
            )
        case CreateServiceGroupDowntimeModel():
            downtime_commands.schedule_servicegroup_service_downtime(
                live,
                servicegroup_name=body.servicegroup_name,
                start_time=body.start_time,
                end_time=body.end_time,
                recur=body.recur,
                duration=body.duration,
                user_id=user.ident,
                comment=body.comment or f"Downtime for servicegroup {body.servicegroup_name!r}",
            )
        case CreateServiceQueryDowntimeModel():
            try:
                downtime_commands.schedule_services_downtimes_with_query(
                    live,
                    query=body.query,
                    start_time=body.start_time,
                    end_time=body.end_time,
                    recur=body.recur,
                    duration=body.duration,
                    user_id=user.ident,
                    comment=body.comment or "",
                )
            except QueryException:
                raise ProblemException(
                    status=422,
                    title="Query did not match any service",
                    detail="The provided query returned an empty list so no downtime was set",
                )
        case _:
            assert_never(body)

    return ApiResponse(body=None, status_code=204)


ENDPOINT_CREATE_SERVICE_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("downtime", "service"),
        link_relation="cmk/create_service",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=create_service_related_downtime_v1,
            additional_status_codes=[422],
            status_descriptions={
                204: "Create service related downtimes commands have been sent to Livestatus. "
                + LIVESTATUS_GENERIC_EXPLANATION
            },
        )
    },
)
