#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)


@api_model
class CommentExtensionsModel:
    host_name: str = api_field(description="The host name.")
    id: int = api_field(description="The comment ID")
    author: str = api_field(description="The author of the comment")
    comment: str = api_field(description="The comment itself")
    persistent: bool = api_field(description="If true, the comment will be persisted")
    entry_time: str = api_field(description="The timestamp from when the comment was created.")
    is_service: bool = api_field(
        description="True if the comment is from a service or else it's False."
    )
    site_id: str = api_field(
        description="The site id of the comment.",
        example="production",
    )
    service_description: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description="The service name the comment belongs to.",
    )


@api_model
class CommentObjectModel(DomainObjectModel):
    domainType: Literal["comment"] = api_field(description="The domain type of the object.")
    extensions: CommentExtensionsModel = api_field(
        description="The attributes of a service/host comment."
    )


@api_model
class CommentCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["comment"] = api_field(
        description="The domain type of the objects in the collection."
    )
    value: list[CommentObjectModel] = api_field(
        description="A list of comment objects.", example=[]
    )
