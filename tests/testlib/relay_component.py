#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Docker-backed helpers for relay active-check *component* tests.

Unlike ``relay_docker`` (which wires a relay daemon to a Checkmk site), this
module runs the relay *image* as an idle container so a single active-check
binary can be exec'd against a mock target service. No site, no CMC, no relay
daemon are involved.

``DockerHttpMock`` and ``run_check`` are generic enough for suites that do have a
site and a relay daemon to reuse, rather than growing a second HTTP-container
class. They live here and not in ``relay_docker`` because that module imports
``CheckmkApp`` and ``openapi_session``, and this one must stay free of them; the
container lifecycle helpers both need come from ``container_lifecycle``.

Provides:
    CheckResult          -- exit code + output of an exec'd active check
    DockerHttpMock       -- minimal HTTP server as an active-check target
    idle_relay_container -- relay image started idle for exec-based checks
    run_check            -- exec an active-check plugin, parse its result
    run_via_checkhelper  -- drive checkhelper and decode its result frame
    start_tls_server     -- serve a self-signed cert on loopback (TLS target)
    assert_executable    -- assert a path is executable inside the container
    assert_ldd_resolves  -- assert a binary's shared libs all resolve
"""

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self

import docker
import docker.errors
import docker.models.containers
import docker.models.networks

from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.container_lifecycle import (
    CONTAINER_READY_TIMEOUT,
    get_container_ip,
    wait_for_container_removed,
    wait_for_container_running,
)

logger = logging.getLogger(__name__)

HTTP_MOCK_IMAGE = "docker.io/library/python:3-slim"
HTTP_MOCK_PORT = 80
RELAY_PLUGINS_DIR = "/opt/check-mk-relay/lib/nagios/plugins"
RELAY_CHECKHELPER = "/opt/check-mk-relay/lib/cmc/checkhelper"
# The minimal relay image ships no `ldd` wrapper; invoke the dynamic loader
# directly (its --list output is equivalent) to check shared-library resolution.
_DYNAMIC_LOADER = "/lib64/ld-linux-x86-64.so.2"
# The relay image bundles an openssl CLI; its baked-in default config path does
# not exist in the image, so calls set OPENSSL_CONF=/dev/null to skip it.
_RELAY_OPENSSL = "/opt/check-mk-relay/bin/openssl"
_OPENSSL_ENV = "OPENSSL_CONF=/dev/null"


@dataclass(frozen=True)
class CheckResult:
    """Result of running an active-check binary: Nagios exit code and output."""

    exit_code: int
    output: str


class DockerHttpMock:
    """Minimal HTTP server on a network, usable as an active-check target.

    Public attributes:
        ip   -- IP of the container on *network*
        port -- port the server listens on
        logs -- current stdout/stderr of the server container
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
        self.port = HTTP_MOCK_PORT

    @property
    def logs(self) -> str:
        return self._container.logs().decode("utf-8")

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
            # auto_remove=True: the daemon removes the container asynchronously after
            # stop(). Wait for it, so the network teardown does not race the removal
            # and a later mock can reuse the deterministic container name.
            wait_for_container_removed(self._container)
        except TimeoutError as e:
            e.add_note(
                f"http-mock container was not auto-removed within {CONTAINER_READY_TIMEOUT} "
                "secs after stop()!"
            )
            raise
        except docker.errors.APIError as e:
            logger.warning("Could not stop http-mock container: %s", e)
            raise

    def _start(self) -> docker.models.containers.Container:
        container_name = f"http-mock-{self._suffix}"
        logger.info("Starting http-mock container: %s", container_name)
        container = self._client.containers.run(
            HTTP_MOCK_IMAGE,
            entrypoint=["python3", "-m", "http.server", str(HTTP_MOCK_PORT)],
            network=self._network.name,
            name=container_name,
            auto_remove=True,
            detach=True,
        )
        wait_for_container_running(container)
        _wait_until_http_serving(container)
        return container


@contextmanager
def idle_relay_container(
    client: docker.DockerClient,
    image: str,
    network: docker.models.networks.Network,
    suffix: str,
) -> Iterator[docker.models.containers.Container]:
    """Run the relay *image* as an idle container for exec-based checks.

    The entrypoint is overridden with ``sleep infinity`` so the container stays
    up without a site or relay daemon; tests exec binaries into it directly.
    """
    container_name = f"relay-component-{suffix}"
    logger.info("Starting idle relay container: %s", container_name)
    container = client.containers.run(
        image,
        entrypoint=["sleep", "infinity"],
        network=network.name,
        name=container_name,
        auto_remove=True,
        detach=True,
    )
    wait_for_container_running(container)
    try:
        yield container
    finally:
        if is_cleanup_enabled():
            try:
                container.stop()
                # auto_remove=True, see DockerHttpMock.__exit__
                wait_for_container_removed(container)
            except TimeoutError as e:
                e.add_note(
                    f"idle relay container was not auto-removed within {CONTAINER_READY_TIMEOUT} "
                    "secs after stop()!"
                )
                raise
            except docker.errors.APIError as e:
                logger.warning("Could not stop idle relay container: %s", e)
                raise


