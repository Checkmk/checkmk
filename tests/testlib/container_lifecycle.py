#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Docker container lifecycle helpers shared by the relay test harnesses.

Kept free of ``CheckmkApp`` and ``openapi_session`` on purpose: ``relay_component``
runs the relay image without a site and must not pull those in, while
``relay_docker`` needs the very same waits. One copy here, no drift.
"""

import logging

import docker.errors
import docker.models.containers
import docker.models.networks

from tests.testlib.common.utils import wait_until

logger = logging.getLogger(__name__)

CONTAINER_READY_TIMEOUT = 30  # seconds to wait for a container to start or to be removed


def wait_for_container_running(
    container: docker.models.containers.Container,
    timeout: int = CONTAINER_READY_TIMEOUT,
) -> None:
    """Poll until the container reaches 'running' status or raise on timeout."""

    def _is_running() -> bool:
        try:
            container.reload()
        except docker.errors.NotFound as exc:
            raise RuntimeError(
                f"Container '{container.name}' exited and was removed — check config/image"
            ) from exc
        return container.status == "running"

    wait_until(
        _is_running,
        timeout=timeout,
        interval=1,
        condition_name=f"container '{container.name}' running",
    )


def wait_for_container_removed(
    container: docker.models.containers.Container,
    timeout: int = CONTAINER_READY_TIMEOUT,
) -> None:
    """Poll until the container no longer exists or raise on timeout.

    Containers started with ``auto_remove=True`` are removed by the Docker
    daemon asynchronously after they stop. Anything that must wait for their
    resources to be released (e.g. removing a named volume they mount) has to
    wait for the removal itself, not just for ``stop()`` to return.
    """

    def _is_removed() -> bool:
        try:
            container.reload()
        except docker.errors.NotFound:
            return True
        return False

    wait_until(
        _is_removed,
        timeout=timeout,
        interval=1,
        condition_name=f"container '{container.name}' removed",
    )


def get_container_ip(
    container: docker.models.containers.Container,
    network: docker.models.networks.Network,
) -> str:
    """Return the IP of *container* on *network*.

    Reads from NetworkSettings first; falls back to the network's endpoint
    list, which is populated for containers started after network creation.
    """
    networks = container.attrs["NetworkSettings"]["Networks"]
    logger.debug("Container %s networks: %s", container.name, list(networks.keys()))
    ip: str = networks.get(network.name, {}).get("IPAddress", "")
    if ip:
        return ip
    network.reload()
    for endpoint in network.attrs.get("Containers", {}).values():
        if endpoint.get("Name") == container.name:
            cidr: str = endpoint.get("IPv4Address", "")
            return cidr.split("/", maxsplit=1)[0]
    raise RuntimeError(
        f"Could not determine IP of container '{container.name}' on network '{network.name}'"
    )
