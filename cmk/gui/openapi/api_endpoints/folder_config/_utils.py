#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, TypeAlias

from cmk.ccc.site import omd_site
from cmk.gui.openapi.api_endpoints.models.folder_attribute_models import FolderViewAttributeModel
from cmk.gui.openapi.api_endpoints.models.folder_models import (
    FolderExtensionsModel,
    FolderMembersModel,
    FolderModel,
)
from cmk.gui.openapi.endpoints.utils import folder_slug
from cmk.gui.openapi.framework import ApiContext, ETag, PathParam
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.base_models import LinkModel, ObjectCollectionMemberModel
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects import constructors
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)

from .models.response_models import FolderCollectionModel

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.manage_folders"),
        # If a folder to be deleted still contains hosts, the manage_hosts permission is required.
        permissions.Optional(permissions.Perm("wato.manage_hosts")),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

UPDATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.edit_folders"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

READ_PERMISSIONS = permissions.Optional(permissions.Perm("wato.see_all_folders"))

# TODO: adjust the framework to support this via type statements.
# NOTE: a plain ``TypeAlias`` (not the ``type`` keyword) is required here: this alias is used as a
# handler parameter annotation, and a ``type`` statement would create a ``TypeAliasType`` that the
# endpoint signature introspection cannot unwrap.
FolderPathParam: TypeAlias = Annotated[  # noqa: UP040
    AnnotatedFolder,
    PathParam(
        description=(
            "The path of the folder being requested. Please be aware that slashes can't be used "
            "in the URL. Also, escaping the slashes via %2f will not work. Please replace the path "
            "delimiters with the tilde character `~`."
        ),
        example="~my~fine~folder",
    ),
]


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


def folder_etag(folder: Folder) -> ETag:
    return ETag(
        {
            "path": folder.path(),
            "attributes": folder.attributes,
            "hosts": folder.host_names(),
        }
    )


def _folder_hosts_member(folder: Folder) -> ObjectCollectionMemberModel:
    return ObjectCollectionMemberModel(
        id="hosts",
        memberType="collection",
        name="hosts",
        title="Hosts",
        disabledReason=None,
        invalidReason=None,
        x_ro_invalidReason=None,
        links=[],
        value=[
            LinkModel.create(
                rel=".../value",
                href=constructors.object_href("host_config", host.id()),
                method="get",
                profile=".../object",
                title=host.name(),
                parameters={"collection": "all"},
            )
            for host in folder.hosts().values()
        ],
    )


def serialize_folder(
    folder: Folder,
    *,
    show_hosts: bool,
    api_context: ApiContext,
) -> FolderModel:
    extra_links: list[LinkModel] = []
    if not folder.is_root():
        extra_links.append(
            LinkModel.create(
                rel="cmk/move",
                href=constructors.versioned_absolute_url(
                    constructors.object_action_href(
                        "folder_config", folder_slug(folder), action_name="move"
                    ),
                    host_url=api_context.host_url,
                    version=api_context.version.value,
                ),
                method="post",
                title="Move the folder",
            )
        )

    members = FolderMembersModel(hosts=_folder_hosts_member(folder) if show_hosts else ApiOmitted())

    return FolderModel(
        domainType="folder_config",
        id=folder_slug(folder),
        title=folder.title(),
        links=generate_links(
            "folder_config",
            folder_slug(folder),
            extra_links=extra_links,
            host_url=api_context.host_url,
            version=api_context.version,
        ),
        members=members,
        extensions=FolderExtensionsModel(
            path="/" + folder.path(),
            attributes=FolderViewAttributeModel.from_internal(folder.attributes),
        ),
    )


def serialize_folders_collection(
    folders: list[Folder],
    *,
    show_hosts: bool,
    api_context: ApiContext,
) -> FolderCollectionModel:
    return FolderCollectionModel(
        domainType="folder_config",
        id="folder_config",
        value=[
            serialize_folder(folder, show_hosts=show_hosts, api_context=api_context)
            for folder in folders
        ],
        links=[
            LinkModel.create(
                "self",
                constructors.versioned_absolute_url(
                    constructors.collection_href("folder_config"),
                    host_url=api_context.host_url,
                    version=api_context.version.value,
                ),
            )
        ],
    )
