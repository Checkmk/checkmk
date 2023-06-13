#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)

from cmk import fields


class ServiceGroup(DomainObject):
    domainType = fields.Constant(
        "service_group_config",
        description="The domain type of the object.",
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
