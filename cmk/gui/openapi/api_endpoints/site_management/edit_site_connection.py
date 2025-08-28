#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.exceptions import MKUserError
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
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.site_config import site_is_local
from cmk.gui.watolib.site_management import (
    add_changes_after_editing_site_connection,
    SitesApiMgr,
)

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .models.request_models import SiteConnectionEditModel
from .models.response_models import SiteConnectionModel
from .utils import PERMISSIONS


def edit_site_connection_v1(
    api_context: ApiContext,
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
    body: SiteConnectionEditModel,
) -> SiteConnectionModel:
    """Edit a site connection"""
    user.need_permission("wato.sites")

    site_config_spec_from_request = body.site_config.to_internal()
    body.site_config.basic_settings.site_id = site_id

    if (secret := SitesApiMgr().get_a_site(site_id).get("secret")) is not None:
        site_config_spec_from_request["secret"] = secret

    try:
        sites_to_update = SitesApiMgr().get_connected_sites_to_update(
            new_or_deleted_connection=False,
            modified_site=site_id,
            current_site_config=site_config_spec_from_request,
            old_site_config=SitesApiMgr().get_a_site(site_id),
            site_configs=SitesApiMgr().get_all_sites(),
        )

        SitesApiMgr().validate_and_save_site(
            site_id,
            site_config_spec_from_request,
            pprint_value=api_context.config.wato_pprint_config,
        )
    except MKUserError as exc:
        raise RestAPIRequestGeneralException(
            status=400,
            title="User Error",
            detail=str(exc),
        )

    add_changes_after_editing_site_connection(
        site_id=site_id,
        is_new_connection=False,
        replication_enabled=bool(site_config_spec_from_request.get("replication")),
        is_local_site=site_is_local(site_config_spec_from_request),
        connected_sites=sites_to_update,
        use_git=api_context.config.wato_use_git,
    )

    return SiteConnectionModel.from_internal(SitesApiMgr().get_a_site(site_id))


ENDPOINT_EDIT_SITE_CONNECTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("site_connection", "{site_id}"),
        link_relation="cmk/update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=edit_site_connection_v1)},
)
