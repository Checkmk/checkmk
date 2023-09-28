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


class PasswordExtension(BaseSchema):
    ident = fields.String(
        example="pass",
        description="The unique identifier for the password",
    )
    title = fields.String(
        example="Kubernetes login",
        description="The title for the password",
    )
    comment = fields.String(
        example="Kommentar",
        description="A comment for the password",
    )
    documentation_url = fields.String(
        example="localhost",
        attribute="docu_url",
        description="The URL pointing to documentation or any other page.",
    )
    owned_by = fields.String(
        example="admin",
        description="The owner of the password who is able to edit, delete and use existing passwords.",
    )

    shared = fields.List(
        fields.String(
            example="all",
            description="The member the password is shared with",
        ),
        example=["all"],
        attribute="shared_with",
        description="The list of members the password is shared with",
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