def run_check(
    container: docker.models.containers.Container,
    argv: Sequence[str],
) -> CheckResult:
    """Exec an active-check plugin inside *container* and return its result."""
    exit_code, output = _exec(container, argv)
    return CheckResult(exit_code=exit_code, output=output)


def assert_executable(
    container: docker.models.containers.Container,
    path: str,
) -> None:
    """Assert *path* exists and is executable inside *container*."""
    exit_code, output = _exec(container, ["test", "-x", path])
    assert exit_code == 0, f"{path} is not executable in the relay image: {output!r}"


def assert_ldd_resolves(
    container: docker.models.containers.Container,
    path: str,
) -> None:
    """Assert every shared library *path* links against resolves in the image."""
    exit_code, output = _exec(container, [_DYNAMIC_LOADER, "--list", path])
    assert exit_code == 0, f"listing shared libraries of {path} failed: {output}"
    missing = [line.strip() for line in output.splitlines() if "not found" in line]
    assert not missing, f"unresolved shared libraries for {path}: {missing}"


@contextmanager
def start_tls_server(
    container: docker.models.containers.Container,
    port: int,
) -> Iterator[None]:
    """Serve a self-signed TLS cert on *port* (loopback), stopping it on exit.

    A self-contained target for TLS active checks: generates a throwaway
    self-signed certificate and runs ``openssl s_server`` in the background,
    yielding once the port accepts connections. On exit the server is killed so
    the port is freed and no stale server lingers to trap a later test.
    """
    cert, key = "/tmp/relay_component_cert.pem", "/tmp/relay_component_key.pem"
    pidfile = f"/tmp/relay_component_tls_{port}.pid"
    exit_code, output = _exec(
        container,
        [
            "env",
            _OPENSSL_ENV,
            _RELAY_OPENSSL,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            key,
            "-out",
            cert,
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=cert-mock",
        ],
    )
    assert exit_code == 0, f"self-signed cert generation failed: {output}"
    # Record the server PID (exec-into-place keeps it) so we can stop it on exit.
    container.exec_run(
        [
            "sh",
            "-c",
            (
                f"echo $$ > {pidfile}; exec env {_OPENSSL_ENV} {_RELAY_OPENSSL} s_server "
                f"-cert {cert} -key {key} -accept {port} -www -quiet"
            ),
        ],
        detach=True,
    )
    try:
        _wait_until_tcp_open(container, port)
        yield
    finally:
        container.exec_run(["sh", "-c", f"kill $(cat {pidfile}) 2>/dev/null || true"])


def run_via_checkhelper(
    container: docker.models.containers.Container,
    host: str,
    command: str,
    timeout: int = 10,
) -> CheckResult:
    """Drive `checkhelper`: feed it host/command/timeout, decode the result.

    `checkhelper` reads three stdin lines and answers with the frame
    ``RRR\\nNNNNNNNN\\n<host>\\t<output>``. This does a minimal decode for the
    component test; the production parser is the shared `CheckhelperFrame` (M1).
    The command must not contain single quotes.
    """
    stdin = f"{host}\n{command}\n{timeout}\n"
    exit_code, raw = _exec(container, ["sh", "-c", f"printf '%s' '{stdin}' | {RELAY_CHECKHELPER}"])
    assert exit_code == 0, f"checkhelper process failed (exit {exit_code}): {raw!r}"
    return_code, _size, payload = raw.split("\n", 2)
    _host, _, output = payload.partition("\t")
    return CheckResult(exit_code=int(return_code), output=output)


def _exec(
    container: docker.models.containers.Container,
    argv: Sequence[str],
) -> tuple[int, str]:
    """Run *argv* in *container*; return its exit code and decoded output."""
    exit_code, output = container.exec_run(list(argv))
    # Neither stream nor detach nor socket mode is used, so the daemon reports the
    # exit code and hands back the whole output at once.
    assert exit_code is not None
    assert isinstance(output, bytes)
    return exit_code, output.decode("utf-8", errors="replace")


def _wait_until_http_serving(
    container: docker.models.containers.Container,
    timeout: int = CONTAINER_READY_TIMEOUT,
) -> None:
    """Poll until the mock HTTP server answers a request on localhost."""

    def _serves() -> bool:
        url = f"http://127.0.0.1:{HTTP_MOCK_PORT}"
        exit_code, _ = container.exec_run(
            ["python3", "-c", f"import urllib.request; urllib.request.urlopen('{url}')"],
        )
        return bool(exit_code == 0)

    wait_until(
        _serves,
        timeout=timeout,
        interval=0.5,
        condition_name="http-mock serving requests",
    )


def _wait_until_tcp_open(
    container: docker.models.containers.Container,
    port: int,
    timeout: int = CONTAINER_READY_TIMEOUT,
) -> None:
    """Poll until *port* accepts TCP connections on the container's loopback."""

    def _accepts() -> bool:
        exit_code, _ = container.exec_run(["bash", "-c", f"echo > /dev/tcp/127.0.0.1/{port}"])
        return bool(exit_code == 0)

    wait_until(
        _accepts,
        timeout=timeout,
        interval=0.5,
        condition_name=f"tcp port {port} accepting connections",
    )
