#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.api_endpoints.models.folder_attribute_models import FolderViewAttributeModel
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectModel,
    ObjectCollectionMemberModel,
)


@api_model
class FolderMembersModel:
    hosts: ObjectCollectionMemberModel | ApiOmitted = api_field(
        description="A list of links pointing to the actual host-resources.",
        default_factory=ApiOmitted,
    )


@api_model
class FolderExtensionsModel:
    # ``path`` and ``attributes`` are always emitted, but declared optional to match the required
    # array of the previous (marshmallow) ``FolderExtensions`` schema.
    path: str | ApiOmitted = api_field(
        description="The full path of this folder, slash delimited.",
        default_factory=ApiOmitted,
    )
    attributes: FolderViewAttributeModel | ApiOmitted = api_field(
        description="The folder's attributes. Hosts placed in this folder will inherit these attributes.",
        default_factory=ApiOmitted,
    )


@api_model
class FolderModel(DomainObjectModel):
    domainType: Literal["folder_config"] = api_field(
        description="The domain type of the object.",
    )
    members: FolderMembersModel | ApiOmitted = api_field(
        description="Specific collections or actions applicable to this object.",
        default_factory=ApiOmitted,
    )
    extensions: FolderExtensionsModel | ApiOmitted = api_field(
        description="Data and Meta-Data of this object.",
        default_factory=ApiOmitted,
    )
