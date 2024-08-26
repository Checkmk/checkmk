#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""RabbitMq configurations module test"""
from collections.abc import Mapping, Sequence

import pytest

from cmk.messaging import rabbitmq
from cmk.messaging._constants import DEFAULT_VHOST_NAME

from ._connections import (
    MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
    MULTISITE_CONNECTIONS_SAME_CUSTOMER,
    P2P_CONNECTIONS_PROVIDER,
    P2P_CONNECTIONS_SAME_CUSTOMER,
    SIMPLE_CONNECTION,
    SIMPLE_CONNECTION_DIFF_CUSTOMER,
)

CENTRAL_SHOVELS_REMOTE1 = [
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "dest-uri": "amqps://remote1:5672?"
            "server_name_indication=remote1&auth_mechanism=external",
            "src-uri": "amqp:///customer1",
            "src-queue": "cmk.intersite.remote1",
        },
        vhost="customer1",
        component="shovel",
        name="cmk.shovel.central->remote1",
    ),
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "src-queue": "cmk.intersite.central",
            "src-uri": "amqps://remote1:5672?"
            "server_name_indication=remote1&auth_mechanism=external",
            "dest-uri": "amqp:///customer1",
        },
        vhost="customer1",
        component="shovel",
        name="cmk.shovel.remote1->central",
    ),
]
CENTRAL_SHOVELS_REMOTE2 = [
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "dest-uri": "amqps://remote2:5672?"
            "server_name_indication=remote2&auth_mechanism=external",
            "src-queue": "cmk.intersite.remote2",
            "src-uri": "amqp:///customer1",
        },
        vhost="customer1",
        component="shovel",
        name="cmk.shovel.central->remote2",
    ),
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "src-queue": "cmk.intersite.central",
            "src-uri": "amqps://remote2:5672?"
            "server_name_indication=remote2&auth_mechanism=external",
            "dest-uri": "amqp:///customer1",
        },
        vhost="customer1",
        component="shovel",
        name="cmk.shovel.remote2->central",
    ),
]
CENTRAL_SHOVELS_REMOTE2_DIFF_CUSTOMER = [
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "dest-uri": "amqps://remote2:5672?"
            "server_name_indication=remote2&auth_mechanism=external",
            "src-queue": "cmk.intersite.remote2",
            "src-uri": "amqp:///customer2",
        },
        vhost="customer2",
        component="shovel",
        name="cmk.shovel.central->remote2",
    ),
    rabbitmq.Component(
        value={
            **rabbitmq.DEFAULT_SHOVEL,
            "src-queue": "cmk.intersite.central",
            "src-uri": "amqps://remote2:5672?"
            "server_name_indication=remote2&auth_mechanism=external",
            "dest-uri": "amqp:///customer2",
        },
        vhost="customer2",
        component="shovel",
        name="cmk.shovel.remote2->central",
    ),
]


@pytest.mark.parametrize(
    "connections, parameters",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [],
                "central": [
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "dest-uri": "amqps://remote1:5672?"
                            "server_name_indication=remote1&auth_mechanism=external",
                            "src-uri": r"amqp:///%2f",
                            "src-queue": "cmk.intersite.remote1",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.central->remote1",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.central",
                            "src-uri": "amqps://remote1:5672?"
                            "server_name_indication=remote1&auth_mechanism=external",
                            "dest-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote1->central",
                    ),
                ],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                "remote1": [],
                "central": CENTRAL_SHOVELS_REMOTE1,
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [],
                "remote2": [],
                "central": CENTRAL_SHOVELS_REMOTE1 + CENTRAL_SHOVELS_REMOTE2,
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [],
                "remote2": [],
                "central": CENTRAL_SHOVELS_REMOTE1 + CENTRAL_SHOVELS_REMOTE2_DIFF_CUSTOMER,
            },
        ),
        (
            P2P_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.remote2",
                            "src-uri": r"amqp:///%2f",
                            "dest-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote1->remote2",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.remote1",
                            "src-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                            "dest-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote2->remote1",
                    ),
                ],
                "remote2": [],
                "central": CENTRAL_SHOVELS_REMOTE1 + CENTRAL_SHOVELS_REMOTE2,
            },
        ),
        (
            P2P_CONNECTIONS_PROVIDER,
            {
                "remote1": [
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.remote2",
                            "src-uri": r"amqp:///%2f",
                            "dest-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote1->remote2",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.remote1",
                            "src-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                            "dest-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote2->remote1",
                    ),
                ],
                "remote2": [],
                "central": [
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "dest-uri": "amqps://remote1:5672?"
                            "server_name_indication=remote1&auth_mechanism=external",
                            "src-uri": r"amqp:///%2f",
                            "src-queue": "cmk.intersite.remote1",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.central->remote1",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.central",
                            "src-uri": "amqps://remote1:5672?"
                            "server_name_indication=remote1&auth_mechanism=external",
                            "dest-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote1->central",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "dest-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                            "src-queue": "cmk.intersite.remote2",
                            "src-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.central->remote2",
                    ),
                    rabbitmq.Component(
                        value={
                            **rabbitmq.DEFAULT_SHOVEL,
                            "src-queue": "cmk.intersite.central",
                            "src-uri": "amqps://remote2:5672?"
                            "server_name_indication=remote2&auth_mechanism=external",
                            "dest-uri": r"amqp:///%2f",
                        },
                        vhost=DEFAULT_VHOST_NAME,
                        component="shovel",
                        name="cmk.shovel.remote2->central",
                    ),
                ],
            },
        ),
    ],
)
def test_compute_distributed_definitions_parameters(
    connections: Sequence[rabbitmq.Connection],
    parameters: Mapping[str, Sequence[rabbitmq.Component]],
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_parameters in parameters.items():
        assert list(definitions[site_id].parameters) == site_parameters
