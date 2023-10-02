#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.watolib.objref import ObjectRefType

from cmk import fields

object_types = ["All", "None"] + [t.name for t in ObjectRefType]

object_type_field = fields.String(
    required=False,
    description="The type of object we want to filter on",
    enum=object_types,
    example="Folder",
    load_default="All",
)

object_name_field = fields.String(
    required=False,
    description="Name of an object to filter by",
    example="host_01",
    attribute="object_ident",
)

user_id_field = fields.String(
    required=False, description="An username to filter by", example="my_admin_user"
)

regexp_field = fields.String(
    required=False,
    description="A regular expression to be applied to the user_id, action and summary fields.",
    example="^l.*m.*p",
    attribute="filter_regex",
)

date_field = fields.Date(
    format="iso8601",
    required=True,
    example="2017-07-21",
    description="The date from wich to obtain the audit log entries. The format has to conform to the ISO 8601 profile",
)
