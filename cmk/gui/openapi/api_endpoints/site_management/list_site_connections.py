#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.site_management import SitesApiMgr

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .internal_to_response import from_internal
from .models.config_example import default_config_example
from .models.response_models import SiteConnectionModel
from .utils import PERMISSIONS


@api_model
class SiteManagementCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["site_connection"] = api_field(
        description="The domain type of the objects in the collection",
        example="site_connection",
    )
    value: list[SiteConnectionModel] = api_field(
        description="A list of site configuration objects.",
        example=[
            {
                "links": [],
                "domainType": "site_connection",
                "id": "prod",
                "title": "Site Alias",
                "members": {},
                "extensions": default_config_example(),
            }
        ],
    )


def list_sites_connections_v1() -> SiteManagementCollectionModel:
    """Show all site connections"""
    user.need_permission("wato.sites")

    return SiteManagementCollectionModel(
        id="site_connection",
        domainType="site_connection",
        value=[from_internal(site) for site in SitesApiMgr().get_all_sites().values()],
        links=[LinkModel.create("self", collection_href("site_connection"))],
        extensions={},
    )


ENDPOINT_LIST_SITE_CONNECTIONS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("site_connection"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_sites_connections_v1)},
)
