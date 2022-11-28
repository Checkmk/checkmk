#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow import post_load, ValidationError

from cmk.gui.fields import AuxTagIDField
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)

from cmk import fields


class AuxTagIDShouldExist(BaseSchema):
    aux_tag_id = AuxTagIDField(
        presence="should_exist",
    )


class AuxTagIDShouldExistShouldBeCustom(BaseSchema):
    aux_tag_id = AuxTagIDField(
        presence="should_exist_and_should_be_custom",
    )


class AuxTagID(BaseSchema):
    aux_tag_id = AuxTagIDField()


class AuxTagTopicField(fields.String):
    def __init__(self, **kwargs):
        super().__init__(
            description="Different tags can be grouped in topics to make the visualization and selections in the GUI more comfortable",
            example="Monitoring agents",
            **kwargs,
        )


class AuxTagTitleField(fields.String):
    def __init__(self, **kwargs):
        super().__init__(
            description="The title of the Auxiliary tag",
            example="AuxTagExampleTitle",
            **kwargs,
        )


class AuxTagAttrsResponse(BaseSchema):
    topic = AuxTagTopicField(
        required=True,
    )


class AuxTagAttrsCreate(BaseSchema):
    aux_tag_id = AuxTagIDField(
        required=True,
        presence="should_not_exist",
    )
    topic = AuxTagTopicField(
        required=True,
    )
    title = AuxTagTitleField(
        required=True,
    )


class AuxTagAttrsUpdate(BaseSchema):
    topic = AuxTagTopicField(
        required=False,
    )
    title = AuxTagTitleField(
        required=False,
    )

    @post_load
    def verify_at_least_one(self, *args, **kwargs):
        at_least_one_of = {"topic", "title"}
        if not at_least_one_of & set(args[0]):
            raise ValidationError(
                f"At least one of the following parameters should be provided: {at_least_one_of}"
            )
        return args[0]


EXAMPLE_AUX_TAG = {
    "id": "snmp",
    "title": "Monitoring via SNMP",
    "topic": "Monitoring agents",
}


class AuxTagResponse(DomainObject):
    domainType = fields.Constant(
        "aux_tag",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        AuxTagAttrsResponse,
        description="The Auxiliary Tag attributes.",
        example=EXAMPLE_AUX_TAG,
    )


class AuxTagResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "aux_tag",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(AuxTagResponse),
        description="A list of site configuration objects.",
        example=[
            {
                "links": [],
                "domainType": "aux_tag",
                "id": EXAMPLE_AUX_TAG["id"],
                "title": EXAMPLE_AUX_TAG["title"],
                "members": {},
                "extensions": EXAMPLE_AUX_TAG,
            }
        ],
    )
