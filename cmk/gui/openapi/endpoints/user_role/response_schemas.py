#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import builtin_role_ids
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields


class UserRoleAttributes(BaseSchema):
    alias = fields.String(required=True, description="The alias of the user role.")
    permissions = fields.List(
        fields.String(),
        required=True,
        description="A list of permissions for the user role. ",
    )
    builtin = fields.Boolean(
        required=True,
        description="True if it's a built-in user role, otherwise False.",
    )
    basedon = fields.String(
        enum=builtin_role_ids,
        required=False,
        description="The built-in user role id that the user role is based on.",
    )


class UserRoleObject(DomainObject):
    domainType = fields.Constant(
        "user_role",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(UserRoleAttributes, description="All the attributes of a user role.")


class UserRoleCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "user_role",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(UserRoleObject),
        description="A list of user role objects.",
    )
