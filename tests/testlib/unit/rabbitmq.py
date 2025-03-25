#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides functions to configure RabbitMQ components for Checkmk inter-site
communication.

It includes helper functions to create queues, bindings, permissions, and shovels, and to generate
expected RabbitMQ definitions for replicated and peer-to-peer sites.
"""

from collections.abc import Mapping, Sequence

from cmk.messaging.rabbitmq import (
    Binding,
    Definitions,
    Permission,
    Queue,
    QUEUE_DEFAULT_MAX_LENGTH_BYTES,
    QUEUE_DEFAULT_MESSAGE_TTL,
    Shovel,
    ShovelValue,
    User,
)


def _get_queue(site_id: str) -> Queue:
    return Queue(
        name=f"cmk.intersite.{site_id}",
        vhost="/",
        durable=True,
        auto_delete=False,
        arguments={**QUEUE_DEFAULT_MESSAGE_TTL, **QUEUE_DEFAULT_MAX_LENGTH_BYTES},
    )


def _get_binding(site_id: str) -> Binding:
    return Binding(
        source="cmk.intersite",
        vhost="/",
        destination=f"cmk.intersite.{site_id}",
        destination_type="queue",
        routing_key=f"{site_id}.#",
        arguments={},
    )


def _get_permission(site_id: str) -> Permission:
    return Permission(
        user=site_id,
        vhost="/",
        configure="cmk.intersite..*",
        write="cmk.intersite",
        read="cmk.intersite..*",
    )


def _get_component(site1: str, site2: str, port2: int) -> Sequence[Shovel]:
    return [
        Shovel(
            value=ShovelValue.from_kwargs(
                dest_uri=f"amqps://127.0.0.1:{port2}?server_name_indication={site2}&auth_mechanism=external",
                src_queue=f"cmk.intersite.{site2}",
                src_uri="amqp:///%2f",
            ),
            vhost="/",
            component="shovel",
            name=f"cmk.shovel.{site1}->{site2}",
        ),
        Shovel(
            value=ShovelValue.from_kwargs(
                dest_uri="amqp:///%2f",
                src_queue=f"cmk.intersite.{site1}",
                src_uri=f"amqps://127.0.0.1:{port2}?server_name_indication={site2}&auth_mechanism=external",
            ),
            vhost="/",
            component="shovel",
            name=f"cmk.shovel.{site2}->{site1}",
        ),
    ]


def get_expected_definition(
    current_site: str,
    replicated_sites: Mapping[str, int],
    p2p_sites: Mapping[str, str],
) -> Mapping[str, Definitions]:
    definitions = {}

    users = []
    permissions = []
    parameters: list[Shovel] = []
    queues = []
    bindings = []
    for site, port in replicated_sites.items():
        users.append(User(name=site, tags=()))
        permissions.append(_get_permission(site))
        bindings.append(_get_binding(site))
        queues.append(_get_queue(site))
        parameters.extend(_get_component(current_site, site, port))

    definitions[current_site] = Definitions(
        users=users,
        permissions=permissions,
        parameters=parameters,
        queues=queues,
        bindings=bindings,
    )

    for site in replicated_sites:
        bindings = []
        queues = []
        users = []
        permissions = []
        parameters = []
        for other_site in [current_site] + list(replicated_sites.keys()):
            if other_site == site:
                continue
            users.append(User(name=other_site, tags=()))
            bindings.append(_get_binding(other_site))
            queues.append(_get_queue(other_site))
            permissions.append(_get_permission(other_site))

            if site in p2p_sites and p2p_sites[site] == other_site:
                parameters.extend(_get_component(site, other_site, replicated_sites[other_site]))

        definitions[site] = Definitions(
            users=users,
            vhosts=[],
            permissions=permissions,
            policies=[],
            exchanges=[],
            bindings=bindings,
            queues=queues,
            parameters=parameters,
        )

    return definitions
