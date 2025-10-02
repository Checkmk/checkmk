#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import random
import socket
import subprocess  # nosec
import time
from collections.abc import Iterator
from dataclasses import dataclass

IMAGE = "wiremock/wiremock:3.13.1"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            # If bind succeeds, port is not in use
            return False
        except OSError:
            # If bind fails, port is in use
            return True


def get_open_port(host: str = "127.0.0.1") -> int:
    while True:
        # ensure truly unique numbers on pytest-xdist execution
        port = random.SystemRandom().randint(10001, 65535)
        if is_port_in_use(port, host):
            continue
        return port


@dataclass(frozen=True)
class Container:
    address: str
    port: int


@contextlib.contextmanager
def run_container() -> Iterator[Container]:
    """
    Start a site service container and return its address.
    """
    port = get_open_port()
    with _run_container(
        docker_image=IMAGE,
        container_name=f"site-{port}",
        additional_docker_args=["-p", f"{port}:8080"],
    ) as address:
        yield Container(address, port)


@contextlib.contextmanager
def _run_container(
    *,
    docker_image: str,
    container_name: str,
    timeout_in_seconds: int = 60,
    additional_docker_args: list[str] | None = None,
) -> Iterator[str]:
    start_time = time.monotonic()

    _start_container(
        docker_image=docker_image,
        container_name=container_name,
        additional_docker_args=additional_docker_args,
    )
    try:
        _wait_for_container_up(
            container_name=container_name,
            start_time=start_time,
            timeout_in_seconds=timeout_in_seconds,
        )
        yield _get_gateway(container_name)
    finally:
        _stop_container(container_name)


def _start_container(
    *,
    docker_image: str,
    container_name: str,
    additional_docker_args: list[str] | None,
) -> None:
    other_args = [] if additional_docker_args is None else additional_docker_args
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            *other_args,
            docker_image,
        ],
        check=True,
        shell=False,
    )


def _wait_for_container_up(
    *, container_name: str, start_time: float, timeout_in_seconds: int
) -> None:
    while True:
        output = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{json .State.Health.Status}}",
                container_name,
            ],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        if "healthy" in output.stdout:
            break
        time_delta = time.monotonic() - start_time
        if time_delta > timeout_in_seconds:
            msg = "Container did not startup in time"
            raise RuntimeError(msg)
        time.sleep(1)


def _stop_container(container_name: str) -> None:
    subprocess.run(["docker", "stop", container_name], check=True)  # nosec


def _get_gateway(container_name: str) -> str:
    output = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}",
            container_name,
        ],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    ).stdout.strip()
    if output == "":
        return "127.0.0.1"
    return output
