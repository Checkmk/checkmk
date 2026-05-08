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
    CreateHostDowntimeModel,
    CreateHostGroupDowntimeModel,
    CreateHostQueryDowntimeModel,
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

from ._family import DOWNTIME_FAMILY


def create_host_related_downtime_v1(
    body: Annotated[
        CreateHostDowntimeModel | CreateHostGroupDowntimeModel | CreateHostQueryDowntimeModel,
        Discriminator("downtime_type"),
    ],
) -> ApiResponse[None]:
    """Create a host related scheduled downtime"""
    live = sites.live()

    match body:
        case CreateHostDowntimeModel():
            downtime_commands.schedule_host_downtime(
                live,
                host_entry=str(body.host_name),
                start_time=body.start_time,
                end_time=body.end_time,
                recur=body.recur,
                duration=body.duration,
                user_id=user.ident,
                comment=body.comment or f"Downtime for host {body.host_name!r}",
            )
        case CreateHostGroupDowntimeModel():
            downtime_commands.schedule_hostgroup_host_downtime(
                live,
                hostgroup_name=body.hostgroup_name,
                start_time=body.start_time,
                end_time=body.end_time,
                recur=body.recur,
                duration=body.duration,
                user_id=user.ident,
                comment=body.comment or f"Downtime for hostgroup {body.hostgroup_name!r}",
            )
        case CreateHostQueryDowntimeModel():
            try:
                downtime_commands.schedule_hosts_downtimes_with_query(
                    live,
                    body.query,
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
                    title="Query did not match any host",
                    detail="The provided query returned an empty list so no downtime was set",
                )
        case _:
            assert_never(body)

    return ApiResponse(body=None, status_code=204)


ENDPOINT_CREATE_HOST_DOWNTIME = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("downtime", "host"),
        link_relation="cmk/create_host",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=DOWNTIME_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=create_host_related_downtime_v1,
            additional_status_codes=[422],
            status_descriptions={
                204: "Create host related downtimes commands have been sent to Livestatus. "
                + LIVESTATUS_GENERIC_EXPLANATION
            },
        )
    },
)
