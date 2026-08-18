#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Final

from cmk.ccc.site import omd_site
from cmk.gui.groups import GroupSpec
from cmk.gui.openapi.api_endpoints.host_group_config.models.response_models import (
    HostGroupCollectionModel,
    HostGroupExtensions,
    HostGroupModel,
)
from cmk.gui.openapi.endpoints.utils import complement_customer
from cmk.gui.openapi.framework import ApiContext, ETag
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects.constructors import collection_href, versioned_absolute_url
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.web.utils import permission_verification as permissions

PERMISSIONS = permissions.Perm("wato.groups")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)

DOMAIN_TYPE: Final = "host_group_config"


def host_group_etag(group: GroupSpec) -> ETag:
    return ETag(dict(group))


def serialize_host_group(api_context: ApiContext, group: GroupSpec) -> HostGroupModel:
    ident = group["id"]
    extensions = complement_customer({key: value for key, value in group.items() if key != "id"})
    return HostGroupModel(
        domainType=DOMAIN_TYPE,
        id=ident,
        title=group["alias"] or ident,
        members={},
        extensions=HostGroupExtensions(
            alias=extensions["alias"],
            customer=extensions.get("customer", ApiOmitted()),
        ),
        links=generate_links(
            DOMAIN_TYPE, ident, host_url=api_context.host_url, version=api_context.version
        ),
    )


def _serialize_host_group_entry(api_context: ApiContext, group: GroupSpec) -> HostGroupModel:
    ident = group["id"]
    extensions = complement_customer(
        {key: value for key, value in group.items() if key not in ("id", "alias")}
    )
    return HostGroupModel(
        domainType=DOMAIN_TYPE,
        id=ident,
        title=group["alias"],
        members={},
        extensions=HostGroupExtensions(
            customer=extensions.get("customer", ApiOmitted()),
        ),
        links=generate_links(
            DOMAIN_TYPE, ident, host_url=api_context.host_url, version=api_context.version
        ),
    )


def serialize_host_group_collection(
    api_context: ApiContext, groups: Sequence[GroupSpec]
) -> HostGroupCollectionModel:
    return HostGroupCollectionModel(
        id=DOMAIN_TYPE,
        domainType=DOMAIN_TYPE,
        value=[_serialize_host_group_entry(api_context, group) for group in groups],
        links=[
            LinkModel.create(
                "self",
                versioned_absolute_url(
                    collection_href(DOMAIN_TYPE),
                    host_url=api_context.host_url,
                    version=api_context.version.value,
                ),
            )
        ],
    )


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            index_update_change_hook,
        ),
    )
