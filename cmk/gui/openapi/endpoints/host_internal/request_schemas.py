#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui.fields.utils import BaseSchema


class LinkHostUUID(BaseSchema):
    uuid = fields.UUID(
        required=True,
        example="34e4c967-1591-4883-8cdf-0e335b09618d",
        description="A valid UUID.",
    )


class RegisterHost(BaseSchema):
    uuid = fields.UUID(
        required=True,
        example="34e4c967-1591-4883-8cdf-0e335b09618d",
        description="A valid UUID.",
    )
