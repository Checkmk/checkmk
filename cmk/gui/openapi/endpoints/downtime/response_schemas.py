#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection


class BaseDowntimeSchema(BaseSchema):
    site_id = gui_fields.SiteField(
        description="The site id of the downtime.",
        example="heute",
        presence="should_exist",
        required=True,
    )
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
    recurring = fields.Boolean(
        required=True,
        description="Indicates if this downtime is time-repetitive",
        example=True,
    )
    comment = fields.String(
        required=True,
        description="A comment text.",
        example="Down for update",
    )


class HostDowntimeAttributes(BaseDowntimeSchema):
    is_service = fields.Constant(
        False, description="Host downtime entry", example=False, required=True
    )


class ServiceDowntimeAttributes(BaseDowntimeSchema):
    is_service = fields.Constant(
        True, description="Service downtime entry", example=True, required=False
    )
    service_description = fields.String(
        required=True,
        description="The service name if the downtime corresponds to a service, otherwise this field is not present.",
        example="CPU Load",
    )


class DowntimeAttributes(OneOfSchema):
    type_field = "is_service"
    type_schemas = {
        "host": HostDowntimeAttributes,
        "service": ServiceDowntimeAttributes,
    }
    type_field_remove = False

    def get_obj_type(self, obj):
        is_service = "service" if obj.get("is_service", False) else "host"
        if is_service in self.type_schemas:
            return is_service

        raise Exception("Unknown object type: %s" % repr(obj))

    def dump(self, obj, *, many=None, **kwargs):
        data = super().dump(obj, many=many, **kwargs)
        if "is_service" in data:
            data["is_service"] = data["is_service"] == "service"
        return data


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
