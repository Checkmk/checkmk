#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection


class PasswordExtension(BaseSchema):
    comment = fields.String(
        example="Kommentar",
        description="An optional comment to explain the purpose of this password.",
    )
    documentation_url = fields.String(
        example="localhost",
        attribute="docu_url",
        description="A URL pointing to documentation or any other page.",
    )
    # TODO: DEPRECATED(17274) - remove in 2.5
    owned_by = fields.String(
        example="admin",
        description="Deprecated - use `editable_by` instead. The owner of the password who is able to edit, delete and use existing passwords.",
        deprecated=True,
    )
    editable_by = fields.String(
        example="admin",
        description="The owner of the password who is able to edit, delete and use existing passwords.",
        dump_only=True,  # marshmallow magic, this allows us to copy the value of "owned_by"
        attribute="owned_by",
    )
    shared = fields.List(
        fields.String(
            example="all",
            description="By default only the members of the owner contact group are permitted to use a configured password. It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        attribute="shared_with",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
    )


class PasswordObject(DomainObject):
    domainType = fields.Constant(
        "password",
        description="The type of the domain-object.",
    )
    extensions = fields.Nested(
        PasswordExtension,
        description="All the attributes of the domain object.",
    )


class PasswordCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "password",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(PasswordObject),
        description="A list of password objects.",
    )
