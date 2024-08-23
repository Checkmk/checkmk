#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module for RabbitMq definitions creation"""
import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel

from ._constants import DEFAULT_VHOST_NAME, INTERSITE_EXCHANGE

_logger = logging.getLogger(__name__)


class User(BaseModel):
    name: str
    tags: tuple[str, ...] = ()


class Permission(BaseModel):
    user: str
    vhost: str
    configure: str
    write: str
    read: str


class Policy(BaseModel):
    # Define the fields for the Policy model here
    pass


class Exchange(BaseModel):
    name: str
    vhost: str
    type: str
    durable: bool
    auto_delete: bool
    internal: bool
    arguments: Mapping[str, str]


class Binding(BaseModel):
    source: str
    vhost: str
    destination: str
    destination_type: str
    routing_key: str
    arguments: Mapping[str, str]


class VirtualHost(BaseModel):
    name: str


DEFAULT_SHOVEL: Mapping[str, str | bool] = {
    "ack-mode": "on-confirm",
    "dest-add-forward-headers": False,
    "dest-exchange": INTERSITE_EXCHANGE,
    "dest-protocol": "amqp091",
    "dest-uri": "amqp://",
    "src-delete-after": "never",
    "src-protocol": "amqp091",
    "src-queue": "",
    "src-uri": "amqp://",
}


class Component(BaseModel):
    value: Mapping[str, str | bool]
    vhost: str
    component: str
    name: str


class Queue(BaseModel):
    name: str
    vhost: str
    durable: bool
    auto_delete: bool
    arguments: Mapping[str, str]


class Definitions(BaseModel):
    users: list[User] = []
    vhosts: list[VirtualHost] = []
    permissions: list[Permission] = []
    policies: list[Policy] = []
    exchanges: list[Exchange] = []
    bindings: list[Binding] = []
    queues: list[Queue] = []
    parameters: list[Component] = []


@dataclass(frozen=True)
class Connecter:
    site_id: str
    customer: str = "provider"


@dataclass(frozen=True)
class Connectee:
    site_id: str
    site_server: str
    rabbitmq_port: int
    customer: str = "provider"


@dataclass(frozen=True)
class Connection:
    connectee: Connectee
    connecter: Connecter


def find_shortest_paths(
    edges: Sequence[tuple[str, str]]
) -> Mapping[tuple[str, str], tuple[str, ...]]:

    known_paths: dict[tuple[str, str], tuple[str, ...]] = {
        (start, end): (start, end) for start, end in edges
    }
    known_paths.update({(end, start): (end, start) for start, end in edges})

    neighbors = defaultdict(set)
    for start, end in edges:
        neighbors[start].add(end)
        neighbors[end].add(start)

    while new_paths := {
        (start, neighbor): path + (neighbor,)
        for (start, end), path in known_paths.items()
        for neighbor in neighbors[end]
        if neighbor not in path and (start, neighbor) not in known_paths
    }:

        known_paths.update(new_paths)

    return known_paths


def _connecting_customer(connection: Connection) -> str:
    if connection.connecter.customer == connection.connectee.customer:
        return connection.connecter.customer
    if "provider" in [connection.connecter.customer, connection.connectee.customer]:
        return (
            connection.connecter.customer
            if connection.connecter.customer != "provider"
            else connection.connectee.customer
        )
    raise ValueError("Invalid connection customers")


def _base_definitions(
    connections: Sequence[Connection],
) -> tuple[defaultdict[str, Definitions], Mapping[str, Sequence[tuple[str, str]]]]:

    connecting_definitions: defaultdict[str, Definitions] = defaultdict(Definitions)
    edges_by_customer = defaultdict(list)
    for c in connections:
        add_connecter_definitions(c, connecting_definitions[c.connecter.site_id])
        add_connectee_definitions(c, connecting_definitions[c.connectee.site_id])

        customer = _connecting_customer(c)
        edges_by_customer[customer].append((c.connecter.site_id, c.connectee.site_id))

    return connecting_definitions, edges_by_customer


