#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module for RabbitMq definitions creation"""

import subprocess
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from ._constants import DEFAULT_VHOST_NAME, INTERSITE_EXCHANGE

DEFAULT_DEFINITIONS_FILE_NAME = "00-default.json"
ACTIVE_DEFINITIONS_FILE_NAME = "definitions.json"

DEFINITIONS_PATH = "etc/rabbitmq/definitions.d"
ACTIVE_DEFINITIONS_FILE_PATH = f"{DEFINITIONS_PATH}/{ACTIVE_DEFINITIONS_FILE_NAME}"
NEW_DEFINITIONS_FILE_PATH = f"{DEFINITIONS_PATH}/definitions.next.json"

# this defines the default message ttl for all the messages in the queue
# we opted for this instead of per-message TTL because when setting per-message TTL
# expired messages can queue up behind non-expired ones until the latter are consumed or expired.
# Hence resources used by such expired messages will not be freed.
# see https://www.rabbitmq.com/docs/ttl
QUEUE_DEFAULT_MESSAGE_TTL = {"x-message-ttl": 60000}

# maximum dimension of the queue in bytes
# the queue will drop old messages when the size exceeds this value
# see https://www.rabbitmq.com/docs/maxlength
QUEUE_DEFAULT_MAX_LENGTH_BYTES = {"x-max-length-bytes": 1073741824}  # 1GB


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


class ShovelValue(BaseModel):
    ack_mode: str = Field(alias="ack-mode", default="on-confirm")
    dest_add_forward_headers: bool = Field(alias="dest-add-forward-headers", default=False)
    dest_exchange: str = Field(alias="dest-exchange", default=INTERSITE_EXCHANGE)
    dest_protocol: str = Field(alias="dest-protocol", default="amqp091")
    dest_uri: str = Field(alias="dest-uri", default="amqp://")
    src_delete_after: str = Field(alias="src-delete-after", default="never")
    src_protocol: str = Field(alias="src-protocol", default="amqp091")
    src_queue: str = Field(alias="src-queue")
    src_uri: str = Field(alias="src-uri", default="amqp://")

    model_config = ConfigDict(
        populate_by_name=True,
        frozen=True,
    )

    @classmethod
    def from_kwargs(cls, *, src_queue: str, src_uri: str, dest_uri: str) -> Self:
        return cls(src_queue=src_queue, src_uri=src_uri, dest_uri=dest_uri)


class Shovel(BaseModel, frozen=True):
    value: ShovelValue
    vhost: str
    component: Literal["shovel"] = "shovel"
    name: str


class Queue(BaseModel):
    name: str
    vhost: str
    durable: bool
    auto_delete: bool
    arguments: Mapping[str, str | int]


class Definitions(BaseModel):
    users: list[User] = []
    vhosts: list[VirtualHost] = []
    permissions: list[Permission] = []
    policies: list[Policy] = []
    exchanges: list[Exchange] = []
    bindings: list[Binding] = []
    queues: list[Queue] = []
    parameters: list[Shovel] = []  # there are others, we currently only need shovels.

    def dumps(self) -> str:
        return self.model_dump_json(indent=4, by_alias=True)

    @classmethod
    def loads(cls, data: str) -> Self:
        return cls.model_validate_json(data)


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


def make_default_remote_user_permission(user_name: str) -> Permission:
    return Permission(
        user=user_name,
        vhost=DEFAULT_VHOST_NAME,
        configure="^$",
        write=INTERSITE_EXCHANGE,
        read="cmk.intersite..*",
    )


