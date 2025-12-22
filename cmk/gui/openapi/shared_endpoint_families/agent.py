#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

AGENTS_FAMILY = EndpointFamily(
    name="Agents",
    description=(
        """

An agent is a small program that is installed on a host in order for Checkmk to be able to query
data from the host.

Checkmk can configure its agents individually, create (or bake) them in this configuration as
a package, sign them and update them automatically.
Agents can also update themselves once they have registered with the server.

You can find an introduction to agents
in the [Checkmk guide](https://docs.checkmk.com/latest/en/wato_monitoringagents.html)
and more information about the Agent Bakery in
[Automatic agent updates](https://docs.checkmk.com/latest/en/agent_deployment.html).

        """
    ),
    doc_group="Setup",
)
