#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import AfterValidator

from cmk.gui.openapi.api_endpoints.models.folder_attribute_models import FolderViewAttributeModel
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostViewAttributeModel
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
    LinkableModel,
    ObjectActionMemberModel,
    ObjectCollectionMemberModel,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import HostConverter


@dataclass(kw_only=True, slots=True)
class HostExtensionsModel:
    folder: AnnotatedFolder = api_field(description="The folder, in which this host resides.")
    attributes: HostViewAttributeModel = api_field(description="Attributes of this host.")
    effective_attributes: HostViewAttributeModel | ApiOmitted = api_field(
        description="All attributes of this host and all parent folders.",
        default_factory=ApiOmitted,
    )
    is_cluster: bool = api_field(
        description="If this is a cluster host, i.e. a container for other hosts."
    )
    is_offline: bool = api_field(description="Whether the host is offline.")
    cluster_nodes: Sequence[Annotated[str, AfterValidator(HostConverter.host_name)]] | None = (
        api_field(
            description="In the case this is a cluster host, these are the cluster nodes.",
        )
    )


@dataclass(kw_only=True, slots=True)
class FolderMembersModel:
    hosts: ObjectCollectionMemberModel = api_field(
        description="A list of links pointing to the actual host-resources."
    )
    move: ObjectActionMemberModel = api_field(
        description="An action which triggers the move of this folder to another folder."
    )


@dataclass(kw_only=True, slots=True)
class FolderExtensionsModel:
    path: str = api_field(description="The full path of this folder, slash delimited.")
    attributes: FolderViewAttributeModel = api_field(
        description="The folder's attributes. Hosts placed in this folder will inherit these attributes."
    )


@dataclass(kw_only=True, slots=True)
class FolderModel(LinkableModel):
    domainType: Literal["folder_config"] = api_field(
        description="The domain type of the object.",
    )
    id: str = api_field(description="The full path of the folder, tilde-separated.")
    title: str = api_field(description="The human readable title for this folder.")
    members: FolderMembersModel = api_field(
        description="Specific collections or actions applicable to this object."
    )
    extensions: FolderExtensionsModel = api_field(description="Data and Meta-Data of this object.")


@dataclass(kw_only=True, slots=True)
class HostMembersModel(DomainObjectModel):
    folder_config: FolderModel = api_field(
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array."
    )


@dataclass(kw_only=True, slots=True)
class HostConfigModel(DomainObjectModel):
    domainType: Literal["host_config"] = api_field(description="The domain type of the object.")
    members: HostMembersModel | None = api_field(
        description="All the members of the host object.",
    )
    extensions: HostExtensionsModel = api_field(
        description="All the data and metadata of this host."
    )


@dataclass(kw_only=True, slots=True)
class HostConfigCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["host_config"] = api_field(
        description="The domain type of the objects in the collection",
        example="host_config",
    )
    # TODO: add proper example
    value: list[HostConfigModel] = api_field(description="A list of host objects", example="")
