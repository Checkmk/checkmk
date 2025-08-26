#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.site_config import site_is_local
from cmk.gui.watolib.site_management import (
    add_changes_after_editing_site_connection,
    SitesApiMgr,
)

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .models.request_models import SiteConnectionCreateModel
from .models.response_models import SiteConnectionModel
from .utils import PERMISSIONS


def create_site_connection_v1(
    api_context: ApiContext,
    body: SiteConnectionCreateModel,
) -> SiteConnectionModel:
    """Create a site connection"""
    user.need_permission("wato.sites")

    site_id = body.site_config.basic_settings.site_id
    new_site_config_spec = body.site_config.to_internal()

    try:
        sites_to_update = SitesApiMgr().get_connected_sites_to_update(
            new_or_deleted_connection=True,
            modified_site=site_id,
            current_site_config=new_site_config_spec,
            old_site_config=None,
            site_configs=SitesApiMgr().get_all_sites(),
        )
        SitesApiMgr().validate_and_save_site(
            site_id,
            new_site_config_spec,
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
        is_new_connection=True,
        replication_enabled=bool(new_site_config_spec.get("replication")),
        is_local_site=site_is_local(new_site_config_spec),
        connected_sites=sites_to_update,
        use_git=api_context.config.wato_use_git,
    )

    return SiteConnectionModel.from_internal(new_site_config_spec)


ENDPOINT_CREATE_SITE_CONNECTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("site_connection"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=create_site_connection_v1)},
)
