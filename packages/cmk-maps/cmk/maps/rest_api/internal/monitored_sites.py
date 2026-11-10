#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The monitored sites of a user, for the Maps daemon.

The GUI queries only the sites set as "Monitored sites" for a user, and the
daemon asks the same sites for them.
"""

from http import HTTPStatus

from cmk.ccc.user import UserId
from cmk.gui.oauth.openapi.utils import require_site_internal_caller
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.userdb import load_user
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsMonitoredSitesRequest
from cmk.maps.rest_api.internal.models.response_models import MapsMonitoredSitesResponse
from cmk.maps.rest_api.utils import NO_CONFIG_CHANGE


def show_monitored_sites_v1(
    api_context: ApiContext, body: MapsMonitoredSitesRequest
) -> MapsMonitoredSitesResponse:
    """Show the monitored sites of a user

    Reserved for the Maps daemon, which calls it with the site-internal secret
    for a user it identified from their GUI session.
    """
    require_site_internal_caller(api_context)
    # The profile of a user who is gone would read as all sites.
    if body.user_id not in api_context.config.multisite_users:
        raise ProblemException(
            status=HTTPStatus.NOT_FOUND,
            title="Unknown user",
            detail=f"There is no user {body.user_id!r}.",
        )
    sites = load_user(UserId(body.user_id)).get("authorized_sites")
    return MapsMonitoredSitesResponse(monitored_sites=None if sites is None else sorted(sites))


ENDPOINT_SHOW_MONITORED_SITES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_monitored_sites", "show"),
        link_relation="cmk/show_maps_monitored_sites",
        method="post",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={
        APIVersion.INTERNAL: EndpointHandler(
            handler=show_monitored_sites_v1, additional_status_codes=[HTTPStatus.NOT_FOUND]
        )
    },
)
