#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.framework.model.api_field import api_field
from cmk.gui.openapi.framework.model.omitted import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import link_rel
from cmk.gui.openapi.restful_objects.type_defs import LinkRelation


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
        title="Domain Type", description="The domain type of the linked resource"
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

    @classmethod
    def create(
        cls,
        rel: LinkRelation,
        href: str,
        method: HTTPMethod = "get",
        content_type: str = "application/json",
        profile: str | None = None,
        title: str | None = None,
        # these might have to be changed to a dataclass but let's see
        parameters: dict[str, str] | None = None,
        body_params: dict[str, str | None] | None = None,
    ) -> "LinkModel":
        link_obj = link_rel(
            rel=rel,
            href=href,
            content_type=content_type,
            profile=profile,
            title=title,
            parameters=parameters,
            body_params=body_params,
        )
        # make mypy happy
        methods: Mapping[str, Literal["GET", "POST", "PUT", "DELETE"]] = {
            "get": "GET",
            "post": "POST",
            "put": "PUT",
            "delete": "DELETE",
        }
        return cls(
            rel=link_obj["rel"],
            href=link_obj["href"],
            method=methods[method],
            type=link_obj["type"],
            domainType=link_obj["domainType"],
            title=link_obj.get("title", ApiOmitted()),
            body_params=link_obj.get("body_params", ApiOmitted()),
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
    id: str = api_field(description="The name of this collection.")
    domainType: str = api_field(description="The domain type of the objects in the collection.")
    title: str | ApiOmitted = api_field(
        description="A human readable title of this object. Can be used for user interfaces.",
        default_factory=ApiOmitted,
    )
    value: list = api_field(
        description="The collection itself. Each entry in here is part of the collection."
    )
    extensions: dict[str, object] | ApiOmitted = api_field(
        description="Additional attributes alongside the collection.",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class ObjectMemberBaseModel(LinkableModel):
    id: str = api_field(description="The id of this object.")
    disabledReason: str | None = api_field(
        description=(
            'Provides the reason (or the literal "disabled") why an object property or '
            "collection is un-modifiable, or, in the case of an action, unusable (and "
            "hence no links to mutate that member's state, or invoke the action, are "
            "provided)."
        )
    )
    invalidReason: str | None = api_field(
        description=(
            'Provides the reason (or the literal "invalid") why a proposed value for a '
            "property, collection or action argument is invalid. Appears within an "
            "argument representation 2.9 returned as a response."
        ),
        example="invalid",
    )
    x_ro_invalidReason: str | None = api_field(
        alias="x-ro-invalidReason",
        description=(
            "Provides the reason why a SET OF proposed values for properties or arguments "
            "is invalid."
        ),
        example="invalid",
    )


@dataclass(kw_only=True, slots=True)
class ObjectCollectionMemberModel(ObjectMemberBaseModel):
    memberType: Literal["collection"] = api_field(description="The type of this member.")
    value: list[LinkModel]
    name: str = api_field(description="The name of the object.", example="import_values")
    title: str = api_field(
        description="A human readable title of this object. Can be used for user interfaces."
    )


@dataclass(kw_only=True, slots=True)
class ObjectActionMemberModel(ObjectMemberBaseModel):
    memberType: Literal["action"] = api_field(description="The type of this member.")
    parameters: dict
    name: str = api_field(description="The name of the object.", example="import_values")
    title: str = api_field(
        description="A human readable title of this object. Can be used for user interfaces."
    )
