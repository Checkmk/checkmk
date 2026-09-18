#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.gui.watolib.hosts_and_folders import Folder

from ._family import FOLDER_CONFIG_FAMILY
from ._utils import make_pending_changes, serialize_folders_collection, UPDATE_PERMISSIONS
from .models.request_models import BulkUpdateFolderModel
from .models.response_models import FolderCollectionModel


def bulk_update_folders_v1(
    api_context: ApiContext,
    body: BulkUpdateFolderModel,
) -> FolderCollectionModel:
    """Bulk update folders

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk
    """
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.edit_folders")

    folders: list[Folder] = []
    faulty_folders: list[str] = []
    for entry in body.entries:
        folder = entry.folder
        title = folder.title() if entry.title is None else entry.title
        attributes = folder.attributes.copy()

        if entry.attributes is not None and (replacement := entry.attributes.to_internal()):
            attributes = replacement
        if entry.update_attributes is not None:
            attributes.update(entry.update_attributes.to_internal())
        if entry.remove_attributes is not None:
            faulty_attempt = False
            for attribute in entry.remove_attributes:
                try:
                    # FIXME: The typing here is a lie: One can't pretend to still have
                    # HostAttributes in attributes after removing random keys from it.
                    attributes.pop(attribute)  # type: ignore[misc]
                except KeyError:
                    faulty_attempt = True
                    break
            if faulty_attempt:
                faulty_folders.append(title)
                continue

        folder.edit(
            title,
            attributes,
            pprint_value=api_context.config.wato_pprint_config,
            pending_changes=make_pending_changes(api_context),
            acting_user=api_context.user,
        )
        folders.append(folder)

    if faulty_folders:
        raise ProblemException(
            status=400,
            title="Some folders were not updated",
            detail=(
                "The following folders were not updated since some of the provided remove "
                f"attributes did not exist: {', '.join(faulty_folders)}"
            ),
        )

    return serialize_folders_collection(folders, show_hosts=False, api_context=api_context)


ENDPOINT_BULK_UPDATE_FOLDER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("folder_config", "bulk-update"),
        link_relation="cmk/bulk_update",
        method="put",
    ),
    permissions=EndpointPermissions(required=UPDATE_PERMISSIONS),
    doc=EndpointDoc(family=FOLDER_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=bulk_update_folders_v1)},
)
