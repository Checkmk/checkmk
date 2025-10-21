#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
    LinkModel,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.utils import permission_verification as permissions

from ._family import PAGETYPE_TOPIC_FAMILY


@api_model
class PagetypeTopicExtensions:
    description: str = api_field(
        description="Description of the pagetype topic.",
        example="This topic covers all pagetypes related to networking.",
    )
    sort_index: int = api_field(description="Sorting index for the topics.", example=0)
    is_default: bool = api_field(
        description="Indicates if this is the default topic.", example=False
    )


@api_model
class PagetypeTopicModel(DomainObjectModel):
    domainType: Literal["pagetype_topic"] = api_field(description="The domain type of the object.")
    extensions: PagetypeTopicExtensions = api_field(
        description="Additional properties of the pagetype topic."
    )


@api_model
class PagetypeTopicCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["pagetype_topic"] = api_field(
        description="The domain type of the objects in the collection."
    )
    value: list[PagetypeTopicModel] = api_field(description="The list of pagetype topics.")


def list_topics_v1(api_context: ApiContext) -> PagetypeTopicCollectionModel:
    """Show all pagetype topics the user has access to."""
    user_permissions = api_context.config.user_permissions()
    topics = PagetypeTopics.load(user_permissions)
    return PagetypeTopicCollectionModel(
        domainType="pagetype_topic",
        id="all",
        links=[LinkModel.create("self", collection_href("pagetype_topic"))],
        value=[
            PagetypeTopicModel(
                domainType="pagetype_topic",
                id=topic.name(),
                title=topic.title(),
                links=[],
                extensions=PagetypeTopicExtensions(
                    description=topic.description(),
                    sort_index=topic.sort_index(),
                    is_default=topic.name() == PagetypeTopics.default_topic(),
                ),
            )
            for topic in topics.instances()
            if topic.is_permitted(user_permissions)
        ],
    )


ENDPOINT_LIST_TOPICS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("pagetype_topic"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.PrefixPerm("pagetype_topic"),
                permissions.Optional(
                    permissions.AllPerm(
                        [
                            permissions.Perm("general.see_user_pagetype_topic"),
                            permissions.AnyPerm(
                                [
                                    permissions.Perm("general.publish_pagetype_topic"),
                                    permissions.Perm("general.publish_to_groups_pagetype_topic"),
                                    permissions.Perm(
                                        "general.publish_to_foreign_groups_pagetype_topic"
                                    ),
                                    permissions.Perm("general.publish_to_sites_pagetype_topic"),
                                ]
                            ),
                        ]
                    )
                ),
            ]
        )
    ),
    doc=EndpointDoc(family=PAGETYPE_TOPIC_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_topics_v1)},
)
