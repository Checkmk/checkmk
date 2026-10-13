#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.api_endpoints.models.folder_models import FolderModel
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel

__all__ = ["FolderCollectionModel", "FolderModel"]


@api_model
class FolderCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["folder_config"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[FolderModel] = api_field(description="A list of folder objects.", example=[])
