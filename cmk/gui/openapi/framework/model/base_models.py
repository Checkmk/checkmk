#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.gui.openapi.framework.model.api_field import api_field
from cmk.gui.openapi.framework.model.omitted import ApiOmitted


@dataclass(kw_only=True, slots=True)
class LinkModel:
    rel: str = api_field(
        title="Relation",
        description="Indicates the nature of the relationship of the related resource to the resource that generated this representation",
        example="self",
    )
    href: str = api_field(
        title="URL",
        description="The (absolute) address of the related resource. Any characters that are invalid in URLs must be URL encoded.",
        example="https://.../api_resource",
    )
    method: Literal["GET", "POST", "PUT", "DELETE"] = api_field(
        title="Method",
        description="The HTTP method to use to traverse the link (get, post, put or delete)",
        example="GET",
    )
    type: str = api_field(
        title="Content-Type",
        description="The content-type that the linked resource will return",
        example="application/json",
    )
    domainType: Literal["link"] = api_field(
        default="link", title="Domain Type", description="The domain type of the linked resource"
    )
    title: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Title",
        description="string that the consuming application may use to render the link without having to traverse the link in advance",
        example="The object itself",
    )
    body_params: Mapping[str, object] | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Body Parameters",
        description="A map of values that shall be sent in the request body. If this is present, the request has to be sent with a content-type of 'application/json'.",
        example={"key": "value"},
    )


@dataclass(kw_only=True, slots=True)
class LinkableModel:
    links: list[LinkModel] = api_field(
        title="Links",
        description="List of links to other resources.",
        example=[
            {
                "rel": "self",
                "href": "https://.../api_resource",
                "method": "GET",
                "type": "application/json",
            }
        ],
    )


@dataclass(kw_only=True, slots=True)
class DomainObjectModel(LinkableModel):
    domainType: str = api_field(
        title="Domain Type", description='The "domain-type" of the object.', example="host"
    )
    id: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="ID",
        description="The unique identifier for this domain-object type.",
        example="host1",
    )
    title: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Title",
        description="A human readable title of this object. Can be used for user interfaces.",
        example="My Host",
    )


@dataclass(kw_only=True, slots=True)
class DomainObjectCollectionModel(LinkableModel):
    id: str = api_field(description="The name of this collection.", default="all")
    domainType: str = api_field(description="The domain type of the objects in the collection.")
    title: str | ApiOmitted = api_field(
        description="A human readable title of this object. Can be used for user interfaces.",
        default_factory=ApiOmitted,
    )
    value: list = api_field(
        description="The collection itself. Each entry in here is part of the collection."
    )
    extensions: dict = api_field(
        description="Additional attributes alongside the collection.", default_factory=dict
    )
