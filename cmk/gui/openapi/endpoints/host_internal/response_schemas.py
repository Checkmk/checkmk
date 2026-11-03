#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_registration import CONNECTION_MODE_FIELD
from cmk.gui.fields.utils import BaseSchema


class HostConnectionMode(BaseSchema):
    connection_mode = CONNECTION_MODE_FIELD
