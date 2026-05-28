#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import omd_site
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.gui.watolib.automations import make_automation_config, MKAutomationException
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.services import DiscoveryAction, get_check_table

from ._family import SERVICE_DISCOVERY_FAMILY
from ._utils import (
    job_snapshot,
    make_pending_changes,
    RO_PERMISSIONS,
    serialize_discovery_result,
)
from .models.response_models import ServiceDiscoveryResultModel


def show_service_discovery_result_v1(
    api_context: ApiContext,
    host: Annotated[
        Annotated[Host, TypedPlainValidator(str, HostConverter().host)],
        PathParam(
            description="The host of the service discovery result",
            example="example.com",
            alias="host_name",
        ),
    ],
) -> ServiceDiscoveryResultModel:
    """Show the current service discovery result"""
    user.need_permission("wato.edit")
    user.need_permission("wato.services")
    user.need_permission("wato.see_all_folders")

    try:
        discovery_result = get_check_table(
            host,
            DiscoveryAction.NONE,
            automation_config=make_automation_config(api_context.config.sites[host.site_id()]),
            user_permission_config=api_context.config.user_permissions().to_serializable_config(),
            raise_errors=False,
            debug=api_context.config.debug,
            use_git=api_context.config.wato_use_git,
            pending_changes=make_pending_changes(
                site_configs=api_context.config.sites,
                use_git=api_context.config.wato_use_git,
                local_site=omd_site(),
                acting_user=user.id,
            ),
        )
    except MKAutomationException:
        pass
    else:
        return serialize_discovery_result(
            host,
            discovery_result,
            version=api_context.version,
            host_url=api_context.host_url,
        )

    try:
        snapshot = job_snapshot(host, api_context.config.sites, debug=api_context.config.debug)
    except MKAutomationException:
        raise ProblemException(
            status=400,
            title="Error running automation",
            detail="Could not retrieve the service discovery result",
        )
    logs = snapshot.status.loginfo
    raise ProblemException(
        status=400,
        title="Error running automation",
        detail="Could not retrieve the service discovery result",
        ext=EXT(
            {
                "job_id": snapshot.job_id,
                "state": snapshot.status.state,
                "logs": {
                    "result": logs["JobResult"],
                    "progress": logs["JobProgressUpdate"],
                    "exception": logs["JobException"],
                },
            }
        ),
    )


ENDPOINT_SHOW_SERVICE_DISCOVERY_RESULT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("service_discovery", "{host_name}"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(required=RO_PERMISSIONS),
    doc=EndpointDoc(family=SERVICE_DISCOVERY_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=show_service_discovery_result_v1,
            additional_status_codes=[400],
        )
    },
)
