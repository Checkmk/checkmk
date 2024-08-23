#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""RabbitMq configurations module test"""
from collections.abc import Mapping, Sequence

import pytest

from cmk.messaging import rabbitmq
from cmk.messaging._constants import DEFAULT_VHOST_NAME

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


@pytest.mark.parametrize(
    "connections, vhosts",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [
                    # this will be in the defaul config
                    # rabbitmq.VirtualHost(name=DEFAULT_VHOST_NAME),
                ],
                "central": [
                    # this will be in the defaul config
                    # rabbitmq.VirtualHost(name=DEFAULT_VHOST_NAME),
                ],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                "remote1": [],
                "central": [rabbitmq.VirtualHost(name="customer1")],
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [],
                "central": [rabbitmq.VirtualHost(name="customer1")],
                "remote2": [],
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [],
                "central": [
                    rabbitmq.VirtualHost(name="customer1"),
                    rabbitmq.VirtualHost(name="customer2"),
                ],
                "remote2": [],
            },
        ),
    ],
)
def test_compute_distributed_definitions_vhosts(
    connections: Sequence[rabbitmq.Connection], vhosts: Mapping[str, Sequence[rabbitmq.VirtualHost]]
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_vhosts in vhosts.items():
        assert definitions[site_id].vhosts == site_vhosts


@pytest.mark.parametrize(
    "connections, bindings",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost=DEFAULT_VHOST_NAME,
                        destination="cmk.intersite.central",
                        destination_type="queue",
                        routing_key="central.#",
                        arguments={},
                    ),
                ],
                "central": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost=DEFAULT_VHOST_NAME,
                        destination="cmk.intersite.remote1",
                        destination_type="queue",
                        routing_key="remote1.#",
                        arguments={},
                    ),
                ],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                "remote1": [],
                "central": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost="customer1",
                        destination="cmk.intersite.remote1",
                        destination_type="queue",
                        routing_key="remote1.#",
                        arguments={},
                    ),
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost=DEFAULT_VHOST_NAME,
                        destination="cmk.intersite.central",
                        destination_type="queue",
                        routing_key="remote2.#",
                        arguments={},
                    ),
                ],
                "central": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost="customer1",
                        destination="cmk.intersite.remote1",
                        destination_type="queue",
                        routing_key="remote1.#",
                        arguments={},
                    ),
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost="customer1",
                        destination="cmk.intersite.remote2",
                        destination_type="queue",
                        routing_key="remote2.#",
                        arguments={},
                    ),
                ],
                "remote2": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost=DEFAULT_VHOST_NAME,
                        destination="cmk.intersite.central",
                        destination_type="queue",
                        routing_key="remote1.#",
                        arguments={},
                    ),
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [],
                "central": [
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost="customer1",
                        destination="cmk.intersite.remote1",
                        destination_type="queue",
                        routing_key="remote1.#",
                        arguments={},
                    ),
                    rabbitmq.Binding(
                        source="cmk.intersite",
                        vhost="customer2",
                        destination="cmk.intersite.remote2",
                        destination_type="queue",
                        routing_key="remote2.#",
                        arguments={},
                    ),
                ],
                "remote2": [],
            },
        ),
    ],
)
def test_compute_distributed_definitions_bindings(
    connections: Sequence[rabbitmq.Connection], bindings: Mapping[str, Sequence[rabbitmq.Binding]]
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    def _key(bind: rabbitmq.Binding) -> str:
        return bind.routing_key

    for site_id, site_bindings in bindings.items():
        assert sorted(definitions[site_id].bindings, key=_key) == site_bindings


@pytest.mark.parametrize(
    "connections, users",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [rabbitmq.User(name="central")],
                "central": [rabbitmq.User(name="remote1")],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                "remote1": [rabbitmq.User(name="central")],
                "central": [rabbitmq.User(name="remote1")],
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [rabbitmq.User(name="central")],
                "remote2": [rabbitmq.User(name="central")],
                "central": [rabbitmq.User(name="remote1"), rabbitmq.User(name="remote2")],
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [rabbitmq.User(name="central")],
                "remote2": [rabbitmq.User(name="central")],
                "central": [rabbitmq.User(name="remote1"), rabbitmq.User(name="remote2")],
            },
        ),
    ],
)
def test_compute_distributed_definitions_users(
    connections: Sequence[rabbitmq.Connection], users: Mapping[str, Sequence[rabbitmq.User]]
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_users in users.items():
        assert list(definitions[site_id].users) == site_users


@pytest.mark.parametrize(
    "connections, permissions",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "central": [
                    rabbitmq.Permission(
                        user="remote1",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "central": [
                    rabbitmq.Permission(
                        user="remote1",
                        vhost="customer1",
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "remote2": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "central": [
                    rabbitmq.Permission(
                        user="remote1",
                        vhost="customer1",
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    ),
                    rabbitmq.Permission(
                        user="remote2",
                        vhost="customer1",
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    ),
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "remote2": [
                    rabbitmq.Permission(
                        user="central",
                        vhost=DEFAULT_VHOST_NAME,
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    )
                ],
                "central": [
                    rabbitmq.Permission(
                        user="remote1",
                        vhost="customer1",
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    ),
                    rabbitmq.Permission(
                        user="remote2",
                        vhost="customer2",
                        configure="^$",
                        write="cmk.intersite",
                        read="cmk.intersite..*",
                    ),
                ],
            },
        ),
    ],
)
def test_compute_distributed_definitions_permissions(
    connections: Sequence[rabbitmq.Connection],
    permissions: Mapping[str, Sequence[rabbitmq.Permission]],
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_permissions in permissions.items():
        assert list(definitions[site_id].permissions) == site_permissions


@pytest.mark.parametrize(
    "connections, queues",
    [
        (
            SIMPLE_CONNECTION,
            {
                "remote1": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "central": [
                    rabbitmq.Queue(
                        name="cmk.intersite.remote1",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
            },
        ),
        (
            SIMPLE_CONNECTION_DIFF_CUSTOMER,
            {
                # is this queue correct?
                "remote1": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "central": [
                    rabbitmq.Queue(
                        name="cmk.intersite.remote1",
                        vhost="customer1",
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_SAME_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "remote2": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "central": [
                    rabbitmq.Queue(
                        name="cmk.intersite.remote1",
                        vhost="customer1",
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    ),
                    rabbitmq.Queue(
                        name="cmk.intersite.remote2",
                        vhost="customer1",
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    ),
                ],
            },
        ),
        (
            MULTISITE_CONNECTIONS_DIFFERENT_CUSTOMER,
            {
                "remote1": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "remote2": [
                    rabbitmq.Queue(
                        name="cmk.intersite.central",
                        vhost=DEFAULT_VHOST_NAME,
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    )
                ],
                "central": [
                    rabbitmq.Queue(
                        name="cmk.intersite.remote1",
                        vhost="customer1",
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    ),
                    rabbitmq.Queue(
                        name="cmk.intersite.remote2",
                        vhost="customer2",
                        durable=True,
                        auto_delete=False,
                        arguments={},
                    ),
                ],
            },
        ),
    ],
)
def test_compute_distributed_definitions_queues(
    connections: Sequence[rabbitmq.Connection], queues: Mapping[str, Sequence[rabbitmq.Queue]]
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_queues in queues.items():
        assert list(definitions[site_id].queues) == site_queues


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
    ],
)
def test_compute_distributed_definitions_parameters(
    connections: Sequence[rabbitmq.Connection],
    parameters: Mapping[str, Sequence[rabbitmq.Component]],
) -> None:

    definitions = rabbitmq.compute_distributed_definitions(connections)

    for site_id, site_parameters in parameters.items():
        assert list(definitions[site_id].parameters) == site_parameters


@pytest.mark.parametrize(
    "edges, shortest_paths",
    [
        (
            [("A", "B"), ("B", "C"), ("C", "D")],
            # A -- B -- C -- D
            {
                ("A", "B"): ("A", "B"),
                ("A", "C"): ("A", "B", "C"),
                ("B", "D"): ("B", "C", "D"),
                ("B", "C"): ("B", "C"),
                ("C", "D"): ("C", "D"),
                ("B", "A"): ("B", "A"),
                ("C", "B"): ("C", "B"),
                ("C", "A"): ("C", "B", "A"),
                ("D", "A"): ("D", "C", "B", "A"),
                ("D", "B"): ("D", "C", "B"),
                ("A", "D"): ("A", "B", "C", "D"),
                ("D", "C"): ("D", "C"),
            },
        ),
        (
            [("A", "B"), ("B", "C"), ("A", "C")],
            #      A
            #     / \
            #    B---C
            {
                ("A", "B"): ("A", "B"),
                ("A", "C"): ("A", "C"),
                ("B", "C"): ("B", "C"),
                ("B", "A"): ("B", "A"),
                ("C", "B"): ("C", "B"),
                ("C", "A"): ("C", "A"),
            },
        ),
        (
            [("A", "B"), ("B", "C"), ("A", "C"), ("C", "D"), ("D", "E")],
            #      A
            #     / \
            #    B---C
            #       /
            #      D
            #       \
            #        E
            {
                ("A", "B"): ("A", "B"),
                ("A", "C"): ("A", "C"),
                ("A", "D"): ("A", "C", "D"),
                ("A", "E"): ("A", "C", "D", "E"),
                ("B", "C"): ("B", "C"),
                ("B", "D"): ("B", "C", "D"),
                ("B", "E"): ("B", "C", "D", "E"),
                ("C", "D"): ("C", "D"),
                ("C", "E"): ("C", "D", "E"),
                ("D", "E"): ("D", "E"),
                ("B", "A"): ("B", "A"),
                ("C", "A"): ("C", "A"),
                ("C", "B"): ("C", "B"),
                ("D", "A"): ("D", "C", "A"),
                ("D", "B"): ("D", "C", "B"),
                ("D", "C"): ("D", "C"),
                ("E", "A"): ("E", "D", "C", "A"),
                ("E", "B"): ("E", "D", "C", "B"),
                ("E", "C"): ("E", "D", "C"),
                ("E", "D"): ("E", "D"),
            },
        ),
    ],
)
def test_find_shortest_path(
    edges: list[tuple[str, str]], shortest_paths: Mapping[tuple[str, str], tuple[str, ...]]
) -> None:
    assert rabbitmq.find_shortest_paths(edges) == shortest_paths
