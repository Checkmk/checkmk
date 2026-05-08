#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import downtimes as downtime_commands
from cmk.gui.openapi.api_endpoints.downtime._utils import RW_PERMISSIONS
from cmk.gui.openapi.api_endpoints.downtime.models.request_models import (
    DeleteDowntimeByHostGroupModel,
    DeleteDowntimeByIdModel,
    DeleteDowntimeByNameModel,
    DeleteDowntimeByQueryModel,
    DeleteDowntimeByServiceGroupModel,
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
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.spec.utils import LIVESTATUS_GENERIC_EXPLANATION
from cmk.livestatus_client.expressions import And, Or, QueryExpression
from cmk.livestatus_client.tables.downtimes import Downtimes

from ._family import DOWNTIME_FAMILY


def delete_downtime_v1(
    body: Annotated[
        DeleteDowntimeByIdModel
        | DeleteDowntimeByNameModel
        | DeleteDowntimeByQueryModel
        | DeleteDowntimeByHostGroupModel
        | DeleteDowntimeByServiceGroupModel,
        Discriminator("delete_type"),
    ],
) -> ApiResponse[None]:
    """Delete a scheduled downtime"""
    site_id: SiteId | None = None
    query_expr: QueryExpression
    match body:
        case DeleteDowntimeByQueryModel():
            query_expr = body.query
        case DeleteDowntimeByIdModel():
            query_expr = Downtimes.id == body.downtime_id
            site_id = body.site_id
        case DeleteDowntimeByHostGroupModel():
            query_expr = Downtimes.host_groups.equals(body.hostgroup_name)
        case DeleteDowntimeByServiceGroupModel():
            query_expr = Downtimes.service_groups.equals(body.servicegroup_name)
        case DeleteDowntimeByNameModel():
            hostname = str(body.host_name)
            if body.service_descriptions is None:
                query_expr = And(
                    Downtimes.host_name.op("=", hostname), Downtimes.is_service.op("=", 0)
                )
            else:
                query_expr = And(
                    Downtimes.host_name.op("=", hostname),
                    Or(
                        *[Downtimes.service_description == svc for svc in body.service_descriptions]
                    ),
                )
        case _:
            assert_never(body)

    downtime_commands.delete_downtime(sites.live(), query_expr, site_id)
    return ApiResponse(body=None, status_code=204)


ENDPOINT_DELETE_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("downtime", "delete"),
        link_relation=".../delete",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=delete_downtime_v1,
            status_descriptions={
                204: "Delete downtimes commands have been sent to Livestatus. "
                + LIVESTATUS_GENERIC_EXPLANATION
            },
        )
    },
)
