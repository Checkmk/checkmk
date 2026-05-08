#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import downtimes as downtime_commands
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.downtime._utils import RW_PERMISSIONS
from cmk.gui.openapi.api_endpoints.downtime.models.request_models import (
    ModifyDowntimeByHostGroupModel,
    ModifyDowntimeByIdModel,
    ModifyDowntimeByNameModel,
    ModifyDowntimeByQueryModel,
    ModifyDowntimeByServiceGroupModel,
    ModifyEndTimeAbsoluteModel,
    ModifyEndTimeModel,
    ModifyEndTimeRelativeModel,
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
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.expressions import And, Or, QueryExpression
from cmk.livestatus_client.tables.downtimes import Downtimes

from ._family import DOWNTIME_FAMILY


def _resolve_end_time(
    end_time_model: ModifyEndTimeModel | None,
) -> dt.datetime | dt.timedelta | None:
    match end_time_model:
        case None:
            return None
        case ModifyEndTimeAbsoluteModel():
            return end_time_model.value
        case ModifyEndTimeRelativeModel():
            return dt.timedelta(minutes=end_time_model.value)
        case _:
            assert_never(end_time_model)


def modify_downtime_v1(
    body: Annotated[
        ModifyDowntimeByIdModel
        | ModifyDowntimeByNameModel
        | ModifyDowntimeByQueryModel
        | ModifyDowntimeByHostGroupModel
        | ModifyDowntimeByServiceGroupModel,
        Discriminator("modify_type"),
    ],
) -> ApiResponse[None]:
    """Modify a scheduled downtime"""
    site_id: SiteId | None = None
    query_expr: QueryExpression
    match body:
        case ModifyDowntimeByQueryModel():
            query_expr = body.query
        case ModifyDowntimeByIdModel():
            query_expr = Downtimes.id == body.downtime_id
            site_id = body.site_id
        case ModifyDowntimeByHostGroupModel():
            query_expr = Downtimes.host_groups.equals(body.hostgroup_name)
        case ModifyDowntimeByServiceGroupModel():
            query_expr = Downtimes.service_groups.equals(body.servicegroup_name)
        case ModifyDowntimeByNameModel():
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

    comment = body.comment
    end_time = _resolve_end_time(body.end_time)
    if end_time is None and comment is None:
        raise ProblemException(
            status=400,
            title="No modification specified",
            detail="You must specify at least one field to modify",
        )

    downtime_commands.modify_downtimes(
        sites.live(),
        query_expr,
        site_id,
        user_id=user.ident,
        end_time=end_time,
        comment=comment,
    )

    return ApiResponse(body=None, status_code=204)


ENDPOINT_MODIFY_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("downtime", "modify"),
        link_relation=".../update",
        method="put",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=modify_downtime_v1,
            status_descriptions={
                204: "Update downtimes commands have been sent to Livestatus. "
                + LIVESTATUS_GENERIC_EXPLANATION
            },
        )
    },
)
