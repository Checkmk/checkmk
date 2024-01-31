#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields


class HostTagOutput(BaseSchema):
    id = fields.String(description="The unique identifier of this host tag", allow_none=True)
    title = fields.String(description="The title of this host tag")
    aux_tags = fields.List(fields.String(), description="The auxiliary tags this tag included in.")


class HostTagExtensions(BaseSchema):
    topic = fields.String(description="The topic this host tag group is organized in.")
    tags = fields.List(
        fields.Nested(HostTagOutput()), description="The list of tags in this group."
    )
    help = fields.String(description="A help description for the tag group")


class ConcreteHostTagGroup(DomainObject):
    domainType = fields.Constant(
        "host_tag_group",
        required=True,
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        HostTagExtensions(), description="Additional fields for objects of this type."
    )


class HostTagGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "host_tag_group",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ConcreteHostTagGroup()),
        description="A list of host tag group objects.",
    )
