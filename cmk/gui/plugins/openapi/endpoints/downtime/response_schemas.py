#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)

from cmk import fields


class DowntimeAttributes(BaseSchema):
    host_name = gui_fields.HostField(
        required=True,
        description="The host name.",
        example="cmk.abc.ch",
    )
    author = fields.String(
        required=True,
        description="The author of the downtime.",
        example="Mr Bojangles",
    )
    is_service = fields.String(
        required=True,
        description="yes, if this entry is for a service, no if it is for a host.",
        example="yes",
    )
    start_time = gui_fields.Timestamp(
        required=True,
        description="The start time of the downtime.",
        example="2023-08-04T08:58:01+00:00",
    )
    end_time = gui_fields.Timestamp(
        required=True,
        description="The end time of the downtime.",
        example="2023-08-04T09:18:01+00:00",
    )
    recurring = fields.String(
        required=True,
        description="yes if the downtime is recurring, no if it is not.",
        example="yes",
    )
    comment = fields.String(
        required=True,
        description="A comment text.",
        example="Down for update",
    )


class DowntimeObject(DomainObject):
    domainType = fields.Constant(
        "downtime",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        DowntimeAttributes,
        description="The attributes of a downtime.",
    )


class DowntimeCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "downtime",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(DowntimeObject),
        description="A list of downtime objects.",
    )
