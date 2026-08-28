#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.api_endpoints.models.folder_models import FolderModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import (
    folder_etag,
    FolderPathParam,
    make_pending_changes,
    serialize_folder,
    UPDATE_PERMISSIONS,
)
from .models.request_models import UpdateFolderModel


def update_folder_v1(
    api_context: ApiContext,
    body: UpdateFolderModel,
    folder: FolderPathParam,
) -> ApiResponse[FolderModel]:
    """Update a folder"""
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.edit_folders")
    if api_context.etag.enabled:
        api_context.etag.verify(folder_etag(folder))

    attributes = folder.attributes.copy()
    if body.attributes is not None and (replacement := body.attributes.to_internal()):
        attributes = replacement
    if body.update_attributes is not None:
        attributes.update(body.update_attributes.to_internal())
    if body.remove_attributes is not None:
        faulty_attributes = []
        for attribute in body.remove_attributes:
            try:
                # FIXME: The typing here is a lie: One can't pretend to still have
                # HostAttributes in attributes after removing random keys from it.
                attributes.pop(attribute)  # type: ignore[misc]
            except KeyError:
                faulty_attributes.append(attribute)
        if faulty_attributes:
            raise ProblemException(
                status=400,
                title="The folder was not updated",
                detail=(
                    "The following attributes did not exist and could therefore not be removed: "
                    f"{', '.join(faulty_attributes)}"
                ),
            )

    folder.edit(
        folder.title() if body.title is None else body.title,
        attributes,
        pprint_value=api_context.config.wato_pprint_config,
        pending_changes=make_pending_changes(api_context),
        acting_user=api_context.user,
    )
    return ApiResponse(
        body=serialize_folder(folder, show_hosts=False, api_context=api_context),
        status_code=200,
        etag=folder_etag(folder),
    )


ENDPOINT_UPDATE_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("folder_config", "{folder}"),
        link_relation=".../persist",
        method="put",
    ),
    permissions=EndpointPermissions(required=UPDATE_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=update_folder_v1)},
    behavior=EndpointBehavior(etag="both"),
)
