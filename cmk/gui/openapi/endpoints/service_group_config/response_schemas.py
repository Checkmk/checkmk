#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import customer_field_response
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection


class ServiceGroupExtensions(BaseSchema):
    customer = customer_field_response()


class ServiceGroup(DomainObject):
    domainType = fields.Constant(
        "service_group_config",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        ServiceGroupExtensions,
        description="All the attributes of the domain object.",
    )


class ServiceGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "service_group_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ServiceGroup),
        description="A list of service group objects.",
    )
