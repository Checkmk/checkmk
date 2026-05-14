#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, Table, TextField, Title, View

node_software_applications_ibm_mq = Node(
    name="software_applications_ibm_mq",
    path=["software", "applications", "ibm_mq"],
    title=Title("IBM MQ"),
    attributes={
        "managers": TextField(Title("Managers")),
        "channels": TextField(Title("Channels")),
        "queues": TextField(Title("Queues")),
    },
)

node_software_applications_ibm_mq_channels = Node(
    name="software_applications_ibm_mq_channels",
    path=["software", "applications", "ibm_mq", "channels"],
    title=Title("IBM MQ channels"),
    table=Table(
        view=View(name="invibmmqchannels", title=Title("IBM MQ channels")),
        columns={
            "qmgr": TextField(Title("Queue manager name")),
            "name": TextField(Title("Channel")),
            "type": TextField(Title("Type")),
            "status": TextField(Title("Status")),
            "monchl": TextField(Title("Monitoring")),
        },
    ),
)

node_software_applications_ibm_mq_managers = Node(
    name="software_applications_ibm_mq_managers",
    path=["software", "applications", "ibm_mq", "managers"],
    title=Title("IBM MQ managers"),
    table=Table(
        view=View(name="invibmmqmanagers", title=Title("IBM MQ managers")),
        columns={
            "name": TextField(Title("Queue manager name")),
            "instver": TextField(Title("Version")),
            "instname": TextField(Title("Installation")),
            "status": TextField(Title("Status")),
            "standby": TextField(Title("Standby")),
            "ha": TextField(Title("HA")),
        },
    ),
)

node_software_applications_ibm_mq_queues = Node(
    name="software_applications_ibm_mq_queues",
    path=["software", "applications", "ibm_mq", "queues"],
    title=Title("IBM MQ queues"),
    table=Table(
        view=View(name="invibmmqqueues", title=Title("IBM MQ queues")),
        columns={
            "qmgr": TextField(Title("Queue manager name")),
            "name": TextField(Title("Queue")),
            "maxdepth": TextField(Title("Max depth")),
            "maxmsgl": TextField(Title("Max length")),
            "created": TextField(Title("Created")),
            "altered": TextField(Title("Altered")),
            "monq": TextField(Title("Monitoring")),
        },
    ),
)
