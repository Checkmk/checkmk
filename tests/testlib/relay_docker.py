#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Reusable Docker-backed objects for relay integration testing.

Provides:
    get_container_ip    -- resolve a container's IP on a specific network
    DockerSnmpHost      -- snmpd container on an isolated monitored network
    DockerRelaySetup    -- relay daemon wired to a Checkmk site
"""

import json
import logging
from typing import Self

import docker
import docker.errors
import docker.models.containers
import docker.models.networks
import docker.models.volumes

from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.docker import CheckmkApp
from tests.testlib.openapi_session import APIVersion

logger = logging.getLogger(__name__)

SNMPD_IMAGE = "docker.io/polinux/snmpd"
RELAY_WORKDIR = "/opt/check-mk-relay/workdir"
_CONTAINER_READY_TIMEOUT = 30  # seconds to wait for a container to become running


def _wait_for_container_running(
    container: docker.models.containers.Container,
    timeout: int = _CONTAINER_READY_TIMEOUT,
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


class DockerSnmpHost:
    """snmpd container on an isolated network, reachable only via the relay.

    Public attributes:
        ip             -- IP of the container on *network*
        container_name -- Docker container name (resolvable via Docker DNS)
        logs           -- current stdout/stderr of the snmpd container
    """

    def __init__(
        self,
        client: docker.DockerClient,
        network: docker.models.networks.Network,
        suffix: str,
    ) -> None:
        self._client = client
        self._network = network
        self._suffix = suffix
        self._container = self._start()
        self.ip = get_container_ip(self._container, self._network)
        logger.info("SNMP host IP on %s: %s", network.name, self.ip)

    @property
    def container_name(self) -> str:
        return str(self._container.name)

    @property
    def logs(self) -> str:
        return self._container.logs().decode("utf-8")

    def snmp_interface_count(self) -> int:
        """Count network interfaces exposed via SNMP IF-MIB.

        Uses snmpwalk on OID 1.3.6.1.2.1.2.2.1.1 (ifIndex) to enumerate
        all interfaces. Combined with the always-present SNMP Info service,
        this gives the expected total service count after discovery.
        """
        exit_code, output = self._container.exec_run(
            ["snmpwalk", "-v2c", "-c", "public", "127.0.0.1", "1.3.6.1.2.1.2.2.1.1"],
        )
        assert exit_code == 0, (
            f"snmpwalk failed (exit {exit_code}): {output.decode(errors='replace')}"
        )
        lines = output.decode().strip().splitlines()
        return len([line for line in lines if line.strip()])

    def _start(self) -> docker.models.containers.Container:
        container_name = f"snmpd-{self._suffix}"
        logger.info("Starting snmpd container: %s", container_name)
        container = self._client.containers.run(
            SNMPD_IMAGE,
            entrypoint=[
                "/bin/sh",
                "-c",
                'echo "" >> /etc/snmp/snmpd.conf'
                ' && echo "view systemview included .1" >> /etc/snmp/snmpd.conf'
                " && exec snmpd -f -Lo -c /etc/snmp/snmpd.conf",
            ],
            network=self._network.name,
            name=container_name,
            auto_remove=True,
            detach=True,
        )
        _wait_for_container_running(container)
        logger.info("snmpd container status: %s", container.status)
        self._wait_for_snmpd_ready(container)
        return container

    @staticmethod
    def _wait_for_snmpd_ready(
        container: docker.models.containers.Container,
        timeout: int = _CONTAINER_READY_TIMEOUT,
    ) -> None:
        """Poll until snmpd responds to SNMP queries."""

        def _snmpd_responds() -> bool:
            exit_code, _ = container.exec_run(
                ["snmpget", "-v2c", "-c", "public", "127.0.0.1", "sysDescr.0"],
            )
            return bool(exit_code == 0)

        wait_until(
            _snmpd_responds,
            timeout=timeout,
            interval=1,
            condition_name="snmpd responding to SNMP queries",
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if not is_cleanup_enabled():
            return
        try:
            self._container.stop()
        except docker.errors.APIError as e:
            logger.warning("Could not stop snmpd container: %s", e)
            raise


class DockerRelaySetup:
    """Relay daemon wired to a Checkmk site and a monitored-host network.

    Attaches the site to site-relay, registers a relay via the site's
    agent-receiver, and starts the relay daemon bridging both networks.

    Public attributes:
        relay_id -- UUID the site assigned to this relay
        logs     -- current stdout/stderr of the relay daemon container
    """

    def __init__(
        self,
        client: docker.DockerClient,
        checkmk: CheckmkApp,
        relay_image: str,
        site_relay_network: docker.models.networks.Network,
        monitored_network: docker.models.networks.Network,
        relay_volume: docker.models.volumes.Volume,
        suffix: str,
    ) -> None:
        self._client = client
        self._checkmk = checkmk
        self._relay_image = relay_image
        self._suffix = suffix
        self._site_relay_network = site_relay_network
        self._relay_monitored_network = monitored_network
        self._relay_volume = relay_volume

        self._site_ip = self._attach_checkmk_to_network()
        self._relay_alias = f"relay-{self._suffix}"
        self._register_relay()
        self.relay_id = self._read_relay_id_from_workdir()
        logger.info("Relay UUID from site: %s (alias: %s)", self.relay_id, self._relay_alias)
        self._relay_container = self._start_daemon()

    @property
    def logs(self) -> str:
        return self._relay_container.logs().decode("utf-8")

    def _attach_checkmk_to_network(self) -> str:
        logger.info("Connecting checkmk container to network %s", self._site_relay_network.name)
        self._site_relay_network.connect(self._checkmk.container)
        self._checkmk.container.reload()
        site_ip = get_container_ip(self._checkmk.container, self._site_relay_network)
        logger.info("Checkmk site IP on site-relay network: %s", site_ip)
        return site_ip

    def _volume_mount(self) -> dict[str, dict[str, str]]:
        return {self._relay_volume.name: {"bind": RELAY_WORKDIR, "mode": "rw"}}

    def _read_relay_id_from_workdir(self) -> str:
        output = self._client.containers.run(
            self._relay_image,
            command=["cat", f"{RELAY_WORKDIR}/site_config.json"],
            volumes=self._volume_mount(),
            remove=True,
        )
        return str(json.loads(output)["relay_id"])

    def _register_relay(self) -> None:
        """Register the relay with the site exactly once.

        Failure raises with the full ``cmk-relay register`` stdout + stderr so
        the underlying problem is visible — no retries hiding flaky behaviour.
        """
        logger.info("Registering relay '%s' with site at %s", self._relay_alias, self._site_ip)
        # cmk-relay's `register` has no --password flag: it reads the password from
        # stdin when not attached to a TTY (see cmk.relay.app._prompt_for_password).
        # Feed it via a piped shell command, passing the secret through the environment
        # rather than argv.
        register_cmd = (
            'printf "%s" "$CMK_RELAY_PASSWORD" | cmk-relay register'
            f" --server {self._site_ip}:{self._checkmk.agent_receiver_port}"
            f" --site {self._checkmk.site_id}"
            f" --user {self._checkmk.username}"
            f" --relay-alias {self._relay_alias}"
            " --trust-cert --log-level debug"
        )
        container = self._client.containers.run(
            self._relay_image,
            entrypoint=["/bin/bash", "-c"],
            command=[register_cmd],
            environment={"CMK_RELAY_PASSWORD": self._checkmk.password},
            volumes=self._volume_mount(),
            network=self._site_relay_network.name,
            detach=True,
        )
        try:
            exit_code = int(container.wait()["StatusCode"])
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        finally:
            container.remove(force=True)
        if exit_code != 0:
            raise RuntimeError(
                f"Relay registration failed (exit {exit_code})\n"
                f"--- STDOUT ---\n{stdout}\n--- STDERR ---\n{stderr}"
            )
        logger.info("Relay registration complete:\n%s", stdout)

    def _start_daemon(self) -> docker.models.containers.Container:
        container_name = f"relay-daemon-{self._suffix}"
        logger.info("Starting relay daemon container: %s", container_name)
        container = self._client.containers.run(
            self._relay_image,
            command=["cmk-relay", "daemon"],
            volumes=self._volume_mount(),
            network=self._site_relay_network.name,
            name=container_name,
            auto_remove=True,
            detach=True,
        )
        logger.info("Connecting relay daemon to monitored network")
        self._relay_monitored_network.connect(container)
        _wait_for_container_running(container)
        return container

    def __enter__(self) -> Self:
        return self

    def _delete_relay_from_site(self) -> None:
        """Delete the relay from the Checkmk site via the OpenAPI.

        All hosts monitored by this relay must be deleted before calling this,
        otherwise the API will reject the deletion.

        The relay endpoints are only available in the unstable API version,
        so we temporarily switch to it for the duration of this call.
        """
        logger.info("Deleting relay '%s' from site", self.relay_id)
        original_version = self._checkmk.openapi.api_version
        try:
            self._checkmk.openapi.api_version = APIVersion.UNSTABLE
            _, etag = self._checkmk.openapi.relays.get(self.relay_id)
            self._checkmk.openapi.relays.delete(self.relay_id, etag)
            self._checkmk.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=True
            )
        except Exception:
            logger.exception("Could not delete relay '%s' from site", self.relay_id)
        finally:
            self._checkmk.openapi.api_version = original_version

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if not is_cleanup_enabled():
            return
        logger.info("Cleaning up relay daemon")
        try:
            self._relay_container.stop()
        except docker.errors.APIError as e:
            logger.warning("Could not stop relay container: %s", e)
            raise
        finally:
            self._delete_relay_from_site()
            try:
                self._site_relay_network.disconnect(self._checkmk.container, force=True)
            except docker.errors.APIError as e:
                logger.warning("Could not disconnect checkmk from site-relay network: %s", e)
                raise
