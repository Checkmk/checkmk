#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""RabbitMq configurations module test: connections"""

from cmk.messaging import rabbitmq

# central -> remote1
SIMPLE_CONNECTION = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            customer="provider",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    )
]

# central -> remote1
SIMPLE_CONNECTION_DIFF_CUSTOMER = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            customer="customer1",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    )
]

# central -> remote1
#   \
#    remote2
MULTISITE_CONNECTIONS_SAME_CUSTOMER = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            customer="customer1",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            customer="customer1",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
]


MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            customer="customer1",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            customer="customer2",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
]


P2P_CONNECTIONS_SAME_CUSTOMER = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            customer="customer1",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            customer="customer1",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
            customer="provider",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            customer="customer1",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="remote1",
            customer="customer1",
        ),
    ),
]


P2P_CONNECTIONS_PROVIDER = [
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote1",
            site_server="remote1",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="central",
        ),
    ),
    rabbitmq.Connection(
        connectee=rabbitmq.Connectee(
            site_id="remote2",
            site_server="remote2",
            rabbitmq_port=5672,
        ),
        connecter=rabbitmq.Connecter(
            site_id="remote1",
        ),
    ),
]