def find_shortest_paths(
    edges: Sequence[tuple[str, str]],
) -> Mapping[tuple[str, str], tuple[str, ...]]:
    """
    >>> sorted(find_shortest_paths([]).items())
    []
    >>> sorted(find_shortest_paths([("a", "b"), ("b", "c"), ("a", "c")]).items())
    [(('a', 'b'), ('a', 'b')), (('a', 'c'), ('a', 'c')), (('b', 'a'), ('b', 'a')), (('b', 'c'), ('b', 'c')), (('c', 'a'), ('c', 'a')), (('c', 'b'), ('c', 'b'))]
    """
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
        arguments={**QUEUE_DEFAULT_MESSAGE_TTL, **QUEUE_DEFAULT_MAX_LENGTH_BYTES},
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
        Shovel(
            value=ShovelValue.from_kwargs(
                src_uri=connecter_url,
                dest_uri=connectee_url,
                src_queue=queue.name,
            ),
            vhost=vhost_name,
            name=f"cmk.shovel.{connection.connecter.site_id}->{connection.connectee.site_id}",
        ),
        Shovel(
            value=ShovelValue.from_kwargs(
                src_queue=f"cmk.intersite.{connection.connecter.site_id}",
                src_uri=connectee_url,
                dest_uri=connecter_url,
            ),
            vhost=vhost_name,
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
    permission = make_default_remote_user_permission(user.name)
    queue = Queue(
        name=f"cmk.intersite.{connection.connecter.site_id}",
        vhost=DEFAULT_VHOST_NAME,
        durable=True,
        auto_delete=False,
        arguments={**QUEUE_DEFAULT_MESSAGE_TTL, **QUEUE_DEFAULT_MAX_LENGTH_BYTES},
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


def update_and_activate_rabbitmq_definitions(omd_root: Path, logger: Logger) -> None:
    definitions_file = omd_root / ACTIVE_DEFINITIONS_FILE_PATH
    new_definitions_file = omd_root / NEW_DEFINITIONS_FILE_PATH
    try:
        old_definitions = Definitions.loads(definitions_file.read_text())
    except FileNotFoundError:
        old_definitions = Definitions()

    try:
        new_definitions = Definitions.loads(new_definitions_file.read_text())
    except FileNotFoundError:
        return

    new_definitions_file.rename(definitions_file)

    if old_definitions == new_definitions:
        return

    # run in parallel
    for process in [
        *_start_cleanup_unused_definitions(old_definitions, new_definitions),
        _start_import_new_definitions(definitions_file),
    ]:
        (logger.info if process.wait() == 0 else logger.error)(_format_process(process))

    if set(old_definitions.parameters) - set(new_definitions.parameters):
        # avoid zombie shovels
        rabbitmqctl_process(("stop_app",), wait=True)
        rabbitmqctl_process(("start_app",), wait=True)


def _start_cleanup_unused_definitions(
    old_definitions: Definitions, new_definitions: Definitions
) -> Iterator[subprocess.Popen[str]]:
    # currently only shovels, but we don't have to care here
    # delete shovels before deleting e.g. users to avoid shovels trying to connect using deleted
    # resources
    for param in set(old_definitions.parameters) - set(new_definitions.parameters):
        yield rabbitmqctl_process(
            ("clear_parameter", "-p", param.vhost, param.component, param.name), wait=False
        )

    for queue in set(
        binding.destination
        for binding in old_definitions.bindings
        if binding.destination_type == "queue" and binding not in new_definitions.bindings
    ):
        # removed bindings are not correctly actualized in rabbitmq
        # we delete the queue to remove the bindings
        yield rabbitmqctl_process(("delete_queue", queue), wait=False)

    for vhost in {v.name for v in old_definitions.vhosts} - {
        v.name for v in new_definitions.vhosts
    }:
        yield rabbitmqctl_process(("delete_vhost", vhost), wait=False)

    for user in {u.name for u in old_definitions.users} - {u.name for u in new_definitions.users}:
        yield rabbitmqctl_process(("delete_user", user), wait=False)


def _start_import_new_definitions(definitions_file: Path) -> subprocess.Popen[str]:
    return rabbitmqctl_process(("import_definitions", str(definitions_file)), wait=False)


def rabbitmqctl_process(cmd: tuple[str, ...], /, *, wait: bool) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        ["rabbitmqctl", *cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if wait:
        proc.wait()
    return proc


def _format_process(p: subprocess.Popen[str]) -> str:
    return (
        f"{'FAILED' if p.returncode else 'OK'}: {p.args!r}\n"  # type: ignore[misc]  # contains Any
        f"{' '.join(p.stdout or ())}\n"
        f"{' '.join(p.stderr or ())}"
    )
