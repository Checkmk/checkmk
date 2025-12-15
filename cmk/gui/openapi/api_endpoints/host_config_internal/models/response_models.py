#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.utils.agent_registration import HostAgentConnectionMode


@api_model
class ConnectionMode:
    # TODO: here some validation if the HostAgentConnectionMode exists in the edition is still outstanding
    #  see: cmk/gui/agent_registration/fields.py

    connection_mode: HostAgentConnectionMode = api_field(
        description="This configures the communication direction of this host.\n"
        f" * `{HostAgentConnectionMode.PULL.value}` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
        f" * `{HostAgentConnectionMode.PUSH.value}` - the host is expected to send the data to the monitoring server without being triggered\n"
    )
