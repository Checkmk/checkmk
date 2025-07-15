#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk import fields
from cmk.gui.fields.utils import BaseSchema


class Choice(BaseSchema):
    id = fields.String(
        description="The id of the choice.",
    )
    value = fields.String(
        description="The display value of the choice.",
    )


class ResponseSchema(BaseSchema):
    choices = fields.List(
        fields.Nested(Choice),
        description="A list of choices.",
    )
