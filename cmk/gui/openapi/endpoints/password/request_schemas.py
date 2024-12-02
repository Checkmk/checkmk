#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class InputPassword(BaseSchema):
    ident = gui_fields.PasswordIdent(
        example="pass",
        description="The unique identifier for the password",
        should_exist=False,
    )
    title = fields.String(
        required=True,
        example="Kubernetes login",
        description="The name of your password for easy recognition.",
    )
    comment = fields.String(
        required=False,
        example="Kommentar",
        description="An optional comment to explain the purpose of this password.",
        load_default="",
    )
    documentation_url = fields.String(
        required=False,
        attribute="docu_url",
        example="localhost",
        description="An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
        load_default="",
    )
    password = fields.String(
        required=True,
        example="password",
        description="The password string",
        minLength=1,
    )
    # TODO: DEPRECATED(17274) - remove in 2.5
    owner = gui_fields.PasswordEditableBy(
        example="admin",
        description="Deprecated - use `editable_by` instead. Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="owned_by",
        deprecated=True,
    )
    editable_by = gui_fields.PasswordEditableBy(
        example="admin",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords. By default, the admin group is the owner of a password.",
        required=False,
    )
    shared = fields.List(
        gui_fields.PasswordShare(
            example="all",
            description="By default only the members of the owner contact group are permitted to use a configured password. It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="shared_with",
        load_default=list,
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
        allow_global=True,
    )


class UpdatePassword(BaseSchema):
    title = fields.String(
        required=False,
        example="Kubernetes login",
        description="The name of your password for easy recognition.",
    )
    comment = fields.String(
        required=False,
        example="Kommentar",
        description="An optional comment to explain the purpose of this password.",
    )
    documentation_url = fields.String(
        required=False,
        attribute="docu_url",
        example="localhost",
        description="An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
    )
    password = fields.String(
        required=False,
        example="password",
        description="The password string",
        minLength=1,
    )
    # TODO: DEPRECATED(17274) - remove in 2.5
    owner = gui_fields.PasswordEditableBy(
        example="admin",
        description="Deprecated - use `editable_by` instead. Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="owned_by",
        deprecated=True,
    )
    editable_by = gui_fields.PasswordEditableBy(
        example="admin",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
    )
    shared = fields.List(
        gui_fields.PasswordShare(
            example="all",
            description="By default only the members of the owner contact group are permitted to use a a configured password. "
            "It is possible to share a password with other groups of users to make them able to use a password in checks.",
        ),
        example=["all"],
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        required=False,
        attribute="shared_with",
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
    )
