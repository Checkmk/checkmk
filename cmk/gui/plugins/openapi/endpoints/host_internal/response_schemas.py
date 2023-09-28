#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_registration import CONNECTION_MODE_FIELD
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class ConnectionMode(BaseSchema):
    connection_mode = CONNECTION_MODE_FIELD


class HostConfigSchemaInternal(BaseSchema):
    site = fields.String(
        required=True,
        description="The site the host is monitored on.",
    )
    is_cluster = fields.Boolean(
        required=True,
        description="Indicates if the host is a cluster host.",
    )
