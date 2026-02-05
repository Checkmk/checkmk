#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Native WireMock process manager - replaces Docker-based WireMock."""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import httpx


def _get_open_port(host: str = "127.0.0.1") -> int:
    """
    Find available free ports on the system.
    Has time of check to time of use race condition!
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return cast(int, s.getsockname()[1])


@dataclass(frozen=True)
class WiremockProcess:
    """Represents a running WireMock process."""

    process: subprocess.Popen[bytes]
    http_port: int
    hostname: str
    temp_dir: Path

    def terminate(self) -> None:
        """Terminate the WireMock process."""
        if self.process.poll() is None:  # Process is still running
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def _wait_for_wiremock(base_url: str, timeout: int = 30) -> None:
    """Wait for WireMock to be ready by polling its health endpoint."""
    start_time = time.monotonic()
    while True:
        try:
            response = httpx.get(f"{base_url}/__admin/health", timeout=1)
            if response.status_code == 200:
                return
        except (httpx.RequestError, httpx.TimeoutException):
            pass

        if time.monotonic() - start_time > timeout:
            raise RuntimeError(f"WireMock did not start within {timeout} seconds")
        time.sleep(0.5)


def _get_java_binary() -> str:
    """
    Get the Java binary path from JAVA_BIN environment variable.

    This environment variable is set by Bazel via the test's env attribute,
    pointing to a hermetic JDK provided by Bazel.

    Returns:
        str: Path to the Java binary

    Raises:
        RuntimeError: If JAVA_BIN is not set
    """
    java_bin = os.environ.get("JAVA_BIN")
    if not java_bin:
        raise RuntimeError(
            "JAVA_BIN environment variable not set. "
            "This should be configured in the Bazel BUILD file."
        )

    java_path = Path(java_bin).resolve()

    assert java_path.exists()
    return str(java_path)


def _locate_wiremock_jar() -> Path:
    """
    Locate the WireMock JAR file from WIREMOCK_JAR environment variable.

    This environment variable is set by Bazel via the test's env attribute.
    The path may be relative to the runfiles directory.

    Returns:
        Path: Path to the WireMock JAR file

    Raises:
        RuntimeError: If WIREMOCK_JAR is not set or file doesn't exist
    """
    jar_env = os.environ.get("WIREMOCK_JAR")
    if not jar_env:
        raise RuntimeError(
            "WIREMOCK_JAR environment variable not set. "
            "This should be configured in the Bazel BUILD file."
        )

    jar_path = Path(jar_env).resolve()
    assert jar_path.exists()
    return jar_path


@contextlib.contextmanager
def run_wiremock(
    hostname: str = "127.0.0.1",
) -> Iterator[WiremockProcess]:
    """
    Start WireMock as a native Java process (HTTP only).

    Args:
        hostname: Hostname to bind to (default: 127.0.0.1)

    Yields:
        WiremockProcess: Running WireMock process information
    """
    # Locate WireMock JAR and Java binary
    jar_path = _locate_wiremock_jar()
    java_bin = _get_java_binary()

    # Allocate port
    http_port = _get_open_port(hostname)

    # Create temporary directory for WireMock's working directory
    with tempfile.TemporaryDirectory(prefix="wiremock-") as temp_dir:
        temp_path = Path(temp_dir)

        # Build WireMock command
        cmd: list[str] = [
            java_bin,
            "-jar",
            str(jar_path),
            "--port",
            str(http_port),
            "--bind-address",
            hostname,
            "--disable-banner",
        ]

        # Start WireMock process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=temp_path,
        )

        try:
            # Wait for WireMock to be ready
            base_url = f"http://{hostname}:{http_port}"
            _wait_for_wiremock(base_url)

            # nosemgrep: disallow-print
            print(f"Started native WireMock on {hostname}:{http_port}")

            wiremock_proc = WiremockProcess(
                process=process,
                http_port=http_port,
                hostname=hostname,
                temp_dir=temp_path,
            )

            yield wiremock_proc

        finally:
            # nosemgrep: disallow-print
            print(f"Stopping native WireMock (PID: {process.pid})")
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
