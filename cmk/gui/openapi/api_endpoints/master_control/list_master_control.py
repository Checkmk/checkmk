#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.livestatus_client.queries import Query

from ._family import MASTER_CONTROL_FAMILY
from ._utils import PERMISSIONS, serialize_master_control, status_columns
from .models.response_models import MasterControlCollectionModel


def list_master_control_v1() -> MasterControlCollectionModel:
    """Show the master control settings of all sites"""
    user.need_permission("sidesnap.master_control")
    live = sites.live()
    rows = Query(status_columns()).fetchall(live, include_site_ids=True)
    return MasterControlCollectionModel(
        domainType="master_control",
        id="master_control",
        links=[LinkModel.create("self", collection_href("master_control"))],
        value=[serialize_master_control(SiteId(row["site"]), row) for row in rows],
    )


ENDPOINT_LIST_MASTER_CONTROL = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("master_control"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MASTER_CONTROL_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_master_control_v1)},
    behavior=EndpointBehavior(skip_locking=True),
)