def compute_distributed_definitions(
    connections: Sequence[Connection],
) -> Mapping[str, Definitions]:

    connecting_definitions, edges_by_customer = _base_definitions(connections)

    def _add_binding(_from: str, _to: str, through: str) -> None:

        binding_site1 = Binding(
            source=INTERSITE_EXCHANGE,
            vhost=DEFAULT_VHOST_NAME,
            destination=f"cmk.intersite.{through}",
            destination_type="queue",
            routing_key=f"{_to}.#",
            arguments={},
        )

        if binding_site1 in connecting_definitions[_from].bindings:
            # should never happen
            return

        connecting_definitions[_from].bindings.append(binding_site1)

    bindings_present = set()
    shortest_paths: dict[tuple[str, str], tuple[str, ...]] = {}
    for _customer, connection in edges_by_customer.items():
        shortest_paths.update(find_shortest_paths(connection))

    for ori_dest, path in shortest_paths.items():
        for i in range(1, len(path) - 1):
            binding_group = (path[i - 1], ori_dest[1], path[i])  # from, to, through
            if binding_group in bindings_present:
                continue
            _add_binding(*binding_group)
            bindings_present.add(binding_group)

    return connecting_definitions


def _get_vhost_from_connection(connection: Connection) -> tuple[str, str]:

    if connection.connecter.customer == connection.connectee.customer:
        return (DEFAULT_VHOST_NAME, r"%2f")

    customer = _connecting_customer(connection)
    return (f"{customer}", f"{customer}")


def add_connecter_definitions(connection: Connection, definition: Definitions) -> None:

    user = User(name=connection.connectee.site_id)
    vhost_name, v_host_uri = _get_vhost_from_connection(connection)

    if vhost_name != DEFAULT_VHOST_NAME:
        vhost = VirtualHost(name=vhost_name)
        if vhost not in definition.vhosts:
            definition.vhosts.append(vhost)

        exchange = Exchange(
            name=INTERSITE_EXCHANGE,
            vhost=vhost_name,
            type="topic",
            durable=True,
            auto_delete=False,
            internal=False,
            arguments={},
        )
        if exchange not in definition.exchanges:
            definition.exchanges.append(exchange)

    connectee_url: str = (
        f"amqps://{connection.connectee.site_server}:"
        f"{connection.connectee.rabbitmq_port}?server_name_indication="
        f"{connection.connectee.site_id}&auth_mechanism=external"
    )
    connecter_url: str = f"amqp:///{v_host_uri}"

    permission = Permission(
        user=user.name,
        vhost=vhost_name,
        configure="^$",
        write=INTERSITE_EXCHANGE,
        read="cmk.intersite..*",
    )
    queue = Queue(
        name=f"cmk.intersite.{connection.connectee.site_id}",
        vhost=vhost_name,
        durable=True,
        auto_delete=False,
        arguments={},
    )
    binding = Binding(
        source=INTERSITE_EXCHANGE,
        vhost=vhost_name,
        destination=queue.name,
        destination_type="queue",
        routing_key=f"{connection.connectee.site_id}.#",
        arguments={},
    )
    parameters = [
        Component(
            value={
                **DEFAULT_SHOVEL,
                "src-uri": connecter_url,
                "dest-uri": connectee_url,
                "src-queue": queue.name,
            },
            vhost=vhost_name,
            component="shovel",
            name=f"cmk.shovel.{connection.connecter.site_id}->{connection.connectee.site_id}",
        ),
        Component(
            value={
                **DEFAULT_SHOVEL,
                "src-queue": f"cmk.intersite.{connection.connecter.site_id}",
                "src-uri": connectee_url,
                "dest-uri": connecter_url,
            },
            vhost=vhost_name,
            component="shovel",
            name=f"cmk.shovel.{connection.connectee.site_id}->{connection.connecter.site_id}",
        ),
    ]

    definition.users.append(user)
    definition.permissions.append(permission)
    definition.queues.append(queue)
    definition.bindings.append(binding)
    definition.parameters.extend(parameters)


def add_connectee_definitions(connection: Connection, definition: Definitions) -> None:

    user = User(name=connection.connecter.site_id)
    permission = Permission(
        user=user.name,
        vhost=DEFAULT_VHOST_NAME,
        configure="^$",
        write=INTERSITE_EXCHANGE,
        read="cmk.intersite..*",
    )
    queue = Queue(
        name=f"cmk.intersite.{connection.connecter.site_id}",
        vhost=DEFAULT_VHOST_NAME,
        durable=True,
        auto_delete=False,
        arguments={},
    )

    # only add binding on default vhost if the connection is within the same customer
    if connection.connecter.customer == connection.connectee.customer:
        binding = Binding(
            source=INTERSITE_EXCHANGE,
            vhost=DEFAULT_VHOST_NAME,
            destination=queue.name,
            destination_type="queue",
            routing_key=f"{connection.connecter.site_id}.#",
            arguments={},
        )
        definition.bindings.append(binding)

    definition.users.append(user)
    definition.permissions.append(permission)
    definition.queues.append(queue)
