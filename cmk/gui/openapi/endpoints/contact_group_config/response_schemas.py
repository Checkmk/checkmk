#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import customer_field_response
from cmk.gui.openapi.endpoints.contact_group_config.common import InventoryPaths
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields


class ContactGroupExtensions(BaseSchema):
    customer = customer_field_response()
    inventory_paths = fields.Nested(
        InventoryPaths,
        description="Permitted HW/SW Inventory paths.",
    )


class ContactGroup(DomainObject):
    domainType = fields.Constant(
        "contact_group_config",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        ContactGroupExtensions,
        description="All the attributes of the domain object.",
    )


class ContactGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "contact_group_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ContactGroup),
        description="A list of contact group objects.",
    )
